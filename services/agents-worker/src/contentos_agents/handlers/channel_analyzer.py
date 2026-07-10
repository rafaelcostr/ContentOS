"""Channel Analyzer agent — Growth OS Fase 4 (on-demand, outside video pipeline)."""

from __future__ import annotations

from uuid import UUID

from contentos_growth import GrowthService
from contentos_growth.infrastructure.sqlalchemy_repository import SqlAlchemyGrowthRepository
from contentos_intelligence.application.platform_analytics.service import get_latest_channel_overview
from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.enums import JobStatus
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput

try:
    from contentos_database.models import Channel
    from contentos_database.session import get_session_factory
    from contentos_events import DomainEvent, get_event_bus
    from sqlalchemy import select
except ImportError:  # pragma: no cover
    Channel = object  # type: ignore[misc, assignment]
    get_session_factory = None  # type: ignore[misc, assignment]
    DomainEvent = None  # type: ignore[misc, assignment]

    def get_event_bus():  # type: ignore[misc]
        return None


class ChannelAnalyzerAgentHandler(BaseAgentHandler):
    step = "channel_analyzer"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        payload = task_input.payload or {}
        channel_id = UUID(str(payload.get("channel_id") or task_input.payload.get("channel_id")))
        logs = [f"[channel_analyzer] Analyzing channel {channel_id}"]

        session_factory = get_session_factory()
        if not session_factory:
            raise RuntimeError("Database session factory unavailable")

        async with session_factory() as db:
            channel = (await db.execute(select(Channel).where(Channel.id == channel_id))).scalar_one_or_none()
            if not channel:
                raise ValueError("Channel not found")
            if str(channel.project_id) != str(task_input.project_id):
                raise ValueError("Channel does not belong to project")

            overview = await get_latest_channel_overview(db, channel_id, platform=channel.platform.lower())
            service = GrowthService(SqlAlchemyGrowthRepository(db))
            result = await service.analyze_channel(
                db=db,
                channel_id=channel_id,
                project_id=channel.project_id,
                platform=channel.platform,
                channel_name=channel.name,
                overview=overview,
            )
            await db.commit()

        logs.append(f"Growth score: {result.score}")
        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            data=result.to_dict(),
            logs=logs,
        )

    async def _callback(self, output: AgentTaskOutput) -> None:
        try:
            bus = get_event_bus()
            if not bus or not DomainEvent or not hasattr(self, "_last_task_input"):
                return
            ti = self._last_task_input
            event = DomainEvent.from_agent_callback(
                step=self.step,
                project_id=ti.project_id,
                pipeline_id=ti.pipeline_id,
                job_id=output.job_id,
                status=output.status,
                payload=output.data or {},
            )
            bus.publish_sync(event)
        except Exception:
            pass
