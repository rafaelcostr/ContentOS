"""Competitor analyzer agent — Growth OS Fase 7 (on-demand, outside video pipeline)."""

from __future__ import annotations

from uuid import UUID

from contentos_growth import GrowthService
from contentos_growth.infrastructure.sqlalchemy_repository import SqlAlchemyGrowthRepository
from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.enums import JobStatus
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput

try:
    from contentos_database.session import get_session_factory
    from contentos_events import DomainEvent, get_event_bus
except ImportError:  # pragma: no cover
    get_session_factory = None  # type: ignore[misc, assignment]
    DomainEvent = None  # type: ignore[misc, assignment]

    def get_event_bus():  # type: ignore[misc]
        return None


class CompetitorAnalyzerAgentHandler(BaseAgentHandler):
    step = "competitor_analyzer"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        payload = task_input.payload or {}
        competitor_id = UUID(str(payload.get("competitor_id")))
        sync_first = bool(payload.get("sync_first", True))
        limit = int(payload.get("limit") or 10)
        logs = [f"[competitor_analyzer] Analyzing competitor {competitor_id}"]

        session_factory = get_session_factory()
        if not session_factory:
            raise RuntimeError("Database session factory unavailable")

        async with session_factory() as db:
            service = GrowthService(SqlAlchemyGrowthRepository(db))
            competitor = await service.get_competitor(competitor_id)
            if not competitor:
                raise ValueError("Competitor not found")
            if str(competitor.project_id) != str(task_input.project_id):
                raise ValueError("Competitor does not belong to project")

            if sync_first:
                logs.append("Syncing public metrics before analysis")
                await service.sync_competitor(competitor_id, limit=limit)

            result = await service.analyze_competitor(competitor_id)
            await db.commit()

        logs.append(f"Competitive score: {result.score}")
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
