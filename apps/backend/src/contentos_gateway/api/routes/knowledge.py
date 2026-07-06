"""Knowledge Base API routes — Epic 3 V4."""

from __future__ import annotations

from uuid import UUID

from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user, require_editor
from contentos_gateway.services.org_service import get_accessible_project
from contentos_intelligence.application.knowledge_base import KnowledgeBaseService
from contentos_intelligence.application.knowledge_indexer import KnowledgeIndexer
from contentos_intelligence.domain.knowledge import KnowledgeQueryRequest
from contentos_intelligence.domain.knowledge_entry import VALID_RESOURCE_TYPES
from contentos_intelligence.infrastructure.embedding_client import get_gateway_embedding_client
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])


class KnowledgeSearchRequest(BaseModel):
    project_id: UUID
    query: str = Field(min_length=1, max_length=2000)
    resource_types: list[str] = Field(default_factory=list)
    limit: int = Field(default=10, ge=1, le=50)
    min_similarity: float = Field(default=0.0, ge=0.0, le=1.0)


class KnowledgeHitResponse(BaseModel):
    resource_type: str
    resource_id: str | None
    title: str
    snippet: str
    similarity: float
    metadata: dict = Field(default_factory=dict)


class KnowledgeEntryResponse(BaseModel):
    id: str | None
    project_id: str
    pipeline_id: str | None
    resource_type: str
    resource_id: str | None
    title: str
    snippet: str
    version: int
    created_at: str | None
    has_embedding: bool


class IndexPipelineResponse(BaseModel):
    pipeline_id: str
    indexed_count: int
    entries: list[KnowledgeEntryResponse]


def _kb(db: AsyncSession) -> KnowledgeBaseService:
    return KnowledgeBaseService(db, get_gateway_embedding_client())


@router.post("/search", response_model=list[KnowledgeHitResponse])
async def search_knowledge(
    body: KnowledgeSearchRequest,
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> list[KnowledgeHitResponse]:
    await get_accessible_project(db, body.project_id, user.id)
    for rt in body.resource_types:
        if rt not in VALID_RESOURCE_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid resource_type: {rt}")
    hits = await _kb(db).search(
        KnowledgeQueryRequest(
            project_id=body.project_id,
            query=body.query,
            resource_types=body.resource_types,
            limit=body.limit,
            min_similarity=body.min_similarity,
        )
    )
    return [KnowledgeHitResponse(**h.to_dict()) for h in hits]


@router.get("/history/{project_id}", response_model=list[KnowledgeEntryResponse])
async def knowledge_history(
    project_id: UUID,
    resource_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> list[KnowledgeEntryResponse]:
    await get_accessible_project(db, project_id, user.id)
    if resource_type and resource_type not in VALID_RESOURCE_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid resource_type: {resource_type}")
    entries = await _kb(db).history(project_id, resource_type=resource_type, limit=limit)
    return [
        KnowledgeEntryResponse(
            id=str(e.id) if e.id else None,
            project_id=str(e.project_id),
            pipeline_id=str(e.pipeline_id) if e.pipeline_id else None,
            resource_type=e.resource_type,
            resource_id=str(e.resource_id) if e.resource_id else None,
            title=e.title,
            snippet=e.snippet,
            version=e.version,
            created_at=e.created_at.isoformat() if e.created_at else None,
            has_embedding=bool(e.embedding),
        )
        for e in entries
    ]


@router.get("/versions/{resource_type}/{resource_id}", response_model=list[KnowledgeEntryResponse])
async def knowledge_versions(
    resource_type: str,
    resource_id: UUID,
    project_id: UUID = Query(...),
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> list[KnowledgeEntryResponse]:
    await get_accessible_project(db, project_id, user.id)
    if resource_type not in VALID_RESOURCE_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid resource_type: {resource_type}")
    entries = await _kb(db).versions(resource_type, resource_id)
    return [
        KnowledgeEntryResponse(
            id=str(e.id) if e.id else None,
            project_id=str(e.project_id),
            pipeline_id=str(e.pipeline_id) if e.pipeline_id else None,
            resource_type=e.resource_type,
            resource_id=str(e.resource_id) if e.resource_id else None,
            title=e.title,
            snippet=e.snippet,
            version=e.version,
            created_at=e.created_at.isoformat() if e.created_at else None,
            has_embedding=bool(e.embedding),
        )
        for e in entries
    ]


@router.post("/index/{pipeline_id}", response_model=IndexPipelineResponse)
async def index_pipeline(
    pipeline_id: UUID,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_editor()),
) -> IndexPipelineResponse:
    from contentos_database.models import Pipeline

    pipeline = await db.get(Pipeline, pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    await get_accessible_project(db, pipeline.project_id, user.id)

    kb = _kb(db)
    indexer = KnowledgeIndexer(kb)
    indexed = await indexer.index_pipeline(db, pipeline_id)

    try:
        from contentos_intelligence.application.content_graph import ContentGraphService, is_content_graph_enabled

        if is_content_graph_enabled():
            await ContentGraphService().build_pipeline(db, pipeline_id)
    except Exception:
        pass

    return IndexPipelineResponse(
        pipeline_id=str(pipeline_id),
        indexed_count=len(indexed),
        entries=[
            KnowledgeEntryResponse(
                id=str(e.id) if e.id else None,
                project_id=str(e.project_id),
                pipeline_id=str(e.pipeline_id) if e.pipeline_id else None,
                resource_type=e.resource_type,
                resource_id=str(e.resource_id) if e.resource_id else None,
                title=e.title,
                snippet=e.snippet,
                version=e.version,
                created_at=e.created_at.isoformat() if e.created_at else None,
                has_embedding=bool(e.embedding),
            )
            for e in indexed
        ],
    )
