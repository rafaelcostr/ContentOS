"""Creative Memory API — V5.2.5."""

from __future__ import annotations

from uuid import UUID

from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user
from contentos_gateway.services.org_service import get_accessible_project
from contentos_intelligence.application.creative_memory import merge_creative_memory
from contentos_intelligence.domain.context import IntelligenceContext
from contentos_intelligence.domain.creative_memory import CreativeMemoryReport
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/creative-memory", tags=["Creative Memory"])


class CreativeMemoryMergeRequest(BaseModel):
    project_id: UUID
    topic: str = Field(default="", max_length=2000)
    pipeline_id: UUID | None = None
    payload: dict = Field(default_factory=dict)


class CreativeMemoryHitResponse(BaseModel):
    resource_type: str
    title: str
    snippet: str
    similarity: float
    source: str


class CreativeMemoryMergeResponse(BaseModel):
    project_id: str
    pipeline_id: str | None
    topic: str
    memory_applied: bool
    memory_updates: list[str]
    kb_indexed_count: int
    knowledge_indexed_count: int
    creative_memory_context: str
    hints: dict
    knowledge_hits: list[CreativeMemoryHitResponse]
    learning_report: dict


@router.post("/merge", response_model=CreativeMemoryMergeResponse)
async def merge_memory(
    body: CreativeMemoryMergeRequest,
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> CreativeMemoryMergeResponse:
    await get_accessible_project(db, body.project_id, user.id)
    payload = dict(body.payload)
    if body.topic and not payload.get("topic"):
        payload["topic"] = body.topic
    context = IntelligenceContext(
        project_id=body.project_id,
        pipeline_id=body.pipeline_id,
        topic=body.topic,
        payload=payload,
    )
    try:
        from contentos_intelligence.application.creative_memory import merge_creative_memory_async

        report = await merge_creative_memory_async(context, db)
        await db.commit()
    except Exception:
        report = merge_creative_memory(context)
    return _to_response(report)


def _to_response(report: CreativeMemoryReport) -> CreativeMemoryMergeResponse:
    return CreativeMemoryMergeResponse(
        project_id=report.project_id,
        pipeline_id=report.pipeline_id,
        topic=report.topic,
        memory_applied=report.memory_applied,
        memory_updates=report.memory_updates,
        kb_indexed_count=report.kb_indexed_count,
        knowledge_indexed_count=report.knowledge_indexed_count,
        creative_memory_context=report.creative_memory_context,
        hints=report.hints,
        knowledge_hits=[
            CreativeMemoryHitResponse(
                resource_type=h.resource_type,
                title=h.title,
                snippet=h.snippet,
                similarity=h.similarity,
                source=h.source,
            )
            for h in report.knowledge_hits
        ],
        learning_report=report.learning_report,
    )
