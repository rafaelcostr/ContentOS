"""Persistence for A/B variant sets — Epic 6."""

from __future__ import annotations

import os
import uuid
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from contentos_intelligence.domain.ab_testing import AbTestReport


class AbVariantRepository:
    async def save_report(self, db: AsyncSession, report: AbTestReport) -> None:
        if not report.pipeline_id:
            return
        from contentos_database.models import AbVariantRow

        await db.execute(
            delete(AbVariantRow).where(AbVariantRow.pipeline_id == report.pipeline_id)
        )
        for dim in report.dimensions:
            row = AbVariantRow(
                id=uuid.uuid4(),
                project_id=report.project_id,
                pipeline_id=report.pipeline_id,
                dimension=dim.dimension,
                variants=[v.to_dict() for v in dim.variants],
                winner_index=dim.winner_index,
                winner=dim.winner.to_dict() if dim.winner else None,
            )
            db.add(row)
        await db.flush()

    async def list_by_pipeline(self, db: AsyncSession, pipeline_id: UUID) -> list[dict[str, Any]]:
        from contentos_database.models import AbVariantRow

        rows = (
            await db.execute(
                select(AbVariantRow)
                .where(AbVariantRow.pipeline_id == pipeline_id)
                .order_by(AbVariantRow.dimension)
            )
        ).scalars().all()
        return [_row_to_dict(r) for r in rows]

    def save_report_sync(self, report: AbTestReport) -> None:
        """Sync persist for agents-worker when DATABASE_URL is set."""
        database_url = os.getenv("DATABASE_URL", "")
        if not database_url or not report.pipeline_id:
            return
        sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace(
            "postgresql://", "postgresql+psycopg2://"
        )
        try:
            from contentos_database.models import AbVariantRow
            from sqlalchemy import create_engine

            engine = create_engine(sync_url, pool_pre_ping=True)
            with Session(engine) as session:
                session.execute(
                    delete(AbVariantRow).where(AbVariantRow.pipeline_id == report.pipeline_id)
                )
                for dim in report.dimensions:
                    session.add(
                        AbVariantRow(
                            id=uuid.uuid4(),
                            project_id=report.project_id,
                            pipeline_id=report.pipeline_id,
                            dimension=dim.dimension,
                            variants=[v.to_dict() for v in dim.variants],
                            winner_index=dim.winner_index,
                            winner=dim.winner.to_dict() if dim.winner else None,
                        )
                    )
                session.commit()
        except Exception:
            pass


def _row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "project_id": str(row.project_id),
        "pipeline_id": str(row.pipeline_id),
        "dimension": row.dimension,
        "variants": row.variants or [],
        "winner_index": row.winner_index,
        "winner": row.winner,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
