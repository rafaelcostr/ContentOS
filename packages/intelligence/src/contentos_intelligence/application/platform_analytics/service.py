"""Platform analytics sync service — V5.4.1."""

from __future__ import annotations

import os
from typing import Any
from uuid import UUID

from contentos_intelligence.application.platform_analytics.fetchers import PLATFORM_FETCHERS
from contentos_intelligence.domain.platform_metrics import PlatformAnalyticsReport, PlatformSyncResult

try:
    from contentos_database.channel_credentials import credentials_connected
    from contentos_database.models import Channel, PlatformAnalyticsSnapshot
    from contentos_database.oauth_tokens import refresh_channel_token_if_needed
    from contentos_shared.oauth_providers import SUPPORTED_OAUTH_PLATFORMS
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession
except ImportError:  # pragma: no cover
    AsyncSession = object  # type: ignore[misc, assignment]
    Channel = PlatformAnalyticsSnapshot = object  # type: ignore[misc, assignment]


def platform_analytics_enabled() -> bool:
    return os.getenv("PLATFORM_ANALYTICS_ENABLED", "true").lower() in ("1", "true", "yes")


def platform_analytics_limit() -> int:
    try:
        return max(1, min(25, int(os.getenv("PLATFORM_ANALYTICS_MEDIA_LIMIT", "10"))))
    except ValueError:
        return 10


async def sync_channel_analytics(
    db: AsyncSession,
    channel: Channel,
    *,
    limit: int | None = None,
    persist: bool = True,
) -> PlatformAnalyticsReport:
    platform = channel.platform.lower()
    report = PlatformAnalyticsReport(
        platform=platform,
        channel_id=str(channel.id),
        channel_name=channel.name,
        synced=False,
    )
    if platform not in SUPPORTED_OAUTH_PLATFORMS:
        report.error = f"Unsupported platform: {platform}"
        return report
    if not credentials_connected(channel.credentials):
        report.error = "Channel not connected via OAuth"
        return report

    await refresh_channel_token_if_needed(channel)
    creds = dict(channel.credentials or {})
    fetcher = PLATFORM_FETCHERS.get(platform)
    if not fetcher:
        report.error = "No fetcher for platform"
        return report

    media_limit = limit or platform_analytics_limit()
    try:
        items, totals = await fetcher(creds, limit=media_limit)
    except Exception as exc:  # noqa: BLE001
        report.error = str(exc)[:300]
        return report

    if totals.get("needs_reconnect"):
        report.needs_reconnect = True
        report.error = totals.get("error") or "Reconnect OAuth with analytics scopes"
        return report
    if totals.get("error") and not items:
        report.error = str(totals.get("error"))
        return report

    report.media_items = items
    report.channel_totals = {k: v for k, v in totals.items() if k not in ("error", "needs_reconnect")}
    report.synced = True

    if platform == "youtube" and report.channel_totals.get("youtube_channel_id"):
        creds = dict(channel.credentials or {})
        creds["youtube_channel_id"] = report.channel_totals["youtube_channel_id"]
        channel.credentials = creds

    if persist and report.synced:
        saved = 0
        if report.channel_totals:
            overview_id = report.channel_totals.get("youtube_channel_id") or f"channel:{channel.id}"
            db.add(
                PlatformAnalyticsSnapshot(
                    project_id=channel.project_id,
                    channel_id=channel.id,
                    platform=platform,
                    external_media_id=f"overview:{overview_id}",
                    title=report.channel_totals.get("title") or channel.name,
                    metrics={"kind": "channel_overview", **report.channel_totals},
                    channel_totals=report.channel_totals,
                )
            )
            saved += 1
        for item in items:
            db.add(
                PlatformAnalyticsSnapshot(
                    project_id=channel.project_id,
                    channel_id=channel.id,
                    platform=platform,
                    external_media_id=item.external_media_id,
                    title=item.title,
                    metrics=item.to_dict(),
                    channel_totals=report.channel_totals or None,
                )
            )
            saved += 1
        if saved:
            await db.flush()
    return report


