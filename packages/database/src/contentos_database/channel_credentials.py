"""Load and merge platform credentials from project channels (Tier D4)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from contentos_database.models import Channel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def merge_credentials(
    env_credentials: dict[str, dict[str, Any]],
    db_credentials: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Merge env + DB credentials; DB values override env per platform."""
    merged: dict[str, dict[str, Any]] = {k: dict(v) for k, v in env_credentials.items()}
    for platform, creds in db_credentials.items():
        base = merged.get(platform, {})
        merged[platform] = {**base, **creds}
    return merged


async def fetch_project_credentials(
    db: AsyncSession,
    project_id: UUID,
) -> dict[str, dict[str, Any]]:
    """Load active channel credentials keyed by platform (latest channel wins)."""
    result = await db.execute(
        select(Channel)
        .where(Channel.project_id == project_id, Channel.is_active.is_(True))
        .order_by(Channel.created_at.desc())
    )
    credentials: dict[str, dict[str, Any]] = {}
    for channel in result.scalars().all():
        if not channel.credentials:
            continue
        platform = channel.platform.lower()
        if platform not in credentials:
            credentials[platform] = dict(channel.credentials)
    return credentials


def credentials_connected(credentials: dict[str, Any] | None) -> bool:
    if not credentials:
        return False
    return bool(credentials.get("access_token"))


def token_expired(credentials: dict[str, Any]) -> bool:
    expires_at = credentials.get("expires_at")
    if not expires_at:
        return False
    try:
        if isinstance(expires_at, (int, float)):
            exp = datetime.fromtimestamp(float(expires_at), tz=timezone.utc)
        else:
            exp = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
        return exp <= datetime.now(timezone.utc)
    except (TypeError, ValueError):
        return False
