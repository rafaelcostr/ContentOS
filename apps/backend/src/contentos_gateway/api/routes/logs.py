from uuid import UUID

from contentos_database.models import LogEntry, User
from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user
from contentos_gateway.schemas import LogResponse
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/logs", tags=["Logs"])


@router.get("", response_model=list[LogResponse])
async def list_logs(
    pipeline_id: UUID | None = None,
    agent: str | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> list[LogResponse]:
    query = select(LogEntry).order_by(LogEntry.created_at.desc()).limit(limit)
    if pipeline_id:
        query = query.where(LogEntry.pipeline_id == pipeline_id)
    if agent:
        query = query.where(LogEntry.agent == agent)
    result = await db.execute(query)
    return [LogResponse.model_validate(log) for log in result.scalars().all()]
