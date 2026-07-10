"""Generic platform channel routes — Growth OS Fase 11."""

from __future__ import annotations

from uuid import UUID

from contentos_database.models import Channel, Project, User
from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user, require_editor
from contentos_gateway.services.org_service import project_access_clause
from contentos_growth.application.platform_overview import build_platform_connection_status, get_channel_overview
from contentos_intelligence.application.platform_analytics.service import (
    platform_analytics_enabled,
    platform_analytics_limit,
    sync_channel_analytics,
)
from contentos_shared.oauth_providers import SUPPORTED_OAUTH_PLATFORMS
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/channels", tags=["Platform Integration"])


class PlatformConnectionStatusResponse(BaseModel):
    channel_id: str
    project_id: str
    platform: str
    platform_label: str
    name: str
    is_active: bool
    oauth_connected: bool
    analytics_supported: bool
    publish_supported: bool
    needs_reconnect: bool
    last_synced_at: str | None = None
    channel_totals: dict = Field(default_factory=dict)


class PlatformSyncResponse(BaseModel):
    synced: bool
    platform: str
    needs_reconnect: bool = False
    error: str | None = None
    channel_totals: dict = Field(default_factory=dict)
    media_items: list[dict] = Field(default_factory=list)
    snapshots_saved: int = 0


class PlatformSnapshotResponse(BaseModel):
    id: str
    channel_id: str | None = None
    platform: str
    fetched_at: str | None = None
    channel_totals: dict = Field(default_factory=dict)
    media_items: list[dict] = Field(default_factory=list)


async def _get_channel(db: AsyncSession, channel_id: UUID, user_id: UUID) -> Channel:
    result = await db.execute(
        select(Channel).join(Project).where(Channel.id == channel_id, project_access_clause(user_id))
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return channel


@router.get("/{channel_id}/platform/status", response_model=PlatformConnectionStatusResponse)
async def platform_connection_status(
    channel_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> PlatformConnectionStatusResponse:
    channel = await _get_channel(db, channel_id, user.id)
    status = build_platform_connection_status(channel)
    overview = await get_channel_overview(db, channel_id, platform=channel.platform)
    totals = (overview or {}).get("channel_totals") or {}
    return PlatformConnectionStatusResponse(
        **status,
        last_synced_at=(overview or {}).get("fetched_at"),
        channel_totals=totals,
        needs_reconnect=status["needs_reconnect"] or not status["oauth_connected"],
    )


@router.post("/{channel_id}/platform/sync", response_model=PlatformSyncResponse)
async def platform_sync_channel(
    channel_id: UUID,
    limit: int | None = Query(default=None, ge=1, le=25),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> PlatformSyncResponse:
    if not platform_analytics_enabled():
        raise HTTPException(status_code=503, detail="Platform analytics disabled")
    channel = await _get_channel(db, channel_id, user.id)
    platform = channel.platform.lower()
    if platform not in SUPPORTED_OAUTH_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Platform sync not supported: {platform}")
    report = await sync_channel_analytics(
        db,
        channel,
        limit=limit or platform_analytics_limit(),
        persist=True,
    )
    await db.commit()
    snapshots_saved = 0
    if report.synced:
        snapshots_saved = len(report.media_items) + (1 if report.channel_totals else 0)
    return PlatformSyncResponse(
        synced=report.synced,
        platform=platform,
        needs_reconnect=report.needs_reconnect,
        error=report.error,
        channel_totals=report.channel_totals,
        media_items=[item.to_dict() for item in report.media_items],
        snapshots_saved=snapshots_saved,
    )


@router.get("/{channel_id}/platform/data", response_model=PlatformSnapshotResponse | None)
async def platform_latest_data(
    channel_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> PlatformSnapshotResponse | None:
    channel = await _get_channel(db, channel_id, user.id)
    overview = await get_channel_overview(db, channel_id, platform=channel.platform)
    if not overview:
        return None
    return PlatformSnapshotResponse(
        id=overview["id"],
        channel_id=overview.get("channel_id"),
        platform=overview.get("platform") or channel.platform,
        fetched_at=overview.get("fetched_at"),
        channel_totals=overview.get("channel_totals") or {},
        media_items=overview.get("media_items") or [],
    )
