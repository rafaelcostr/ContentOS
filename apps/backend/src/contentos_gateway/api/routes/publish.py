"""Publish status and configuration (Tier D4)."""

import os
from uuid import UUID

from contentos_database.channel_credentials import credentials_connected, fetch_project_credentials
from contentos_database.models import Channel, PlatformPublicationRow, Project, User
from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user, require_editor
from contentos_gateway.services.org_service import get_accessible_project, project_access_clause
from contentos_shared.audiovisual_qa import normalize_publish_mode, publish_mode_allows_live, publish_require_qa
from contentos_shared.oauth_providers import (
    SUPPORTED_OAUTH_PLATFORMS,
    get_oauth_config,
    list_configured_oauth_platforms,
)
from contentos_shared.plugins.loader import get_enabled_platforms
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/publish", tags=["Publishing"])


class PlatformPublishStatus(BaseModel):
    platform: str
    enabled: bool
    oauth_available: bool
    connected: bool


class PublishStatusResponse(BaseModel):
    publish_mode: str
    live_enabled: bool
    prepare_only_enabled: bool
    dry_run_enabled: bool
    publish_require_qa: bool
    configured_oauth_platforms: list[str]
    enabled_platforms: list[str]
    platforms: list[PlatformPublishStatus]
    project_id: UUID | None = None


class ProjectChannelStatus(BaseModel):
    id: UUID
    project_id: UUID
    platform: str
    name: str
    is_active: bool
    oauth_connected: bool


@router.get("/status", response_model=PublishStatusResponse)
async def publish_status(
    project_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> PublishStatusResponse:
    mode = normalize_publish_mode(os.getenv("PUBLISH_MODE", "dry_run"))
    enabled = set(get_enabled_platforms())
    connected: set[str] = set()

    if project_id:
        await get_accessible_project(db, project_id, user.id)
        db_creds = await fetch_project_credentials(db, project_id)
        connected = {p for p, c in db_creds.items() if credentials_connected(c)}

    platforms = [
        PlatformPublishStatus(
            platform=p,
            enabled=p in enabled,
            oauth_available=get_oauth_config(p) is not None,
            connected=p in connected,
        )
        for p in sorted(SUPPORTED_OAUTH_PLATFORMS)
    ]

    return PublishStatusResponse(
        publish_mode=mode,
        live_enabled=publish_mode_allows_live(mode),
        prepare_only_enabled=mode == "prepare_only",
        dry_run_enabled=mode == "dry_run",
        publish_require_qa=publish_require_qa(),
        configured_oauth_platforms=list_configured_oauth_platforms(),
        enabled_platforms=sorted(enabled),
        platforms=platforms,
        project_id=project_id,
    )


class PlatformPublicationAttempt(BaseModel):
    id: UUID
    project_id: UUID
    pipeline_id: UUID | None
    platform: str
    publish_mode: str
    status: str
    title: str | None
    external_id: str | None
    publish_url: str | None
    error: str | None
    created_at: str | None


@router.get("/attempts", response_model=list[PlatformPublicationAttempt])
async def list_publication_attempts(
    project_id: UUID = Query(...),
    pipeline_id: UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[PlatformPublicationAttempt]:
    await get_accessible_project(db, project_id, user.id)
    query = select(PlatformPublicationRow).where(PlatformPublicationRow.project_id == project_id)
    if pipeline_id:
        query = query.where(PlatformPublicationRow.pipeline_id == pipeline_id)
    query = query.order_by(PlatformPublicationRow.created_at.desc()).limit(limit)
    result = await db.execute(query)
    return [
        PlatformPublicationAttempt(
            id=row.id,
            project_id=row.project_id,
            pipeline_id=row.pipeline_id,
            platform=row.platform,
            publish_mode=row.publish_mode,
            status=row.status,
            title=row.title,
            external_id=row.external_id,
            publish_url=row.publish_url,
            error=row.error,
            created_at=row.created_at.isoformat() if row.created_at else None,
        )
        for row in result.scalars().all()
    ]


@router.get("/channels", response_model=list[ProjectChannelStatus])
async def list_publish_channels(
    project_id: UUID = Query(...),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[ProjectChannelStatus]:
    await get_accessible_project(db, project_id, user.id)
    result = await db.execute(
        select(Channel)
        .join(Project)
        .where(Channel.project_id == project_id, project_access_clause(user.id))
        .order_by(Channel.created_at.desc())
    )
    return [
        ProjectChannelStatus(
            id=c.id,
            project_id=c.project_id,
            platform=c.platform,
            name=c.name,
            is_active=c.is_active,
            oauth_connected=credentials_connected(c.credentials),
        )
        for c in result.scalars().all()
    ]


@router.post("/channels/{channel_id}/disconnect", status_code=204)
async def disconnect_channel(
    channel_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> None:
    result = await db.execute(
        select(Channel).join(Project).where(Channel.id == channel_id, project_access_clause(user.id))
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    channel.credentials = None
