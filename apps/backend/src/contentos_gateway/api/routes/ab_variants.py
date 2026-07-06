"""A/B Testing API — Epic 6 V4."""

from __future__ import annotations

from uuid import UUID

from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user
from contentos_gateway.services.org_service import get_accessible_project
from contentos_intelligence.application.ab_testing import AbTestingService
from contentos_intelligence.application.bootstrap import get_content_intelligence_service
from contentos_intelligence.domain.context import IntelligenceContext
from contentos_intelligence.infrastructure.ab_repository import AbVariantRepository
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/ab-variants", tags=["A/B Testing"])


class AbGenerateRequest(BaseModel):
    project_id: UUID
    topic: str = Field(min_length=1, max_length=2000)
    pipeline_id: UUID | None = None
    payload: dict = Field(default_factory=dict)
    persist: bool = True


class AbVariantSetResponse(BaseModel):
    id: str
    project_id: str
    pipeline_id: str
    dimension: str
    variants: list[dict]
    winner_index: int
    winner: dict | None = None
    created_at: str | None = None


class AbTestReportResponse(BaseModel):
    project_id: str
    pipeline_id: str | None
    dimensions: list[dict]
    winners: dict


@router.post("/generate", response_model=AbTestReportResponse)
async def generate_ab_variants(
    body: AbGenerateRequest,
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> AbTestReportResponse:
    await get_accessible_project(db, body.project_id, user.id)
    context = IntelligenceContext(
        project_id=body.project_id,
        pipeline_id=body.pipeline_id,
        topic=body.topic,
        payload=body.payload,
    )
    ci = get_content_intelligence_service()
    ci_result = await ci.run(context)
    viral_report = ci_result.get("viral_report") or {}
    ab_service = AbTestingService(db=db)
    if body.persist and body.pipeline_id:
        report = await ab_service.run_and_persist(context, viral_report)
    else:
        report = ab_service.run(context, viral_report)
    return AbTestReportResponse(**report.to_dict())


@router.get("/pipeline/{pipeline_id}", response_model=list[AbVariantSetResponse])
async def list_ab_variants_for_pipeline(
    pipeline_id: UUID,
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> list[AbVariantSetResponse]:
    from contentos_database.models import Pipeline
    from sqlalchemy import select

    pipeline = (await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))).scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    await get_accessible_project(db, pipeline.project_id, user.id)
    repo = AbVariantRepository()
    rows = await repo.list_by_pipeline(db, pipeline_id)
    return [AbVariantSetResponse(**r) for r in rows]
