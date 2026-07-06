"""Persistence for multi-content artifacts — Epic 2a."""

from __future__ import annotations

import os
import uuid
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from contentos_intelligence.domain.multi_content import MultiContentReport


class MultiContentRepository:
    async def save_report(self, db: AsyncSession, report: MultiContentReport) -> None:
        if not report.pipeline_id:
            return
        from contentos_database.models import MultiContentArtifactRow

        pid = UUID(str(report.pipeline_id))
        await db.execute(delete(MultiContentArtifactRow).where(MultiContentArtifactRow.pipeline_id == pid))
        for artifact in report.artifacts:
            row = MultiContentArtifactRow(
                id=uuid.uuid4(),
                project_id=UUID(str(report.project_id)),
                pipeline_id=pid,
                format=artifact.format,
                title=artifact.title,
                content_text=artifact.content,
                metadata_=artifact.data,
                source=artifact.source,
            )
            db.add(row)
        await db.flush()

    async def list_by_pipeline(self, db: AsyncSession, pipeline_id: UUID) -> list[dict[str, Any]]:
        from contentos_database.models import MultiContentArtifactRow

        rows = (
            await db.execute(
                select(MultiContentArtifactRow)
                .where(MultiContentArtifactRow.pipeline_id == pipeline_id)
                .order_by(MultiContentArtifactRow.format)
            )
        ).scalars().all()
        return [_row_to_dict(r) for r in rows]

    def save_report_sync(self, report: MultiContentReport) -> None:
        database_url = os.getenv("DATABASE_URL", "")
        if not database_url or not report.pipeline_id:
            return
        sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace(
            "postgresql://", "postgresql+psycopg2://"
        )
        try:
            from contentos_database.models import MultiContentArtifactRow
            from sqlalchemy import create_engine

            engine = create_engine(sync_url, pool_pre_ping=True)
            pid = UUID(str(report.pipeline_id))
            with Session(engine) as session:
                session.execute(
                    delete(MultiContentArtifactRow).where(MultiContentArtifactRow.pipeline_id == pid)
                )
                for artifact in report.artifacts:
                    session.add(
                        MultiContentArtifactRow(
                            id=uuid.uuid4(),
                            project_id=UUID(str(report.project_id)),
                            pipeline_id=pid,
                            format=artifact.format,
                            title=artifact.title,
                            content_text=artifact.content,
                            metadata_=artifact.data,
                            source=artifact.source,
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
        "format": row.format,
        "title": row.title,
        "content": row.content_text,
        "data": row.metadata_ or {},
        "source": row.source,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