async def sync_project_platform_analytics(
    db: AsyncSession,
    project_id: UUID,
    *,
    platforms: list[str] | None = None,
    limit: int | None = None,
    persist: bool = True,
) -> PlatformSyncResult:
    allowed = {p.lower() for p in (platforms or SUPPORTED_OAUTH_PLATFORMS)}
    result = await db.execute(
        select(Channel).where(
            Channel.project_id == project_id,
            Channel.is_active.is_(True),
            Channel.platform.in_(sorted(allowed)),
        )
    )
    channels = list(result.scalars().all())
    reports: list[PlatformAnalyticsReport] = []
    saved = 0
    for channel in channels:
        report = await sync_channel_analytics(db, channel, limit=limit, persist=persist)
        reports.append(report)
        if persist and report.synced:
            saved += len(report.media_items)
    return PlatformSyncResult(project_id=str(project_id), reports=reports, snapshots_saved=saved)


async def list_recent_snapshots(
    db: AsyncSession,
    project_id: UUID,
    *,
    platform: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    query = (
        select(PlatformAnalyticsSnapshot)
        .where(PlatformAnalyticsSnapshot.project_id == project_id)
        .order_by(PlatformAnalyticsSnapshot.fetched_at.desc())
        .limit(min(limit, 200))
    )
    if platform:
        query = query.where(PlatformAnalyticsSnapshot.platform == platform.lower())
    rows = (await db.execute(query)).scalars().all()
    return [
        {
            "id": str(r.id),
            "project_id": str(r.project_id),
            "channel_id": str(r.channel_id) if r.channel_id else None,
            "platform": r.platform,
            "external_media_id": r.external_media_id,
            "title": r.title,
            "metrics": r.metrics,
            "channel_totals": r.channel_totals,
            "fetched_at": r.fetched_at.isoformat() if r.fetched_at else None,
        }
        for r in rows
    ]


def summarize_snapshots(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    by_platform: dict[str, dict[str, Any]] = {}
    for snap in snapshots:
        metrics = snap.get("metrics") or {}
        if metrics.get("kind") == "channel_overview":
            continue
        platform = snap.get("platform", "unknown")
        bucket = by_platform.setdefault(
            platform,
            {"platform": platform, "media_count": 0, "total_views": 0, "total_likes": 0, "total_comments": 0},
        )
        bucket["media_count"] += 1
        bucket["total_views"] += int(metrics.get("views") or 0)
        bucket["total_likes"] += int(metrics.get("likes") or 0)
        bucket["total_comments"] += int(metrics.get("comments") or 0)
    return {"platforms": list(by_platform.values()), "snapshot_count": len(snapshots)}


async def get_latest_channel_overview(
    db: AsyncSession,
    channel_id: UUID,
    *,
    platform: str | None = None,
) -> dict[str, Any] | None:
    query = (
        select(PlatformAnalyticsSnapshot)
        .where(PlatformAnalyticsSnapshot.channel_id == channel_id)
        .order_by(PlatformAnalyticsSnapshot.fetched_at.desc())
        .limit(50)
    )
    if platform:
        query = query.where(PlatformAnalyticsSnapshot.platform == platform.lower())

    rows = list((await db.execute(query)).scalars().all())
    overview_row = None
    media_items: list[dict[str, Any]] = []
    for row in rows:
        metrics = row.metrics or {}
        is_overview = metrics.get("kind") == "channel_overview" or str(row.external_media_id or "").startswith("overview:")
        if is_overview:
            if overview_row is None:
                overview_row = row
            continue
        media_items.append(
            {
                "id": str(row.id),
                "external_media_id": row.external_media_id,
                "title": row.title,
                "metrics": metrics,
                "fetched_at": row.fetched_at.isoformat() if row.fetched_at else None,
            }
        )

    if overview_row is None:
        return None

    metrics = overview_row.metrics or {}
    return {
        "id": str(overview_row.id),
        "channel_id": str(overview_row.channel_id) if overview_row.channel_id else None,
        "platform": overview_row.platform,
        "fetched_at": overview_row.fetched_at.isoformat() if overview_row.fetched_at else None,
        "channel_totals": overview_row.channel_totals or metrics,
        "media_items": media_items,
    }


def build_youtube_connection_status(channel: Channel) -> dict[str, Any]:
    creds = dict(channel.credentials or {})
    connected = credentials_connected(creds)
    expires_at = creds.get("expires_at")
    return {
        "channel_id": str(channel.id),
        "project_id": str(channel.project_id),
        "platform": channel.platform,
        "name": channel.name,
        "is_active": channel.is_active,
        "oauth_connected": connected,
        "has_refresh_token": bool(creds.get("refresh_token")),
        "token_expires_at": expires_at,
        "oauth_connected_at": creds.get("oauth_connected_at"),
        "youtube_channel_id": creds.get("youtube_channel_id"),
    }
