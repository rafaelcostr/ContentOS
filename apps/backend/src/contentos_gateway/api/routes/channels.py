"""Channel credentials for platform publishing."""

from uuid import UUID

from contentos_database.models import Channel, Project, User
from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user, require_editor
from contentos_gateway.services.org_service import get_accessible_project, project_access_clause
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/channels", tags=["Channels"])


class ChannelCreate(BaseModel):
    project_id: UUID
    platform: str
    name: str
    credentials: dict | None = None


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
    return [
        ChannelResponse(
            id=c.id,
            project_id=c.project_id,
            platform=c.platform,
            name=c.name,
            is_active=c.is_active,
            has_credentials=bool(c.credentials),
        )
        for c in result.scalars().all()
    ]


@router.post("", response_model=ChannelDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_channel(
    body: ChannelCreate,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> ChannelDetailResponse:
    await get_accessible_project(db, body.project_id, user.id)

    channel = Channel(
        project_id=body.project_id,
        platform=body.platform.lower(),
        name=body.name,
        credentials=body.credentials,
        is_active=True,
    )
    db.add(channel)
    await db.flush()
    return ChannelDetailResponse(
        id=channel.id,
        project_id=channel.project_id,
        platform=channel.platform,
        name=channel.name,
        is_active=channel.is_active,
        has_credentials=bool(channel.credentials),
        credentials=channel.credentials,
    )


@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(
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
    await db.delete(channel)
