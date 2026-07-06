"""Content Score API — Epic 9 V4."""

from __future__ import annotations

from uuid import UUID

from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user
from contentos_gateway.services.org_service import get_accessible_project
from contentos_intelligence.application.bootstrap import get_content_intelligence_service
from contentos_intelligence.application.content_score.service import ContentScoreService
from contentos_intelligence.application.registry import get_intelligence_registry
from contentos_intelligence.domain.content_score import ContentScoreReport
from contentos_intelligence.domain.context import IntelligenceContext
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/content-score", tags=["Content Score"])


class ContentScoreRequest(BaseModel):
    project_id: UUID
    topic: str = Field(min_length=1, max_length=2000)
    pipeline_id: UUID | None = None
    payload: dict = Field(default_factory=dict)
    full_pipeline: bool = True


class ContentScoreDimensionResponse(BaseModel):
    name: str
    score: float
    weight: float
    source: str


class ContentScoreResponse(BaseModel):
    total_score: float
    grade: str
    mode: str
    summary: str
    dimensions: list[ContentScoreDimensionResponse]


@router.post("/score", response_model=ContentScoreResponse)
async def score_content(
    body: ContentScoreRequest,
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> ContentScoreResponse:
    await get_accessible_project(db, body.project_id, user.id)
    context = IntelligenceContext(
        project_id=body.project_id,
        pipeline_id=body.pipeline_id,
        topic=body.topic,
        payload=body.payload,
    )

    if body.full_pipeline:
        service = get_content_intelligence_service()
        result = await service.run(context)
        report = ContentScoreReport.from_dict(result.get("content_score_report") or {})
    else:
        registry = get_intelligence_registry()
        scorer = registry.content_scorer
        if type(scorer).__name__ == "NoOpContentScorer":
            scorer = ContentScoreService()
        report = await scorer.score(context)

    return ContentScoreResponse(
        total_score=report.total_score,
        grade=report.grade,
        mode=report.mode,
        summary=report.summary,
        dimensions=[
            ContentScoreDimensionResponse(
                name=d.name,
                score=d.score,
                weight=d.weight,
                source=d.source,
            )
            for d in report.dimensions
        ],
    )
