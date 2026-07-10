"""Fetch competitor public metrics by platform — Growth OS Fase 7."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from contentos_growth.platform_registry import get_platform_profile, normalize_platform_id


def _media_items_payload(items) -> list[dict[str, Any]]:
    return [
        {
            "external_media_id": item.external_media_id,
            "title": item.title,
            **item.to_dict(),
        }
        for item in items
    ]


async def fetch_competitor_data(
    platform: str,
    handle: str,
    *,
    limit: int = 10,
) -> dict[str, Any]:
    """Return metrics payload to persist on growth_competitors.metrics."""
    normalized = normalize_platform_id(platform)
    now = datetime.now(timezone.utc).isoformat()
    profile = get_platform_profile(normalized)

    if normalized == "youtube":
        from contentos_intelligence.application.platform_analytics.youtube_public import (
            fetch_youtube_public_channel,
            resolve_youtube_api_key,
        )

        api_key = resolve_youtube_api_key()
        if not api_key:
            return {
                "sync_error": "YOUTUBE_API_KEY not configured",
                "last_synced_at": now,
            }
        items, totals = await fetch_youtube_public_channel(handle, api_key=api_key, limit=limit)
        if totals.get("error"):
            return {
                "channel_totals": totals,
                "media_items": [],
                "sync_error": totals.get("error"),
                "last_synced_at": now,
            }
        return {
            "channel_totals": totals,
            "media_items": _media_items_payload(items),
            "sync_error": None,
            "last_synced_at": now,
        }

    label = profile.label if profile else normalized
    if profile and not profile.analytics_supported:
        return {
            "sync_error": f"Competitor sync not available for {label} yet",
            "last_synced_at": now,
        }

    return {
        "sync_error": f"sync not implemented for platform: {normalized}",
        "last_synced_at": now,
    }
