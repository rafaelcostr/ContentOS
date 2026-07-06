"""Content Relation Graph API — Epic 11 V4."""

from __future__ import annotations

from uuid import UUID

from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user
from contentos_gateway.services.org_service import get_accessible_project
from contentos_intelligence.application.content_graph import ContentGraphService
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/graph", tags=["Content Graph"])


class GraphNodeResponse(BaseModel):
    id: str
    type: str
    node_id: str
    label: str
    pipeline_id: str | None = None
    metadata: dict = Field(default_factory=dict)


class GraphEdgeResponse(BaseModel):
    source: str
    target: str
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    relation: str
    pipeline_id: str | None = None
    metadata: dict = Field(default_factory=dict)


class GraphViewResponse(BaseModel):
    project_id: str
    node_count: int
    edge_count: int
    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]


class BuildGraphResponse(BaseModel):
    pipeline_id: str
    project_id: str
    edge_count: int
    node_count: int


class NeighborsResponse(BaseModel):
    node: GraphNodeResponse
    outgoing: list[GraphEdgeResponse]
    incoming: list[GraphEdgeResponse]


@router.post("/build/{pipeline_id}", response_model=BuildGraphResponse)
async def build_graph_for_pipeline(
    pipeline_id: UUID,
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> BuildGraphResponse:
    from contentos_database.models import Pipeline
    from sqlalchemy import select

    pipeline = (await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))).scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    await get_accessible_project(db, pipeline.project_id, user.id)

    view = await ContentGraphService().build_pipeline(db, pipeline_id)
    return BuildGraphResponse(
        pipeline_id=str(pipeline_id),
        project_id=view.project_id,
        edge_count=len(view.edges),
        node_count=len(view.nodes),
    )


@router.get("/project/{project_id}", response_model=GraphViewResponse)
async def get_project_graph(
    project_id: UUID,
    limit: int = Query(default=500, ge=1, le=2000),
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> GraphViewResponse:
    await get_accessible_project(db, project_id, user.id)
    view = await ContentGraphService().get_project_graph(db, project_id, limit=limit)
    return _view_response(view)


@router.get("/neighbors", response_model=NeighborsResponse)
async def get_neighbors(
    project_id: UUID = Query(...),
    node_type: str = Query(..., min_length=1, max_length=50),
    node_id: str = Query(..., min_length=1, max_length=120),
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> NeighborsResponse:
    await get_accessible_project(db, project_id, user.id)
    result = await ContentGraphService().get_neighbors(db, project_id, node_type, node_id)
    return NeighborsResponse(
        node=GraphNodeResponse(**result.node.to_dict()),
        outgoing=[GraphEdgeResponse(**e.to_dict()) for e in result.outgoing],
        incoming=[GraphEdgeResponse(**e.to_dict()) for e in result.incoming],
    )


def _view_response(view) -> GraphViewResponse:
    d = view.to_dict()
    return GraphViewResponse(
        project_id=d["project_id"],
        node_count=d["node_count"],
        edge_count=d["edge_count"],
        nodes=[GraphNodeResponse(**n) for n in d["nodes"]],
        edges=[GraphEdgeResponse(**{**e, "relation": e["relation"]}) for e in d["edges"]],
    )
