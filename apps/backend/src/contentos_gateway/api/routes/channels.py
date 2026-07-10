"""Channel registry — social channels for publishing and Growth AI."""

from uuid import UUID, uuid4

from contentos_database.models import Channel, Project, User
from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user, require_editor
from contentos_gateway.services.org_service import get_accessible_project, project_access_clause
from contentos_shared.oauth_providers import SUPPORTED_OAUTH_PLATFORMS
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/channels", tags=["Channels"])

_SUPPORTED_PLATFORMS = frozenset(SUPPORTED_OAUTH_PLATFORMS) | {"facebook", "threads", "pinterest", "linkedin", "x"}


class ChannelCreate(BaseModel):
    project_id: UUID
    platform: str
    name: str = Field(min_length=1, max_length=255)
    credentials: dict | None = None


class ChannelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None


class ChannelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    platform: str
    name: str
    is_active: bool
    has_credentials: bool


class ChannelDetailResponse(ChannelResponse):
    credentials: dict | None = None


def _channel_response(channel: Channel, *, include_credentials: bool = False) -> ChannelDetailResponse | ChannelResponse:
    payload = {
        "id": channel.id,
        "project_id": channel.project_id,
        "platform": channel.platform,
        "name": channel.name,
        "is_active": channel.is_active,
        "has_credentials": bool(channel.credentials),
    }
    if include_credentials:
        return ChannelDetailResponse(**payload, credentials=channel.credentials)
    return ChannelResponse(**payload)


async def _get_accessible_channel(
    db: AsyncSession,
    channel_id: UUID,
    user_id: UUID,
) -> Channel:
    result = await db.execute(
        select(Channel).join(Project).where(Channel.id == channel_id, project_access_clause(user_id))
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    return channel


def _normalize_platform(platform: str) -> str:
    normalized = platform.strip().lower()
    if normalized not in _SUPPORTED_PLATFORMS:
        supported = ", ".join(sorted(_SUPPORTED_PLATFORMS))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported platform '{platform}'. Supported: {supported}",
        )
    return normalized


@router.get("", response_model=list[ChannelResponse])
async def list_channels(
    project_id: UUID | None = None,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[ChannelResponse]:
    query = select(Channel).join(Project).where(project_access_clause(user.id))
    if project_id:
        query = query.where(Channel.project_id == project_id)
    result = await db.execute(query.order_by(Channel.created_at.desc()))
    return [_channel_response(channel) for channel in result.scalars().all()]


@router.get("/{channel_id}", response_model=ChannelDetailResponse)
async def get_channel(
    channel_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ChannelDetailResponse:
    channel = await _get_accessible_channel(db, channel_id, user.id)
    return _channel_response(channel, include_credentials=True)


@router.post("", response_model=ChannelDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_channel(
    body: ChannelCreate,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> ChannelDetailResponse:
    await get_accessible_project(db, body.project_id, user.id)

    channel = Channel(
        id=uuid4(),
        project_id=body.project_id,
        platform=_normalize_platform(body.platform),
        name=body.name.strip(),
        credentials=body.credentials,
        is_active=True,
    )
    db.add(channel)
    await db.flush()
    return _channel_response(channel, include_credentials=True)


@router.put("/{channel_id}", response_model=ChannelDetailResponse)
async def update_channel(
    channel_id: UUID,
    body: ChannelUpdate,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> ChannelDetailResponse:
    if body.name is None and body.is_active is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No fields to update")

    channel = await _get_accessible_channel(db, channel_id, user.id)
    if body.name is not None:
        channel.name = body.name.strip()
    if body.is_active is not None:
        channel.is_active = body.is_active
    await db.flush()
    return _channel_response(channel, include_credentials=True)


@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(
    channel_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> None:
    channel = await _get_accessible_channel(db, channel_id, user.id)
    await db.delete(channel)
