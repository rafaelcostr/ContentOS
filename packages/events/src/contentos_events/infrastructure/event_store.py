"""PostgreSQL event store."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def store_sync(payload: dict[str, Any]) -> bool:
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        return False
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace(
        "postgresql://", "postgresql+psycopg2://"
    )
    try:
        from contentos_database.models import DomainEventRecord
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        engine = create_engine(sync_url, pool_pre_ping=True)
        with Session(engine) as session:
            row = DomainEventRecord(
                id=uuid.uuid4(),
                event_type=payload.get("type") or payload.get("event_type", "unknown"),
                pipeline_id=_uuid(payload.get("pipeline_id")),
                project_id=_uuid(payload.get("project_id")),
                job_id=_uuid(payload.get("job_id")),
                agent=payload.get("agent") or payload.get("step"),
                step=payload.get("step"),
                status=payload.get("status"),
                payload=payload.get("data") or payload.get("payload") or {},
                created_at=datetime.now(UTC),
            )
            session.add(row)
            session.commit()
        return True
    except Exception:
        return False


class EventStore:
    async def list_recent(self, db: AsyncSession, limit: int = 50) -> list[dict]:
        from contentos_database.models import DomainEventRecord

        result = await db.execute(
            select(DomainEventRecord).order_by(DomainEventRecord.created_at.desc()).limit(limit)
        )
        return [_row_to_dict(r) for r in result.scalars().all()]

    async def list_by_pipeline(self, db: AsyncSession, pipeline_id: UUID, limit: int = 100) -> list[dict]:
        from contentos_database.models import DomainEventRecord

        result = await db.execute(
            select(DomainEventRecord)
            .where(DomainEventRecord.pipeline_id == pipeline_id)
            .order_by(DomainEventRecord.created_at.desc())
            .limit(limit)
        )
        return [_row_to_dict(r) for r in result.scalars().all()]


def _uuid(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


def _row_to_dict(row) -> dict:
    return {
        "id": str(row.id),
        "type": row.event_type,
        "event_type": row.event_type,
        "pipeline_id": str(row.pipeline_id) if row.pipeline_id else None,
        "project_id": str(row.project_id) if row.project_id else None,
        "job_id": str(row.job_id) if row.job_id else None,
        "agent": row.agent,
        "step": row.step,
        "status": row.status,
        "data": row.payload or {},
        "timestamp": row.created_at.isoformat(),
    }
