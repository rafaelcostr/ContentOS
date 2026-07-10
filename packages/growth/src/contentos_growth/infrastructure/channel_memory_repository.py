"""Channel memory persistence — Growth OS Fase 6."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contentos_growth.channel_memory_model import ChannelMemoryData


def _row_to_data(row) -> ChannelMemoryData:
    return ChannelMemoryData(
        channel_id=row.channel_id,
        project_id=row.project_id,
        winning_videos=list(row.winning_videos or []),
        losing_videos=list(row.losing_videos or []),
        top_hooks=list(row.top_hooks or []),
        top_ctas=list(row.top_ctas or []),
        top_themes=list(row.top_themes or []),
        top_hashtags=list(row.top_hashtags or []),
        best_posting_hours=list(row.best_posting_hours or []),
        insights=list(row.insights or []),
        notes=row.notes or "",
    )


def _apply_data_to_row(row, data: ChannelMemoryData, *, now: datetime) -> None:
    row.project_id = data.project_id
    row.winning_videos = data.winning_videos or None
    row.losing_videos = data.losing_videos or None
    row.top_hooks = data.top_hooks or None
    row.top_ctas = data.top_ctas or None
    row.top_themes = data.top_themes or None
    row.top_hashtags = data.top_hashtags or None
    row.best_posting_hours = data.best_posting_hours or None
    row.insights = data.insights or None
    row.notes = data.notes or ""
    row.updated_at = now


class ChannelMemoryRepository:
    async def get(self, db: AsyncSession, channel_id: UUID) -> ChannelMemoryData | None:
        from contentos_database.models import Channel, ChannelMemoryRow

        channel = (await db.execute(select(Channel).where(Channel.id == channel_id))).scalar_one_or_none()
        if not channel:
            return None
        row = (await db.execute(select(ChannelMemoryRow).where(ChannelMemoryRow.channel_id == channel_id))).scalar_one_or_none()
        if not row:
            return ChannelMemoryData.empty(channel_id, channel.project_id)
        return _row_to_data(row)

    async def upsert(self, db: AsyncSession, data: ChannelMemoryData) -> ChannelMemoryData:
        from contentos_database.models import ChannelMemoryRow

        now = datetime.now(UTC)
        row = (
            await db.execute(select(ChannelMemoryRow).where(ChannelMemoryRow.channel_id == data.channel_id))
        ).scalar_one_or_none()
        if row:
            _apply_data_to_row(row, data, now=now)
        else:
            row = ChannelMemoryRow(
                channel_id=data.channel_id,
                project_id=data.project_id,
                created_at=now,
                updated_at=now,
            )
            _apply_data_to_row(row, data, now=now)
            db.add(row)
        await db.flush()
        return _row_to_data(row)


def load_sync(channel_id: UUID) -> ChannelMemoryData | None:
    """Sync load for Celery workers and prompt injection."""
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        return None

    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace(
        "postgresql://", "postgresql+psycopg2://"
    )
    try:
        from contentos_database.models import Channel, ChannelMemoryRow
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        engine = create_engine(sync_url, pool_pre_ping=True)
        with Session(engine) as session:
            channel = session.get(Channel, channel_id)
            if not channel:
                return None
            row = session.get(ChannelMemoryRow, channel_id)
            if row:
                return _row_to_data(row)
            return ChannelMemoryData.empty(channel_id, channel.project_id)
    except Exception:
        return None
