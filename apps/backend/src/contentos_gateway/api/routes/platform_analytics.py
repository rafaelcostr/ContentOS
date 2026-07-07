"""Platform OAuth analytics API — V5.4.1."""

from __future__ import annotations

import os
from uuid import UUID

from contentos_database.channel_credentials import credentials_connected
from contentos_database.models import Channel, Project, User
from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user, require_editor
from contentos_gateway.services.org_service import get_accessible_project, project_access_clause
from contentos_intelligence.application.platform_analytics import (
    list_recent_snapshots,
    platform_analytics_enabled,
    summarize_snapshots,
    sync_channel_analytics,
    sync_project_platform_analytics,
)
from contentos_shared.oauth_providers import ANALYTICS_OAUTH_SCOPES, SUPPORTED_OAUTH_PLATFORMS, get_oauth_config
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/analytics/platforms", tags=["Platform Analytics"])


class PlatformAnalyticsInfo(BaseModel):
    platform: str
    oauth_available: bool
    analytics_scopes: list[str]
    connected_channels: int


class SyncPlatformAnalyticsRequest(BaseModel):
    project_id: UUID
    platforms: list[str] | None = None
    limit: int | None = Field(default=None, ge=1, le=25)
    persist: bool = True


class PlatformMediaMetricsResponse(BaseModel):
    platform: str
    external_media_id: str | None = None
    title: str | None = None
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    watch_time_seconds: float | None = None
    engagement_rate: float | None = None
    published_at: str | None = None
    url: str | None = None


class PlatformAnalyticsReportResponse(BaseModel):
    platform: str
    channel_id: str
    channel_name: str
    synced: bool
    media_items: list[PlatformMediaMetricsResponse]
    channel_totals: dict
    needs_reconnect: bool = False
    error: str | None = None


class PlatformSyncResponse(BaseModel):
    project_id: str
    reports: list[PlatformAnalyticsReportResponse]
    snapshots_saved: int


class PlatformSnapshotResponse(BaseModel):
    id: str
    project_id: str
    channel_id: str | None
    platform: str
    external_media_id: str | None
    title: str | None
    metrics: dict
    channel_totals: dict | None
    fetched_at: str | None


@router.get("", response_model=list[PlatformAnalyticsInfo])
async def list_platform_analytics_capabilities(
    project_id: UUID = Query(...),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[PlatformAnalyticsInfo]:
    if not platform_analytics_enabled():
        raise HTTPException(status_code=503, detail="Platform analytics disabled")
    await get_accessible_project(db, project_id, user.id)
    result = await db.execute(
        select(Channel).where(Channel.project_id == project_id, Channel.is_active.is_(True))
    )
    channels = list(result.scalars().all())
    connected_by_platform: dict[str, int] = {}
    for ch in channels:
        if credentials_connected(ch.credentials):
            connected_by_platform[ch.platform] = connected_by_platform.get(ch.platform, 0) + 1
    return [
        PlatformAnalyticsInfo(
            platform=p,
            oauth_available=get_oauth_config(p) is not None,
            analytics_scopes=list(ANALYTICS_OAUTH_SCOPES.get(p, ())),
            connected_channels=connected_by_platform.get(p, 0),
        )
        for p in sorted(SUPPORTED_OAUTH_PLATFORMS)
    ]


@router.post("/sync", response_model=PlatformSyncResponse)
async def sync_platform_analytics(
    body: SyncPlatformAnalyticsRequest,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> PlatformSyncResponse:
    if not platform_analytics_enabled():
        raise HTTPException(status_code=503, detail="Platform analytics disabled")
    await get_accessible_project(db, body.project_id, user.id)
    result = await sync_project_platform_analytics(
        db,
        body.project_id,
        platforms=body.platforms,
        limit=body.limit,
        persist=body.persist,
    )
    await db.commit()
    if os.getenv("PERFORMANCE_LEARNING_AUTO_PROCESS", "false").lower() in ("1", "true", "yes"):
        try:
            from contentos_intelligence.application.performance_learning import (
                performance_learning_enabled,
                process_project_performance_learning,
            )

            if performance_learning_enabled():
                await process_project_performance_learning(db, body.project_id, persist=True)
                await db.commit()
        except Exception:
            pass
    return PlatformSyncResponse(
        project_id=result.project_id,
        snapshots_saved=result.snapshots_saved,
        reports=[
            PlatformAnalyticsReportResponse(
                platform=r.platform,
                channel_id=r.channel_id,
                channel_name=r.channel_name,
                synced=r.synced,
                media_items=[PlatformMediaMetricsResponse(**m.to_dict()) for m in r.media_items],
                channel_totals=r.channel_totals,
                needs_reconnect=r.needs_reconnect,
                error=r.error,
            )
            for r in result.reports
        ],
    )


@router.post("/channels/{channel_id}/sync", response_model=PlatformAnalyticsReportResponse)
async def sync_channel_platform_analytics(
    channel_id: UUID,
    limit: int | None = Query(default=None, ge=1, le=25),
    persist: bool = Query(default=True),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> PlatformAnalyticsReportResponse:
    if not platform_analytics_enabled():
        raise HTTPException(status_code=503, detail="Platform analytics disabled")
    result = await db.execute(
        select(Channel).join(Project).where(Channel.id == channel_id, project_access_clause(user.id))
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    report = await sync_channel_analytics(db, channel, limit=limit, persist=persist)
    await db.commit()
    return PlatformAnalyticsReportResponse(
        platform=report.platform,
        channel_id=report.channel_id,
        channel_name=report.channel_name,
        synced=report.synced,
        media_items=[PlatformMediaMetricsResponse(**m.to_dict()) for m in report.media_items],
        channel_totals=report.channel_totals,
        needs_reconnect=report.needs_reconnect,
        error=report.error,
    )


@router.get("/snapshots", response_model=list[PlatformSnapshotResponse])
async def get_platform_snapshots(
    project_id: UUID = Query(...),
    platform: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[PlatformSnapshotResponse]:
    await get_accessible_project(db, project_id, user.id)
    rows = await list_recent_snapshots(db, project_id, platform=platform, limit=limit)
    return [PlatformSnapshotResponse(**row) for row in rows]


@router.get("/summary")
async def platform_analytics_summary(
    project_id: UUID = Query(...),
    limit: int = Query(default=100, ge=1, le=200),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    await get_accessible_project(db, project_id, user.id)
    snapshots = await list_recent_snapshots(db, project_id, limit=limit)
    return summarize_snapshots(snapshots)
