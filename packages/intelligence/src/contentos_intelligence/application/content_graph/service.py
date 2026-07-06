"""ContentGraphService — build and query relation graph (Epic 11)."""

from __future__ import annotations

import os
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from contentos_intelligence.application.content_graph.builder import build_pipeline_graph
from contentos_intelligence.domain.content_graph import GraphNode, GraphView, NeighborsView
from contentos_intelligence.infrastructure.content_graph_repository import ContentGraphRepository


def is_content_graph_enabled() -> bool:
    return os.getenv("CONTENT_GRAPH_ENABLED", "true").lower() in ("1", "true", "yes")


def auto_build_on_learning() -> bool:
    return os.getenv("CONTENT_GRAPH_AUTO_BUILD", "true").lower() in ("1", "true", "yes")


class ContentGraphService:
    def __init__(self, repository: ContentGraphRepository | None = None) -> None:
        self._repo = repository or ContentGraphRepository()

    async def build_pipeline(self, db: AsyncSession, pipeline_id: UUID) -> GraphView:
        view = await build_pipeline_graph(db, pipeline_id)
        if view.project_id:
            await self._repo.replace_pipeline_edges(db, pipeline_id, UUID(view.project_id), view.edges)
        return view

    async def get_project_graph(
        self, db: AsyncSession, project_id: UUID, *, limit: int = 500
    ) -> GraphView:
        return await self._repo.load_project_graph(db, project_id, limit=limit)

    async def get_neighbors(
        self,
        db: AsyncSession,
        project_id: UUID,
        node_type: str,
        node_id: str,
    ) -> NeighborsView:
        node = await self._repo.find_node_label(db, project_id, node_type, node_id)
        if not node:
            node = GraphNode(node_type=node_type, node_id=node_id, label=f"{node_type}:{node_id}")
        outgoing, incoming = await self._repo.neighbors(db, project_id, node_type, node_id)
        return NeighborsView(node=node, outgoing=outgoing, incoming=incoming)

    def build_pipeline_sync(self, pipeline_id: UUID) -> int:
        return self._repo.build_pipeline_sync(pipeline_id)
