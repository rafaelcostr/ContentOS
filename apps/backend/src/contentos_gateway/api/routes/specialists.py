"""Specialists API — Epic 5 V4."""

from __future__ import annotations

from uuid import UUID

from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user
from contentos_gateway.services.org_service import get_accessible_project
from contentos_intelligence.application.registry import get_intelligence_registry
from contentos_intelligence.application.specialists import get_specialist, list_specialists
from contentos_intelligence.application.specialists.selector import NicheSpecialistSelector
from contentos_intelligence.domain.context import IntelligenceContext
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/specialists", tags=["Specialists"])


class SpecialistSummary(BaseModel):
    specialist_id: str
    name: str
    niche: str
    tone: str = ""
    prompt_pack: str = ""
    pilot: bool = False
    enabled: bool = True
    coming_soon: bool = False


class SpecialistSelectRequest(BaseModel):
    project_id: UUID
    topic: str = Field(min_length=1, max_length=2000)
    pipeline_id: UUID | None = None
    payload: dict = Field(default_factory=dict)


class SpecialistSelectResponse(BaseModel):
    specialist: SpecialistSummary
    confidence: float
    reason: str
    specialist_context: str


@router.get("", response_model=list[SpecialistSummary])
async def list_all_specialists(
    include_upcoming: bool = Query(False),
    user=Depends(get_current_user),
) -> list[SpecialistSummary]:
    profiles = list_specialists(include_upcoming=include_upcoming)
    return [
        SpecialistSummary(
            specialist_id=p.specialist_id,
            name=p.name,
            niche=p.niche,
            tone=p.tone,
            prompt_pack=p.prompt_pack,
            pilot=bool(p.metadata.get("pilot")),
            enabled=bool(p.metadata.get("enabled", True)),
            coming_soon=bool(p.metadata.get("coming_soon")),
        )
        for p in profiles
    ]


@router.get("/{specialist_id}", response_model=SpecialistSummary)
async def get_specialist_detail(
    specialist_id: str,
    user=Depends(get_current_user),
) -> SpecialistSummary:
    profile = get_specialist(specialist_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Specialist not found")
    return SpecialistSummary(
        specialist_id=profile.specialist_id,
        name=profile.name,
        niche=profile.niche,
        tone=profile.tone,
        prompt_pack=profile.prompt_pack,
        pilot=bool(profile.metadata.get("pilot")),
        enabled=bool(profile.metadata.get("enabled", True)),
        coming_soon=bool(profile.metadata.get("coming_soon")),
    )


@router.post("/select", response_model=SpecialistSelectResponse)
async def select_specialist(
    body: SpecialistSelectRequest,
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> SpecialistSelectResponse:
    await get_accessible_project(db, body.project_id, user.id)
    context = IntelligenceContext(
        project_id=body.project_id,
        pipeline_id=body.pipeline_id,
        topic=body.topic,
        payload=body.payload,
    )
    registry = get_intelligence_registry()
    selector = registry.specialist_selector
    if type(selector).__name__ == "NoOpSpecialistSelector":
        selector = NicheSpecialistSelector()
    selection = await selector.select(context)
    from contentos_intelligence.application.specialists.context import format_specialist_context

    return SpecialistSelectResponse(
        specialist=SpecialistSummary(
            specialist_id=selection.specialist.specialist_id,
            name=selection.specialist.name,
            niche=selection.specialist.niche,
            tone=selection.specialist.tone,
            prompt_pack=selection.specialist.prompt_pack,
            pilot=bool(selection.specialist.metadata.get("pilot")),
            enabled=True,
        ),
        confidence=selection.confidence,
        reason=selection.reason,
        specialist_context=format_specialist_context(selection.specialist),
    )
