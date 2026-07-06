"""Persistence for content relation graph — Epic 11."""

from __future__ import annotations

import os
import uuid
from typing import Any
from uuid import UUID

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from contentos_intelligence.domain.content_graph import GraphEdge, GraphNode, GraphView, node_key


def _sync_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "")
    return database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace(
        "postgresql://", "postgresql+psycopg2://"
    )


class ContentGraphRepository:
    async def replace_pipeline_edges(
        self,
        db: AsyncSession,
        pipeline_id: UUID,
        project_id: UUID,
        edges: list[GraphEdge],
    ) -> int:
        from contentos_database.models import ContentRelationRow

        await db.execute(delete(ContentRelationRow).where(ContentRelationRow.pipeline_id == pipeline_id))
        count = 0
        for edge in edges:
            db.add(
                ContentRelationRow(
                    id=uuid.uuid4(),
                    project_id=project_id,
                    pipeline_id=pipeline_id,
                    source_type=edge.source_type,
                    source_id=edge.source_id,
                    target_type=edge.target_type,
                    target_id=edge.target_id,
                    relation_type=edge.relation_type,
                    label_source=edge.metadata.get("label_source", ""),
                    label_target=edge.metadata.get("label_target", ""),
                    metadata_=edge.metadata or None,
                )
            )
            count += 1
        await db.flush()
        return count

    async def neighbors(
        self,
        db: AsyncSession,
        project_id: UUID,
        node_type: str,
        node_id: str,
    ) -> tuple[list[GraphEdge], list[GraphEdge]]:
        from contentos_database.models import ContentRelationRow

        rows = (
            await db.execute(select(ContentRelationRow).where(ContentRelationRow.project_id == project_id))
        ).scalars().all()
        outgoing: list[GraphEdge] = []
        incoming: list[GraphEdge] = []
        for row in rows:
            edge = _row_to_edge(row)
            if row.source_type == node_type and row.source_id == node_id:
                outgoing.append(edge)
            if row.target_type == node_type and row.target_id == node_id:
                incoming.append(edge)
        return outgoing, incoming

    async def find_node_label(
        self, db: AsyncSession, project_id: UUID, node_type: str, node_id: str
    ) -> GraphNode | None:
        from contentos_database.models import (
            KnowledgeEntry,
            LearningInsightRow,
            Pipeline,
            Script,
            Video,
        )

        if node_type == "pipeline":
            row = await db.get(Pipeline, UUID(node_id))
            if row and row.project_id == project_id:
                return GraphNode("pipeline", node_id, row.topic or "Pipeline", pipeline_id=node_id)
        if node_type == "script":
            row = await db.get(Script, UUID(node_id))
            if row:
                return GraphNode("script", node_id, row.title or "Script", pipeline_id=str(row.pipeline_id))
        if node_type == "video":
            row = await db.get(Video, UUID(node_id))
            if row and row.project_id == project_id:
                return GraphNode(
                    "video",
                    node_id,
                    row.title or "Video",
                    pipeline_id=str(row.pipeline_id) if row.pipeline_id else None,
                )
        if node_type == "knowledge_entry":
            row = await db.get(KnowledgeEntry, UUID(node_id))
            if row and row.project_id == project_id:
                return GraphNode(
                    "knowledge_entry",
                    node_id,
                    row.title or row.resource_type,
                    pipeline_id=str(row.pipeline_id) if row.pipeline_id else None,
                )
        if node_type == "learning_insight":
            row = await db.get(LearningInsightRow, UUID(node_id))
            if row and row.project_id == project_id:
                return GraphNode(
                    "learning_insight",
                    node_id,
                    f"Learning: {row.topic}",
                    pipeline_id=str(row.pipeline_id),
                )
        if node_type in ("specialist", "prompt", "asset"):
            return GraphNode(node_type, node_id, f"{node_type}:{node_id}")

        from contentos_database.models import ContentRelationRow as CR

        rel = (
            await db.execute(
                select(CR)
                .where(CR.project_id == project_id)
                .where(
                    or_(
                        and_(CR.source_type == node_type, CR.source_id == node_id),
                        and_(CR.target_type == node_type, CR.target_id == node_id),
                    )
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if rel:
            return GraphNode(node_type, node_id, f"{node_type}:{node_id}")
        return None

    async def load_project_graph(self, db: AsyncSession, project_id: UUID, *, limit: int = 500) -> GraphView:
        from contentos_database.models import ContentRelationRow

        rows = (
            await db.execute(
                select(ContentRelationRow)
                .where(ContentRelationRow.project_id == project_id)
                .limit(limit)
            )
        ).scalars().all()

        nodes: dict[str, GraphNode] = {}
        edges: list[GraphEdge] = []
        for row in rows:
            edge = _row_to_edge(row)
            edges.append(edge)
            for ntype, nid, label in (
                (row.source_type, row.source_id, row.label_source),
                (row.target_type, row.target_id, row.label_target),
            ):
                key = node_key(ntype, nid)
                if key not in nodes:
                    nodes[key] = GraphNode(
                        node_type=ntype,
                        node_id=nid,
                        label=label or f"{ntype}:{nid}",
                        pipeline_id=str(row.pipeline_id) if row.pipeline_id else None,
                    )

        if nodes:
            await self._enrich_node_labels(db, project_id, nodes)

        return GraphView(project_id=str(project_id), nodes=list(nodes.values()), edges=edges)

    async def _enrich_node_labels(
        self, db: AsyncSession, project_id: UUID, nodes: dict[str, GraphNode]
    ) -> None:
        from contentos_database.models import Pipeline, Script, Video

        for node in nodes.values():
            if node.label and not node.label.startswith(f"{node.node_type}:"):
                continue
            try:
                uid = UUID(node.node_id)
            except ValueError:
                continue
            if node.node_type == "pipeline":
                row = await db.get(Pipeline, uid)
                if row:
                    node.label = row.topic or node.label
            elif node.node_type == "script":
                row = await db.get(Script, uid)
                if row:
                    node.label = row.title or node.label
            elif node.node_type == "video":
                row = await db.get(Video, uid)
                if row and row.project_id == project_id:
                    node.label = row.title or node.label

    def build_pipeline_sync(self, pipeline_id: UUID) -> int:
        try:
            from contentos_database.session import get_session_factory
            from contentos_shared.agents.base import run_async

            async def _run() -> int:
                factory = get_session_factory()
                if factory is None:
                    return 0
                async with factory() as db:
                    from contentos_intelligence.application.content_graph.builder import build_pipeline_graph

                    view = await build_pipeline_graph(db, pipeline_id)
                    if not view.project_id:
                        return 0
                    count = await ContentGraphRepository().replace_pipeline_edges(
                        db, pipeline_id, UUID(view.project_id), view.edges
                    )
                    await db.commit()
                    return count

            return int(run_async(_run()) or 0)
        except Exception:
            return 0


def _row_to_edge(row: Any) -> GraphEdge:
    return GraphEdge(
        source_type=row.source_type,
        source_id=row.source_id,
        target_type=row.target_type,
        target_id=row.target_id,
        relation_type=row.relation_type,
        pipeline_id=str(row.pipeline_id) if row.pipeline_id else None,
        metadata=dict(row.metadata_ or {}),
    )
