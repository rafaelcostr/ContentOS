from uuid import UUID

from contentos_database.models import User, Video
from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user
from contentos_gateway.schemas import VideoResponse
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/videos", tags=["Videos"])


@router.get("", response_model=list[VideoResponse])
async def list_videos(
    project_id: UUID | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> list[VideoResponse]:
    query = select(Video).order_by(Video.created_at.desc()).limit(limit)
    if project_id:
        query = query.where(Video.project_id == project_id)
    result = await db.execute(query)
    return [VideoResponse.model_validate(v) for v in result.scalars().all()]
