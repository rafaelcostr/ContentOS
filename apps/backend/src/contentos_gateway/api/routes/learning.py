"""Learning Engine API — Epic 7 V4."""

from __future__ import annotations

from uuid import UUID

from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user
from contentos_gateway.services.org_service import get_accessible_project
from contentos_intelligence.application.learning import LearningEngine
from contentos_intelligence.domain.context import IntelligenceContext
from contentos_intelligence.infrastructure.learning_repository import LearningRepository
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/learning", tags=["Learning Engine"])


class LearningRecordRequest(BaseModel):
    project_id: UUID
    pipeline_id: UUID
    topic: str = Field(default="", max_length=2000)
    payload: dict = Field(default_factory=dict)
    persist: bool = True


class LearningSignalResponse(BaseModel):
    signal_type: str
    value: str
    score: float | None = None
    source: str
    metadata: dict = Field(default_factory=dict)


class LearningReportResponse(BaseModel):
    project_id: str
    pipeline_id: str | None
    topic: str
    content_score: float | None = None
    viral_score: float | None = None
    specialist_id: str | None = None
    hook_text: str = ""
    cta_text: str = ""
    signal_count: int
    signals: list[LearningSignalResponse]
    memory_applied: bool
    memory_updates: list[str]
    kb_indexed_count: int


@router.post("/record", response_model=LearningReportResponse)
async def record_learning(
    body: LearningRecordRequest,
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> LearningReportResponse:
    await get_accessible_project(db, body.project_id, user.id)
    from contentos_database.models import Pipeline
    from sqlalchemy import select

    pipeline = (await db.execute(select(Pipeline).where(Pipeline.id == body.pipeline_id))).scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    if pipeline.project_id != body.project_id:
        raise HTTPException(status_code=400, detail="Pipeline does not belong to project")

    context = IntelligenceContext(
        project_id=body.project_id,
        pipeline_id=body.pipeline_id,
        topic=body.topic or pipeline.topic,
        payload=body.payload,
    )
    report = LearningEngine().process(context)
    if body.persist:
        await LearningRepository().save_report(db, report)
    return _to_response(report)


@router.get("/pipeline/{pipeline_id}", response_model=LearningReportResponse)
async def get_learning_for_pipeline(
    pipeline_id: UUID,
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> LearningReportResponse:
    from contentos_database.models import Pipeline
    from sqlalchemy import select

    pipeline = (await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))).scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    await get_accessible_project(db, pipeline.project_id, user.id)
    row = await LearningRepository().get_by_pipeline(db, pipeline_id)
    if not row:
        raise HTTPException(status_code=404, detail="Learning insight not found")
    return _row_to_response(row)


@router.get("/insights", response_model=list[LearningReportResponse])
async def list_learning_insights(
    project_id: UUID = Query(...),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> list[LearningReportResponse]:
    await get_accessible_project(db, project_id, user.id)
    rows = await LearningRepository().list_by_project(db, project_id, limit=limit)
    return [_row_to_response(r) for r in rows]


def _to_response(report) -> LearningReportResponse:
    d = report.to_dict()
    return _dict_to_response(d)


def _row_to_response(row: dict) -> LearningReportResponse:
    return _dict_to_response(
        {
            **row,
            "signal_count": len(row.get("signals") or []),
        }
    )


def _dict_to_response(d: dict) -> LearningReportResponse:
    return LearningReportResponse(
        project_id=str(d["project_id"]),
        pipeline_id=str(d["pipeline_id"]) if d.get("pipeline_id") else None,
        topic=str(d.get("topic") or ""),
        content_score=d.get("content_score"),
        viral_score=d.get("viral_score"),
        specialist_id=d.get("specialist_id"),
        hook_text=str(d.get("hook_text") or ""),
        cta_text=str(d.get("cta_text") or ""),
        signal_count=int(d.get("signal_count") or len(d.get("signals") or [])),
        signals=[
            LearningSignalResponse(
                signal_type=str(s.get("signal_type", "")),
                value=str(s.get("value", "")),
                score=s.get("score"),
                source=str(s.get("source", "pipeline")),
                metadata=dict(s.get("metadata") or {}),
            )
            for s in d.get("signals") or []
        ],
        memory_applied=bool(d.get("memory_applied")),
        memory_updates=list(d.get("memory_updates") or []),
        kb_indexed_count=int(d.get("kb_indexed_count") or 0),
    )
