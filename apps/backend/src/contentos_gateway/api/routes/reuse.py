"""Smart Reuse API routes — Epic 4 V4."""

from __future__ import annotations

from uuid import UUID

from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user
from contentos_gateway.services.org_service import get_accessible_project
from contentos_intelligence.application.registry import get_intelligence_registry
from contentos_intelligence.domain.context import IntelligenceContext
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/reuse", tags=["Smart Reuse"])


class ReuseSuggestRequest(BaseModel):
    project_id: UUID
    topic: str = Field(min_length=1, max_length=2000)
    pipeline_id: UUID | None = None
    payload: dict = Field(default_factory=dict)


class ReuseSuggestionResponse(BaseModel):
    resource_type: str
    resource_id: str | None
    title: str
    similarity: float
    reason: str
    metadata: dict = Field(default_factory=dict)


@router.post("/suggest", response_model=list[ReuseSuggestionResponse])
async def suggest_reuse(
    body: ReuseSuggestRequest,
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> list[ReuseSuggestionResponse]:
    await get_accessible_project(db, body.project_id, user.id)
    context = IntelligenceContext(
        project_id=body.project_id,
        pipeline_id=body.pipeline_id,
        topic=body.topic,
        payload=body.payload,
    )
    registry = get_intelligence_registry()
    suggestions = await registry.reuse_advisor.suggest(context)
    return [ReuseSuggestionResponse(**s.to_dict()) for s in suggestions]
