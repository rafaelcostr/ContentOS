"""Channel Memory API — per-channel patterns (Growth OS Fase 6)."""

from __future__ import annotations

from uuid import UUID

from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user, require_editor
from contentos_gateway.api.routes.channels import _get_accessible_channel
from contentos_growth.application.channel_analyzer import analyze_channel_snapshot
from contentos_growth.application.channel_memory_service import (
    get_channel_memory_service,
    reset_channel_memory_service_cache,
)
from contentos_intelligence.application.platform_analytics.service import get_latest_channel_overview
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/channels", tags=["Channel Memory"])


class ChannelMemoryResponse(BaseModel):
    channel_id: str
    project_id: str
    winning_videos: list[dict] = Field(default_factory=list)
    losing_videos: list[dict] = Field(default_factory=list)
    top_hooks: list[str] = Field(default_factory=list)
    top_ctas: list[str] = Field(default_factory=list)
    top_themes: list[str] = Field(default_factory=list)
    top_hashtags: list[str] = Field(default_factory=list)
    best_posting_hours: list[int] = Field(default_factory=list)
    insights: list[str] = Field(default_factory=list)
    notes: str = ""
    channel_context_preview: str = ""


class ChannelMemoryPatchBody(BaseModel):
    winning_videos: list[dict] | None = None
    losing_videos: list[dict] | None = None
    top_hooks: list[str] | None = None
    top_ctas: list[str] | None = None
    top_themes: list[str] | None = None
    top_hashtags: list[str] | None = None
    best_posting_hours: list[int] | None = None
    insights: list[str] | None = None
    notes: str | None = None


def _to_response(data) -> ChannelMemoryResponse:
    payload = data.to_dict()
    return ChannelMemoryResponse(**payload)


@router.get("/{channel_id}/memory", response_model=ChannelMemoryResponse)
async def get_channel_memory(
    channel_id: UUID,
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> ChannelMemoryResponse:
    channel = await _get_accessible_channel(db, channel_id, user.id)
    data = await get_channel_memory_service().get_async(db, channel_id)
    if not data:
        raise HTTPException(status_code=404, detail="Channel not found")
    if data.project_id != channel.project_id:
        raise HTTPException(status_code=404, detail="Channel not found")
    return _to_response(data)


@router.patch("/{channel_id}/memory", response_model=ChannelMemoryResponse)
async def patch_channel_memory(
    channel_id: UUID,
    body: ChannelMemoryPatchBody,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_editor()),
) -> ChannelMemoryResponse:
    await _get_accessible_channel(db, channel_id, user.id)
    patch = body.model_dump(exclude_unset=True)
    if not patch:
        raise HTTPException(status_code=400, detail="No channel memory fields provided")
    try:
        updated = await get_channel_memory_service().patch(db, channel_id, patch)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await db.commit()
    reset_channel_memory_service_cache()
    return _to_response(updated)


@router.post("/{channel_id}/memory/seed", response_model=ChannelMemoryResponse)
async def seed_channel_memory(
    channel_id: UUID,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_editor()),
) -> ChannelMemoryResponse:
    channel = await _get_accessible_channel(db, channel_id, user.id)
    overview = await get_latest_channel_overview(db, channel_id, platform=channel.platform.lower())
    if not overview:
        raise HTTPException(status_code=400, detail="Nenhum dado sincronizado para este canal.")

    try:
        analysis = analyze_channel_snapshot(
            channel_id=str(channel_id),
            project_id=str(channel.project_id),
            platform=channel.platform,
            channel_name=channel.name,
            overview=overview,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    memory = await get_channel_memory_service().seed_from_analysis(
        db,
        channel_id=channel_id,
        project_id=channel.project_id,
        analysis=analysis,
        overview=overview,
    )
    await db.commit()
    reset_channel_memory_service_cache()
    return _to_response(memory)
