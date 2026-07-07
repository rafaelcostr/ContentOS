"""Performance Learning API — V5.4.2."""

from __future__ import annotations

from uuid import UUID

from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user, require_editor
from contentos_gateway.services.org_service import get_accessible_project
from contentos_intelligence.application.performance_learning import (
    list_performance_insights,
    performance_learning_enabled,
    process_project_performance_learning,
)
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/performance-learning", tags=["Performance Learning"])


class ProcessPerformanceRequest(BaseModel):
    project_id: UUID
    persist: bool = True
    index_kb: bool | None = None


class PerformanceMediaInsightResponse(BaseModel):
    platform: str
    external_media_id: str | None = None
    title: str | None = None
    topic: str
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    ctr: float | None = None
    engagement_rate: float | None = None
    retention_pct: float | None = None
    predicted_retention_pct: float | None = None
    retention_delta: float | None = None
    performance_tier: str = "medium"
    pipeline_id: str | None = None
    hook_text: str | None = None
    learnings: list[str] = Field(default_factory=list)


class PerformanceLearningReportResponse(BaseModel):
    project_id: str
    media_insights: list[PerformanceMediaInsightResponse]
    top_performers: list[PerformanceMediaInsightResponse]
    kb_indexed_count: int
    memory_applied: bool
    memory_updates: list[str]
    summary: str


class PerformanceInsightRowResponse(BaseModel):
    id: str
    project_id: str
    platform: str
    external_media_id: str | None
    pipeline_id: str | None
    title: str | None
    topic: str
    ctr: float | None
    engagement_rate: float | None
    retention_pct: float | None
    retention_delta: float | None
    views: int
    likes: int
    comments: int
    performance_tier: str
    learnings: list[str]
    kb_indexed: bool
    created_at: str | None


@router.post("/process", response_model=PerformanceLearningReportResponse)
async def process_performance_learning(
    body: ProcessPerformanceRequest,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_editor()),
) -> PerformanceLearningReportResponse:
    if not performance_learning_enabled():
        raise HTTPException(status_code=503, detail="Performance Learning disabled")
    await get_accessible_project(db, body.project_id, user.id)
    report = await process_project_performance_learning(
        db,
        body.project_id,
        persist=body.persist,
        index_kb=body.index_kb,
    )
    await db.commit()
    return _to_response(report)


@router.get("/insights", response_model=list[PerformanceInsightRowResponse])
async def get_performance_insights(
    project_id: UUID = Query(...),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> list[PerformanceInsightRowResponse]:
    await get_accessible_project(db, project_id, user.id)
    rows = await list_performance_insights(db, project_id, limit=limit)
    return [PerformanceInsightRowResponse(**row) for row in rows]


def _to_response(report) -> PerformanceLearningReportResponse:
    d = report.to_dict()
    return PerformanceLearningReportResponse(
        project_id=d["project_id"],
        media_insights=[PerformanceMediaInsightResponse(**m) for m in d["media_insights"]],
        top_performers=[PerformanceMediaInsightResponse(**m) for m in d["top_performers"]],
        kb_indexed_count=d["kb_indexed_count"],
        memory_applied=d["memory_applied"],
        memory_updates=d["memory_updates"],
        summary=d["summary"],
    )
