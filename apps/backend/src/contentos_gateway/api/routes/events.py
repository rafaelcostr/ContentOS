"""Event Bus API routes."""

from uuid import UUID

from contentos_database.models import User
from contentos_database.session import get_session
from contentos_events import get_event_bus
from contentos_events.application.subscriber import EventSubscriber
from contentos_events.infrastructure.event_store import EventStore
from contentos_gateway.api.deps import get_current_user
from contentos_gateway.services.org_service import get_accessible_pipeline
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/events", tags=["Events"])


class DomainEventItem(BaseModel):
    id: str | None = None
    type: str
    pipeline_id: str | None = None
    project_id: str | None = None
    job_id: str | None = None
    agent: str | None = None
    step: str | None = None
    status: str | None = None
    data: dict = {}
    timestamp: str | None = None
    stream_id: str | None = None


@router.get("/recent", response_model=list[DomainEventItem])
async def recent_events(
    limit: int = 50,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> list[DomainEventItem]:
    store = EventStore()
    rows = await store.list_recent(db, min(limit, 200))
    if rows:
        return [DomainEventItem(**r) for r in rows]
    # fallback to redis stream if DB empty
    stream_events = await EventSubscriber().read_recent(min(limit, 200))
    return [DomainEventItem(**e) for e in stream_events]


@router.get("/pipelines/{pipeline_id}", response_model=list[DomainEventItem])
async def pipeline_events(
    pipeline_id: UUID,
    limit: int = 100,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[DomainEventItem]:
    await get_accessible_pipeline(db, pipeline_id, user.id)
    rows = await EventStore().list_by_pipeline(db, pipeline_id, min(limit, 500))
    return [DomainEventItem(**r) for r in rows]


@router.get("/stream/info")
async def stream_info(_user: User = Depends(get_current_user)) -> dict:
    return await get_event_bus().stream_info()
