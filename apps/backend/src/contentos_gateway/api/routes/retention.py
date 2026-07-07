"""Retention Engine API — V5.2.1."""

from __future__ import annotations

from uuid import UUID

from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user
from contentos_gateway.services.org_service import get_accessible_project
from contentos_intelligence.application.retention import RetentionAnalyzer
from contentos_intelligence.domain.retention_report import RetentionReport
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/retention", tags=["Retention Engine"])


class RetentionAnalyzeRequest(BaseModel):
    project_id: UUID
    topic: str = Field(default="", max_length=2000)
    pipeline_id: UUID | None = None
    payload: dict = Field(default_factory=dict)


class RetentionTimelinePoint(BaseModel):
    second: int
    retention_pct: float
    scene_label: str = ""


class RetentionWeakSegment(BaseModel):
    label: str
    start_second: float
    end_second: float
    avg_retention_pct: float
    min_retention_pct: float
    reason: str = ""


class RetentionAnalyzeResponse(BaseModel):
    overall_score: float
    avg_retention_pct: float
    hook_retention_pct: float
    completion_pct: float
    duration_seconds: float
    drop_seconds: list[int]
    weak_segments: list[RetentionWeakSegment]
    timeline: list[RetentionTimelinePoint]
    recommendations: list[str]


@router.post("/analyze", response_model=RetentionAnalyzeResponse)
async def analyze_retention(
    body: RetentionAnalyzeRequest,
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> RetentionAnalyzeResponse:
    await get_accessible_project(db, body.project_id, user.id)
    payload = dict(body.payload)
    if body.topic and not payload.get("topic"):
        payload["topic"] = body.topic
    report = RetentionAnalyzer().analyze(payload)
    return _to_response(report)


def _to_response(report: RetentionReport) -> RetentionAnalyzeResponse:
    return RetentionAnalyzeResponse(
        overall_score=report.overall_score,
        avg_retention_pct=report.avg_retention_pct,
        hook_retention_pct=report.hook_retention_pct,
        completion_pct=report.completion_pct,
        duration_seconds=report.duration_seconds,
        drop_seconds=report.drop_seconds,
        weak_segments=[
            RetentionWeakSegment(
                label=s.label,
                start_second=s.start_second,
                end_second=s.end_second,
                avg_retention_pct=s.avg_retention_pct,
                min_retention_pct=s.min_retention_pct,
                reason=s.reason,
            )
            for s in report.weak_segments
        ],
        timeline=[
            RetentionTimelinePoint(
                second=t.second,
                retention_pct=t.retention_pct,
                scene_label=t.scene_label,
            )
            for t in report.timeline
        ],
        recommendations=report.recommendations,
    )
