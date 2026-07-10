"""YouTube channel integration routes — Growth OS Fase 3."""

from __future__ import annotations

from uuid import UUID

from contentos_database.models import Channel, Project, User
from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user, require_editor
from contentos_gateway.services.org_service import project_access_clause
from contentos_growth import GrowthService
from contentos_growth.infrastructure.sqlalchemy_repository import SqlAlchemyGrowthRepository
from contentos_intelligence.application.platform_analytics.service import (
    build_youtube_connection_status,
    get_latest_channel_overview,
    platform_analytics_enabled,
    platform_analytics_limit,
    sync_channel_analytics,
)
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/channels", tags=["YouTube Integration"])


class YouTubeConnectionStatusResponse(BaseModel):
    channel_id: str
    project_id: str
    platform: str
    name: str
    is_active: bool
    oauth_connected: bool
    has_refresh_token: bool
    token_expires_at: str | None = None
    oauth_connected_at: str | None = None
    youtube_channel_id: str | None = None
    last_synced_at: str | None = None
    subscriber_count: int | None = None
    view_count: int | None = None
    video_count: int | None = None
    shorts_count: int | None = None
    playlists_count: int | None = None
    needs_reconnect: bool = False


class YouTubeMediaItemResponse(BaseModel):
    id: str
    external_media_id: str | None = None
    title: str | None = None
    metrics: dict = Field(default_factory=dict)
    fetched_at: str | None = None


class YouTubeSnapshotResponse(BaseModel):
    id: str
    channel_id: str | None
    fetched_at: str | None
    channel_totals: dict = Field(default_factory=dict)
    media_items: list[YouTubeMediaItemResponse] = Field(default_factory=list)


class YouTubeSyncResponse(BaseModel):
    synced: bool
    needs_reconnect: bool = False
    error: str | None = None
    channel_totals: dict = Field(default_factory=dict)
    media_items: list[dict] = Field(default_factory=list)
    snapshots_saved: int = 0


class ChannelAnalysisResponse(BaseModel):
    channel_id: str
    project_id: str
    platform: str
    channel_name: str
    score: float
    summary: str
    report: dict = Field(default_factory=dict)
    profile: dict = Field(default_factory=dict)
    recommendations: list[dict] = Field(default_factory=list)
    analyzed_at: str


class ChannelAnalysisHistoryItem(BaseModel):
    id: str
    channel_id: str | None
    project_id: str
    score: float
    summary: str
    report: dict = Field(default_factory=dict)
    created_at: str | None


async def _get_youtube_channel(
    db: AsyncSession,
    channel_id: UUID,
    user_id: UUID,
) -> Channel:
    result = await db.execute(
        select(Channel).join(Project).where(Channel.id == channel_id, project_access_clause(user_id))
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    if channel.platform.lower() != "youtube":
        raise HTTPException(status_code=400, detail="Channel is not a YouTube channel")
    return channel


@router.get("/{channel_id}/youtube/status", response_model=YouTubeConnectionStatusResponse)
async def youtube_connection_status(
    channel_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> YouTubeConnectionStatusResponse:
    channel = await _get_youtube_channel(db, channel_id, user.id)
    status = build_youtube_connection_status(channel)
    overview = await get_latest_channel_overview(db, channel_id, platform="youtube")
    totals = (overview or {}).get("channel_totals") or {}
    playlists = totals.get("playlists") or []
    return YouTubeConnectionStatusResponse(
        **status,
        last_synced_at=(overview or {}).get("fetched_at"),
        subscriber_count=totals.get("subscriber_count"),
        view_count=totals.get("view_count"),
        video_count=totals.get("video_count"),
        shorts_count=totals.get("shorts_count"),
        playlists_count=len(playlists) if isinstance(playlists, list) else None,
        needs_reconnect=not status["oauth_connected"],
    )


@router.post("/{channel_id}/youtube/sync", response_model=YouTubeSyncResponse)
async def youtube_sync_channel(
    channel_id: UUID,
    limit: int | None = Query(default=None, ge=1, le=25),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> YouTubeSyncResponse:
    if not platform_analytics_enabled():
        raise HTTPException(status_code=503, detail="Platform analytics disabled")
    channel = await _get_youtube_channel(db, channel_id, user.id)
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
    return YouTubeSyncResponse(
        synced=report.synced,
        needs_reconnect=report.needs_reconnect,
        error=report.error,
        channel_totals=report.channel_totals,
        media_items=[item.to_dict() for item in report.media_items],
        snapshots_saved=snapshots_saved,
    )


@router.get("/{channel_id}/youtube/data", response_model=YouTubeSnapshotResponse | None)
async def youtube_latest_data(
    channel_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> YouTubeSnapshotResponse | None:
    await _get_youtube_channel(db, channel_id, user.id)
    overview = await get_latest_channel_overview(db, channel_id, platform="youtube")
    if not overview:
        return None
    return YouTubeSnapshotResponse(
        id=overview["id"],
        channel_id=overview.get("channel_id"),
        fetched_at=overview.get("fetched_at"),
        channel_totals=overview.get("channel_totals") or {},
        media_items=[YouTubeMediaItemResponse(**item) for item in overview.get("media_items", [])],
    )


@router.post("/{channel_id}/analyze", response_model=ChannelAnalysisResponse)
async def analyze_channel(
    channel_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> ChannelAnalysisResponse:
    result = await db.execute(
        select(Channel).join(Project).where(Channel.id == channel_id, project_access_clause(user.id))
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    overview = await get_latest_channel_overview(db, channel_id, platform=channel.platform.lower())
    if not overview:
        raise HTTPException(
            status_code=400,
            detail="Nenhum dado sincronizado para este canal. Execute a sincronização da plataforma antes da análise.",
        )

    service = GrowthService(SqlAlchemyGrowthRepository(db))
    try:
        analysis = await service.analyze_channel(
            db=db,
            channel_id=channel_id,
            project_id=channel.project_id,
            platform=channel.platform,
            channel_name=channel.name,
            overview=overview,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await db.commit()

    return ChannelAnalysisResponse(**analysis.to_dict())


@router.get("/{channel_id}/analysis", response_model=ChannelAnalysisResponse | None)
async def get_channel_analysis(
    channel_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ChannelAnalysisResponse | None:
    result = await db.execute(
        select(Channel).join(Project).where(Channel.id == channel_id, project_access_clause(user.id))
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    profile = await GrowthService(SqlAlchemyGrowthRepository(db)).get_channel_profile(channel_id)
    if not profile or not profile.analyzed_at:
        return None

    return ChannelAnalysisResponse(
        channel_id=profile.channel_id,
        project_id=profile.project_id,
        platform=profile.platform,
        channel_name=profile.name,
        score=profile.score,
        summary=str(profile.report.get("summary") or ""),
        report=profile.report,
        profile=profile.profile,
        recommendations=[],
        analyzed_at=profile.analyzed_at or "",
    )


@router.get("/{channel_id}/analysis/history", response_model=list[ChannelAnalysisHistoryItem])
async def get_channel_analysis_history(
    channel_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[ChannelAnalysisHistoryItem]:
    result = await db.execute(
        select(Channel).join(Project).where(Channel.id == channel_id, project_access_clause(user.id))
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Channel not found")

    history = await GrowthService(SqlAlchemyGrowthRepository(db)).list_channel_analysis_history(channel_id, limit=limit)
    return [ChannelAnalysisHistoryItem(**item) for item in history]
