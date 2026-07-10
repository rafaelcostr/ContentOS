"""Platform analytics aggregation for Growth reports — Fase 11."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from contentos_growth.domain import ChannelProfile
from contentos_growth.platform_registry import get_platform_profile, normalize_platform_id

try:
    from contentos_intelligence.application.platform_analytics import list_recent_snapshots, summarize_snapshots
    from sqlalchemy.ext.asyncio import AsyncSession
except ImportError:  # pragma: no cover
    AsyncSession = object  # type: ignore[misc, assignment]


async def aggregate_project_platforms(db: AsyncSession, project_id: UUID) -> dict[str, Any]:
    snapshots = await list_recent_snapshots(db, project_id, limit=120)
    return summarize_snapshots(snapshots)


def enrich_channel_health(
    channels: list[ChannelProfile],
    analytics_summary: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    platform_totals: dict[str, dict[str, Any]] = {}
    for row in (analytics_summary or {}).get("platforms") or []:
        platform_totals[normalize_platform_id(row.get("platform"))] = row

    health: list[dict[str, Any]] = []
    for channel in channels:
        normalized = normalize_platform_id(channel.platform)
        profile = get_platform_profile(normalized)
        status = "healthy"
        signals: list[str] = []

        if not channel.has_credentials:
            status = "disconnected"
            signals.append("OAuth não conectado")
        elif profile and not profile.analytics_supported:
            status = "planned"
            signals.append("Analytics ainda não disponível para esta plataforma")
        elif not channel.analyzed_at:
            status = "needs_attention"
            signals.append("Canal sem análise Growth")
        elif channel.score < 50:
            status = "needs_attention"
            signals.append(f"Growth score baixo ({channel.score:.0f})")

        totals = platform_totals.get(normalized) or {}
        health.append(
            {
                "channel_id": channel.channel_id,
                "name": channel.name,
                "platform": normalized,
                "platform_label": profile.label if profile else normalized,
                "score": channel.score,
                "status": status,
                "signals": signals,
                "analytics_supported": bool(profile and profile.analytics_supported),
                "recent_media_count": totals.get("media_count"),
                "recent_total_views": totals.get("total_views"),
            }
        )
    return health


def build_platform_context(
    *,
    platform: str,
    channel_name: str,
    overview: dict[str, Any] | None = None,
    memory_preview: str | None = None,
) -> str:
    profile = get_platform_profile(platform)
    label = profile.label if profile else platform
    lines = [f"Plataforma: {label}", f"Canal: {channel_name}"]
    if profile:
        lines.append(f"Formatos: {', '.join(profile.content_types)}")
        if profile.max_duration_seconds:
            lines.append(f"Duração alvo: até {profile.max_duration_seconds}s")
    if overview:
        totals = overview.get("channel_totals") or {}
        follower_field = profile.follower_field if profile else "followers_count"
        followers = totals.get(follower_field)
        if followers is not None:
            lines.append(f"Audiência: {followers:,}".replace(",", "."))
    if memory_preview:
        lines.append(memory_preview.strip())
    return "\n".join(lines)
