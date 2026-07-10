"""Content Strategist agent — Growth OS Fase 9 (on-demand)."""

from __future__ import annotations

from uuid import UUID

from contentos_growth import GrowthService
from contentos_growth.infrastructure.sqlalchemy_repository import SqlAlchemyGrowthRepository
from contentos_shared.agents.base import BaseAgentHandler
from contentos_shared.enums import JobStatus
from contentos_shared.schemas.agent import AgentTaskInput, AgentTaskOutput

try:
    from contentos_database.session import get_session_factory
except ImportError:  # pragma: no cover
    get_session_factory = None  # type: ignore[misc, assignment]


class ContentStrategistAgentHandler(BaseAgentHandler):
    step = "content_strategist"

    async def execute(self, task_input: AgentTaskInput) -> AgentTaskOutput:
        payload = task_input.payload or {}
        horizon_days = int(payload.get("horizon_days") or 30)
        logs = [f"[content_strategist] Generating plan for project {task_input.project_id}"]

        session_factory = get_session_factory()
        if not session_factory:
            raise RuntimeError("Database session factory unavailable")

        async with session_factory() as db:
            service = GrowthService(SqlAlchemyGrowthRepository(db))
            plan = await service.generate_content_strategy(
                db,
                UUID(str(task_input.project_id)),
                horizon_days=horizon_days,
            )
            await db.commit()

        logs.append(plan.summary)
        return AgentTaskOutput(
            job_id=task_input.job_id,
            status=JobStatus.COMPLETED.value,
            data=plan.to_dict(),
            logs=logs,
        )
