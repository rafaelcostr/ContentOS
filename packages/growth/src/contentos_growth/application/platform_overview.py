"""Platform overview facade — Growth OS Fase 11."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from contentos_growth.platform_registry import get_platform_profile, normalize_platform_id

try:
    from contentos_database.channel_credentials import credentials_connected
    from contentos_database.models import Channel
    from contentos_intelligence.application.platform_analytics.service import get_latest_channel_overview
    from sqlalchemy.ext.asyncio import AsyncSession
except ImportError:  # pragma: no cover
    AsyncSession = object  # type: ignore[misc, assignment]
    Channel = object  # type: ignore[misc, assignment]


async def get_channel_overview(
    db: AsyncSession,
    channel_id: UUID,
    *,
    platform: str,
) -> dict[str, Any] | None:
    normalized = normalize_platform_id(platform)
    overview = await get_latest_channel_overview(db, channel_id, platform=normalized)
    if not overview:
        return None
    overview.setdefault("platform", normalized)
    return overview


def build_platform_connection_status(channel: Channel) -> dict[str, Any]:
    normalized = normalize_platform_id(channel.platform)
    profile = get_platform_profile(normalized)
    creds = dict(channel.credentials or {})
    connected = credentials_connected(creds)
    return {
        "channel_id": str(channel.id),
        "project_id": str(channel.project_id),
        "platform": normalized,
        "platform_label": profile.label if profile else normalized,
        "name": channel.name,
        "is_active": channel.is_active,
        "oauth_connected": connected,
        "analytics_supported": bool(profile and profile.analytics_supported),
        "publish_supported": bool(profile and profile.publish_supported),
        "has_refresh_token": bool(creds.get("refresh_token")),
        "token_expires_at": creds.get("expires_at"),
        "needs_reconnect": not connected,
    }
