"""Cost entry persistence."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

from contentos_cost.domain.cost_entry import CostRecord
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


def record_sync(entry: CostRecord) -> bool:
    """Insert cost entry from Celery worker (sync)."""
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        return False
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace(
        "postgresql://", "postgresql+psycopg2://"
    )
    try:
        from contentos_database.models import CostEntry as CostEntryModel
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        engine = create_engine(sync_url, pool_pre_ping=True)
        with Session(engine) as session:
            row = CostEntryModel(
                id=uuid.uuid4(),
                project_id=entry.project_id,
                pipeline_id=entry.pipeline_id,
                job_id=entry.job_id,
                agent=entry.agent,
                provider=entry.provider,
                model=entry.model,
                operation=entry.operation,
                tokens_input=entry.tokens_input,
                tokens_output=entry.tokens_output,
                duration_ms=entry.duration_ms,
                estimated_cost_usd=entry.estimated_cost_usd,
                from_cache=entry.from_cache,
                created_at=datetime.now(UTC),
            )
            session.add(row)
            session.commit()
        return True
    except Exception:
        return False


class CostRepository:
    def _scope(self, query, project_ids: list[uuid.UUID] | None):
        from contentos_database.models import CostEntry as CostEntryModel

        if project_ids is not None:
            return query.where(CostEntryModel.project_id.in_(project_ids))
        return query

    async def overview(self, db: AsyncSession, project_ids: list[uuid.UUID] | None = None) -> dict:
        from contentos_database.models import CostEntry as CostEntryModel

        q = select(
            func.coalesce(func.sum(CostEntryModel.estimated_cost_usd), 0.0),
            func.coalesce(func.sum(CostEntryModel.tokens_input), 0),
            func.coalesce(func.sum(CostEntryModel.tokens_output), 0),
            func.count(),
        )
        q = self._scope(q, project_ids)
        row = (await db.execute(q)).one()

        by_provider_q = select(
            CostEntryModel.provider,
            func.sum(CostEntryModel.estimated_cost_usd),
            func.count(),
        ).group_by(CostEntryModel.provider)
        by_provider_q = self._scope(by_provider_q, project_ids)
        by_provider = {
            r[0]: {"cost_usd": float(r[1] or 0), "operations": int(r[2])}
            for r in (await db.execute(by_provider_q)).all()
        }

        by_agent_q = select(
            CostEntryModel.agent,
            func.sum(CostEntryModel.estimated_cost_usd),
            func.count(),
        ).group_by(CostEntryModel.agent)
        by_agent_q = self._scope(by_agent_q, project_ids)
        by_agent = {
            r[0]: {"cost_usd": float(r[1] or 0), "operations": int(r[2])}
            for r in (await db.execute(by_agent_q)).all()
        }

        return {
            "total_cost_usd": float(row[0] or 0),
            "total_tokens_input": int(row[1] or 0),
            "total_tokens_output": int(row[2] or 0),
            "total_operations": int(row[3] or 0),
            "by_provider": by_provider,
            "by_agent": by_agent,
        }

    async def by_project(self, db: AsyncSession, project_id: uuid.UUID) -> dict:
        data = await self.overview(db, [project_id])
        data["project_id"] = str(project_id)
        return data

    async def by_pipeline(self, db: AsyncSession, pipeline_id: uuid.UUID) -> dict:
        from contentos_database.models import CostEntry as CostEntryModel

        q = select(
            func.coalesce(func.sum(CostEntryModel.estimated_cost_usd), 0.0),
            func.coalesce(func.sum(CostEntryModel.tokens_input), 0),
            func.coalesce(func.sum(CostEntryModel.tokens_output), 0),
            func.count(),
        ).where(CostEntryModel.pipeline_id == pipeline_id)
        row = (await db.execute(q)).one()
        entries_q = (
            select(CostEntryModel)
            .where(CostEntryModel.pipeline_id == pipeline_id)
            .order_by(CostEntryModel.created_at.desc())
            .limit(50)
        )
        entries = (await db.execute(entries_q)).scalars().all()
        return {
            "pipeline_id": str(pipeline_id),
            "total_cost_usd": float(row[0] or 0),
            "total_tokens_input": int(row[1] or 0),
            "total_tokens_output": int(row[2] or 0),
            "total_operations": int(row[3] or 0),
            "entries": [
                {
                    "agent": e.agent,
                    "provider": e.provider,
                    "model": e.model,
                    "estimated_cost_usd": e.estimated_cost_usd,
                    "tokens_input": e.tokens_input,
                    "tokens_output": e.tokens_output,
                    "duration_ms": e.duration_ms,
                    "from_cache": e.from_cache,
                    "created_at": e.created_at.isoformat(),
                }
                for e in entries
            ],
        }
