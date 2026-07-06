"""Content Sources API."""

from uuid import UUID

from contentos_database.models import User
from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user, require_editor
from contentos_gateway.services.org_service import get_accessible_pipeline, project_access_clause
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from contentos_sources import get_collection_store, get_source_manager
    from contentos_sources.domain.source_query import SourceQuery
except ImportError:

    def get_source_manager():  # type: ignore[misc]
        raise HTTPException(status_code=503, detail="Content sources not available")

    def get_collection_store():  # type: ignore[misc]
        return None

router = APIRouter(prefix="/content-sources", tags=["Content Sources"])


class SearchRequest(BaseModel):
    scene_description: str
    visual_hint: str = ""
    duration_needed: float = 5.0
    tags: list[str] = []
    project_id: UUID | None = None


@router.get("")
async def list_sources(_user: User = Depends(get_current_user)) -> dict:
    mgr = get_source_manager()
    return {"sources": mgr.list_sources()}


@router.get("/health")
async def sources_health(_user: User = Depends(get_current_user)) -> dict:
    mgr = get_source_manager()
    return {"sources": await mgr.health_all()}


@router.post("/search")
async def search_sources(body: SearchRequest, _user: User = Depends(require_editor())) -> dict:
    mgr = get_source_manager()
    query = SourceQuery(
        scene_description=body.scene_description,
        visual_hint=body.visual_hint,
        duration_needed=body.duration_needed,
        tags=body.tags,
        project_id=body.project_id,
    )
    results = await mgr.search(query)
    return {"candidates": [c.to_dict() for c in results]}


@router.get("/collections")
async def list_collections(
    limit: int = 30,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[dict]:
    from contentos_database.models import Pipeline, PipelineAssetCollection, Project

    result = await db.execute(
        select(PipelineAssetCollection)
        .join(Pipeline, PipelineAssetCollection.pipeline_id == Pipeline.id)
        .join(Project, Pipeline.project_id == Project.id)
        .where(project_access_clause(user.id))
        .order_by(PipelineAssetCollection.updated_at.desc())
        .limit(min(limit, 100))
    )
    rows = result.scalars().all()
    return [
        {
            "pipeline_id": str(r.pipeline_id),
            "project_id": str(r.project_id),
            "status": r.status,
            "candidate_scenes": len(r.candidates or []),
            "collected_assets": len(r.assets or []),
            "updated_at": r.updated_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/collections/{pipeline_id}")
async def get_pipeline_collection(
    pipeline_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    await get_accessible_pipeline(db, pipeline_id, user.id)

    store = get_collection_store()
    if not store:
        raise HTTPException(status_code=503, detail="Collection store unavailable")
    data = store.get_sync(pipeline_id)
    if not data:
        raise HTTPException(status_code=404, detail="No collection for pipeline")
    return data
