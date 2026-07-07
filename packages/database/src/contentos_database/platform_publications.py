"""Persist platform publication audit rows."""

from __future__ import annotations

import os
import uuid
from typing import Any
from uuid import UUID

from contentos_database.models import PlatformPublicationRow
from contentos_database.session import get_session_factory, init_db
from sqlalchemy import desc, select


async def persist_platform_publications(
    project_id: UUID,
    pipeline_id: UUID | None,
    publish_mode: str,
    platforms: dict[str, Any],
    *,
    publication_status: str = "ready",
) -> int:
    """Insert one audit row per platform. Returns rows written."""
    if not platforms:
        return 0

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return 0

    session_factory = get_session_factory()
    if session_factory is None:
        init_db(database_url)
    session_factory = get_session_factory()
    if session_factory is None:
        return 0

    written = 0
    async with session_factory() as db:
        for platform, pub in platforms.items():
            if not isinstance(pub, dict):
                continue
            row = PlatformPublicationRow(
                id=uuid.uuid4(),
                project_id=project_id,
                pipeline_id=pipeline_id,
                platform=str(platform),
                publish_mode=publish_mode,
                status=str(pub.get("status") or publication_status),
                title=pub.get("title"),
                external_id=pub.get("external_id"),
                publish_url=pub.get("publish_url"),
                error=pub.get("error"),
                payload=pub.get("payload") if isinstance(pub.get("payload"), dict) else None,
            )
            db.add(row)
            written += 1
        await db.commit()
    return written


async def list_platform_publications(
    project_id: UUID,
    *,
    pipeline_id: UUID | None = None,
    limit: int = 50,
) -> list[PlatformPublicationRow]:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return []

    session_factory = get_session_factory()
    if session_factory is None:
        init_db(database_url)
    session_factory = get_session_factory()
    if session_factory is None:
        return []

    async with session_factory() as db:
        query = select(PlatformPublicationRow).where(PlatformPublicationRow.project_id == project_id)
        if pipeline_id:
            query = query.where(PlatformPublicationRow.pipeline_id == pipeline_id)
        query = query.order_by(desc(PlatformPublicationRow.created_at)).limit(max(1, min(limit, 200)))
        result = await db.execute(query)
        return list(result.scalars().all())
