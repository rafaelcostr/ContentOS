"""Viral Intelligence API — Epic 1 V4."""

from __future__ import annotations

from uuid import UUID

from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user
from contentos_gateway.services.org_service import get_accessible_project
from contentos_intelligence.application.bootstrap import get_content_intelligence_service
from contentos_intelligence.domain.context import IntelligenceContext
from contentos_intelligence.domain.viral_report import ViralReport
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/viral", tags=["Viral Intelligence"])


class ViralAnalyzeRequest(BaseModel):
    project_id: UUID
    topic: str = Field(min_length=1, max_length=2000)
    pipeline_id: UUID | None = None
    payload: dict = Field(default_factory=dict)
    include_reuse: bool = True


class ViralReportResponse(BaseModel):
    viral_score: float
    retention_prediction: float
    recommendations: list[str]
    hook_score: float | None = None
    rhythm_score: float | None = None
    emotion_score: float | None = None
    scene_score: float | None = None
    cta_score: float | None = None
    details: dict = Field(default_factory=dict)
    reuse_suggestions: list[dict] = Field(default_factory=list)


@router.post("/analyze", response_model=ViralReportResponse)
async def analyze_viral(
    body: ViralAnalyzeRequest,
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> ViralReportResponse:
    await get_accessible_project(db, body.project_id, user.id)
    context = IntelligenceContext(
        project_id=body.project_id,
        pipeline_id=body.pipeline_id,
        topic=body.topic,
        payload=body.payload,
    )
    service = get_content_intelligence_service()
    result = await service.run(context)
    viral = ViralReport.from_dict(result.get("viral_report") or {})
    reuse = result.get("reuse_suggestions") or [] if body.include_reuse else []
    return ViralReportResponse(
        **viral.to_dict(),
        reuse_suggestions=reuse,
    )
