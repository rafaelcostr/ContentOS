"""Comment Analyzer API — V5.4.3."""

from __future__ import annotations

from uuid import UUID

from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user, require_editor
from contentos_gateway.services.org_service import get_accessible_project
from contentos_intelligence.application.comment_analyzer import (
    analyze_project_comments,
    comment_analyzer_enabled,
    list_comment_insights,
)
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/comment-analyzer", tags=["Comment Analyzer"])


class AnalyzeCommentsRequest(BaseModel):
    project_id: UUID
    persist: bool = True
    index_kb: bool | None = None


class CommentMediaAnalysisResponse(BaseModel):
    platform: str
    external_media_id: str | None = None
    title: str | None = None
    comment_count: int = 0
    positive_pct: float = 0.0
    negative_pct: float = 0.0
    neutral_pct: float = 0.0
    question_count: int = 0
    themes: list[str] = Field(default_factory=list)
    sample_comments: list[str] = Field(default_factory=list)
    error: str | None = None


class CommentAnalysisReportResponse(BaseModel):
    project_id: str
    media_analyses: list[CommentMediaAnalysisResponse]
    total_comments: int
    kb_indexed_count: int
    summary: str


class CommentInsightRowResponse(BaseModel):
    id: str
    project_id: str
    platform: str
    external_media_id: str | None
    title: str | None
    comment_count: int
    positive_pct: float
    negative_pct: float
    neutral_pct: float
    question_count: int
    themes: list[str]
    sample_comments: list[str]
    error: str | None
    kb_indexed: bool
    created_at: str | None


@router.post("/analyze", response_model=CommentAnalysisReportResponse)
async def analyze_comments(
    body: AnalyzeCommentsRequest,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_editor()),
) -> CommentAnalysisReportResponse:
    if not comment_analyzer_enabled():
        raise HTTPException(status_code=503, detail="Comment Analyzer disabled")
    await get_accessible_project(db, body.project_id, user.id)
    report = await analyze_project_comments(
        db,
        body.project_id,
        persist=body.persist,
        index_kb=body.index_kb,
    )
    await db.commit()
    d = report.to_dict()
    return CommentAnalysisReportResponse(
        project_id=d["project_id"],
        media_analyses=[CommentMediaAnalysisResponse(**m) for m in d["media_analyses"]],
        total_comments=d["total_comments"],
        kb_indexed_count=d["kb_indexed_count"],
        summary=d["summary"],
    )


@router.get("/insights", response_model=list[CommentInsightRowResponse])
async def get_comment_insights(
    project_id: UUID = Query(...),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> list[CommentInsightRowResponse]:
    await get_accessible_project(db, project_id, user.id)
    rows = await list_comment_insights(db, project_id, limit=limit)
    return [CommentInsightRowResponse(**row) for row in rows]
