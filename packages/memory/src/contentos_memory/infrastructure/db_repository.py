"""Database repository for project memory."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import UUID

from contentos_memory.domain.project_memory import ProjectMemoryData
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def _row_to_data(row) -> ProjectMemoryData:
    return ProjectMemoryData(
        project_id=row.project_id,
        tone=row.tone or "",
        vocabulary=list(row.vocabulary or []),
        cta=row.cta or "",
        avg_duration=row.avg_duration,
        hook_style=row.hook_style or "",
        niche=row.niche or "",
        goal=row.goal or "",
        style=dict(row.style or {}),
        history=list(row.history or []),
        humor_level=row.humor_level,
        pace=row.pace or "",
        visual_style=dict(row.visual_style or {}),
        narrator_persona=row.narrator_persona or "",
        preferred_formats=list(row.preferred_formats or []),
        hook_patterns=list(row.hook_patterns or []),
        cta_style=row.cta_style or "",
    )


def _apply_data_to_row(row, data: ProjectMemoryData, *, now: datetime) -> None:
    row.tone = data.tone or None
    row.vocabulary = data.vocabulary or None
    row.cta = data.cta or None
    row.avg_duration = data.avg_duration
    row.hook_style = data.hook_style or None
    row.niche = data.niche or None
    row.goal = data.goal or None
    row.style = data.style or None
    row.history = data.history or None
    row.humor_level = data.humor_level
    row.pace = data.pace or None
    row.visual_style = data.visual_style or None
    row.narrator_persona = data.narrator_persona or None
    row.preferred_formats = data.preferred_formats or None
    row.hook_patterns = data.hook_patterns or None
    row.cta_style = data.cta_style or None
    row.updated_at = now


def _new_row(data: ProjectMemoryData, *, now: datetime):
    from contentos_database.models import ProjectMemory

    return ProjectMemory(
        project_id=data.project_id,
        tone=data.tone or None,
        vocabulary=data.vocabulary or None,
        cta=data.cta or None,
        avg_duration=data.avg_duration,
        hook_style=data.hook_style or None,
        niche=data.niche or None,
        goal=data.goal or None,
        style=data.style or None,
        history=data.history or None,
        humor_level=data.humor_level,
        pace=data.pace or None,
        visual_style=data.visual_style or None,
        narrator_persona=data.narrator_persona or None,
        preferred_formats=data.preferred_formats or None,
        hook_patterns=data.hook_patterns or None,
        cta_style=data.cta_style or None,
        updated_at=now,
    )


class MemoryRepository:
    async def get(self, db: AsyncSession, project_id: UUID) -> ProjectMemoryData:
        from contentos_database.models import ProjectMemory

        result = await db.execute(select(ProjectMemory).where(ProjectMemory.project_id == project_id))
        row = result.scalar_one_or_none()
        if row:
            return _row_to_data(row)
        return ProjectMemoryData.empty(project_id)

    async def upsert(self, db: AsyncSession, data: ProjectMemoryData) -> ProjectMemoryData:
        from contentos_database.models import ProjectMemory

        result = await db.execute(select(ProjectMemory).where(ProjectMemory.project_id == data.project_id))
        row = result.scalar_one_or_none()
        now = datetime.now(UTC)
        if row:
            _apply_data_to_row(row, data, now=now)
        else:
            row = _new_row(data, now=now)
            db.add(row)
        await db.flush()
        return _row_to_data(row)

    async def create_empty(self, db: AsyncSession, project_id: UUID) -> ProjectMemoryData:
        return await self.upsert(db, ProjectMemoryData.empty(project_id))


def load_sync(project_id: UUID) -> ProjectMemoryData:
    """Sync load for Celery workers."""
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        return ProjectMemoryData.empty(project_id)

    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace(
        "postgresql://", "postgresql+psycopg2://"
    )
    try:
        from contentos_database.models import ProjectMemory
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        engine = create_engine(sync_url, pool_pre_ping=True)
        with Session(engine) as session:
            row = session.get(ProjectMemory, project_id)
            if row:
                return _row_to_data(row)
    except Exception:
        pass
    return ProjectMemoryData.empty(project_id)


def upsert_sync(data: ProjectMemoryData) -> bool:
    """Sync upsert for Celery workers."""
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        return False
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace(
        "postgresql://", "postgresql+psycopg2://"
    )
    try:
        from contentos_database.models import ProjectMemory
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        engine = create_engine(sync_url, pool_pre_ping=True)
        with Session(engine) as session:
            row = session.get(ProjectMemory, data.project_id)
            now = datetime.now(UTC)
            if row:
                _apply_data_to_row(row, data, now=now)
            else:
                row = _new_row(data, now=now)
                session.add(row)
            session.commit()
        return True
    except Exception:
        return False
