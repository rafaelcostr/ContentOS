"""Build content relation edges from pipeline artifacts — Epic 11."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from contentos_shared.payload_utils import coerce_dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contentos_intelligence.domain.content_graph import GraphEdge, GraphNode, GraphView, node_key


def _add_node(nodes: dict[str, GraphNode], node: GraphNode) -> None:
    nodes[node.key] = node


def _add_edge(edges: list[GraphEdge], edge: GraphEdge) -> None:
    edges.append(edge)


def _prompts_from_jobs(jobs: list[Any]) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for job in jobs:
        output = coerce_dict(job.output_data)
        prompts = output.get("prompts_used")
        if isinstance(prompts, dict):
            for prompt_id, version in prompts.items():
                key = f"{prompt_id}:{version}"
                if key not in seen:
                    seen.add(key)
                    found.append((str(prompt_id), str(version)))
        pack = coerce_dict(output.get("specialist_prompt_pack"))
        for prompt_id in pack:
            if prompt_id not in seen:
                seen.add(prompt_id)
                found.append((str(prompt_id), ""))
    return found


def _specialist_from_jobs(jobs: list[Any]) -> tuple[str, str] | None:
    for job in jobs:
        output = coerce_dict(job.output_data)
        selection = coerce_dict(output.get("specialist_selection"))
        specialist = coerce_dict(selection.get("specialist"))
        sid = str(selection.get("specialist_id") or specialist.get("id") or output.get("specialist_id") or "").strip()
        name = str(specialist.get("name") or specialist.get("label") or sid).strip()
        if sid or name:
            return (sid or name, name or sid)
    return None


async def build_pipeline_graph(db: AsyncSession, pipeline_id: UUID) -> GraphView:
    from contentos_database.models import (
        Asset,
        Job,
        KnowledgeEntry,
        LearningInsightRow,
        Pipeline,
        Script,
        Video,
    )

    pipeline = await db.get(Pipeline, pipeline_id)
    if not pipeline:
        return GraphView(project_id="")

    project_id = str(pipeline.project_id)
    pid = str(pipeline.id)
    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []

    _add_node(
        nodes,
        GraphNode(
            node_type="pipeline",
            node_id=pid,
            label=pipeline.topic or "Pipeline",
            pipeline_id=pid,
            metadata={"workflow_name": pipeline.workflow_name, "status": str(pipeline.status.value)},
        ),
    )

    jobs = (
        await db.execute(select(Job).where(Job.pipeline_id == pipeline_id).order_by(Job.order))
    ).scalars().all()

    scripts = (await db.execute(select(Script).where(Script.pipeline_id == pipeline_id))).scalars().all()
    for script in scripts:
        sid = str(script.id)
        _add_node(
            nodes,
            GraphNode(
                node_type="script",
                node_id=sid,
                label=script.title or "Script",
                pipeline_id=pid,
            ),
        )
        _add_edge(
            edges,
            GraphEdge("pipeline", pid, "script", sid, "produces", pipeline_id=pid),
        )
        if script.asset_id:
            aid = str(script.asset_id)
            _add_node(nodes, GraphNode(node_type="asset", node_id=aid, label="Script asset", pipeline_id=pid))
            _add_edge(edges, GraphEdge("script", sid, "asset", aid, "uses", pipeline_id=pid))

    videos = (await db.execute(select(Video).where(Video.pipeline_id == pipeline_id))).scalars().all()
    for video in videos:
        vid = str(video.id)
        _add_node(
            nodes,
            GraphNode(
                node_type="video",
                node_id=vid,
                label=video.title or "Video",
                pipeline_id=pid,
                metadata={"status": video.status},
            ),
        )
        _add_edge(edges, GraphEdge("pipeline", pid, "video", vid, "produces", pipeline_id=pid))
        for script in scripts:
            _add_edge(
                edges,
                GraphEdge("video", vid, "script", str(script.id), "derived_from", pipeline_id=pid),
            )
        for field, label in (("render_asset_id", "Render"), ("thumb_asset_id", "Thumbnail")):
            asset_id = getattr(video, field, None)
            if asset_id:
                aid = str(asset_id)
                _add_node(nodes, GraphNode(node_type="asset", node_id=aid, label=label, pipeline_id=pid))
                _add_edge(edges, GraphEdge("video", vid, "asset", aid, "uses", pipeline_id=pid))

    specialist = _specialist_from_jobs(jobs)
    if specialist:
        sid, name = specialist
        _add_node(
            nodes,
            GraphNode(node_type="specialist", node_id=sid, label=name, pipeline_id=pid),
        )
        _add_edge(edges, GraphEdge("pipeline", pid, "specialist", sid, "selected", pipeline_id=pid))

    for prompt_id, version in _prompts_from_jobs(jobs):
        prompt_node_id = f"{prompt_id}@{version}" if version else prompt_id
        _add_node(
            nodes,
            GraphNode(
                node_type="prompt",
                node_id=prompt_node_id,
                label=f"{prompt_id} {version}".strip(),
                pipeline_id=pid,
            ),
        )
        _add_edge(
            edges,
            GraphEdge("pipeline", pid, "prompt", prompt_node_id, "references", pipeline_id=pid),
        )

    kb_rows = (
        await db.execute(select(KnowledgeEntry).where(KnowledgeEntry.pipeline_id == pipeline_id))
    ).scalars().all()
    for entry in kb_rows:
        eid = str(entry.id)
        _add_node(
            nodes,
            GraphNode(
                node_type="knowledge_entry",
                node_id=eid,
                label=entry.title or entry.resource_type,
                pipeline_id=pid,
                metadata={"resource_type": entry.resource_type},
            ),
        )
        _add_edge(
            edges,
            GraphEdge("knowledge_entry", eid, "pipeline", pid, "indexed_from", pipeline_id=pid),
        )
        if entry.resource_id and entry.resource_type == "script":
            rid = str(entry.resource_id)
            if node_key("script", rid) in nodes:
                _add_edge(
                    edges,
                    GraphEdge("knowledge_entry", eid, "script", rid, "references", pipeline_id=pid),
                )

    learning = (
        await db.execute(select(LearningInsightRow).where(LearningInsightRow.pipeline_id == pipeline_id))
    ).scalar_one_or_none()
    if learning:
        lid = str(learning.id)
        _add_node(
            nodes,
            GraphNode(
                node_type="learning_insight",
                node_id=lid,
                label=f"Learning: {learning.topic}",
                pipeline_id=pid,
                metadata={"content_score": learning.content_score},
            ),
        )
        _add_edge(
            edges,
            GraphEdge("learning_insight", lid, "pipeline", pid, "learned_from", pipeline_id=pid),
        )
        if learning.specialist_id:
            sid = learning.specialist_id
            if node_key("specialist", sid) not in nodes:
                _add_node(nodes, GraphNode(node_type="specialist", node_id=sid, label=sid, pipeline_id=pid))
            _add_edge(
                edges,
                GraphEdge("learning_insight", lid, "specialist", sid, "references", pipeline_id=pid),
            )

    asset_ids = {e.target_id for e in edges if e.target_type == "asset"}
    missing = [UUID(aid) for aid in asset_ids if aid]
    if missing:
        assets = (await db.execute(select(Asset).where(Asset.id.in_(missing)))).scalars().all()
        for asset in assets:
            key = node_key("asset", str(asset.id))
            if key in nodes:
                nodes[key].label = (asset.object_key or "").split("/")[-1] or asset.category or nodes[key].label

    return GraphView(project_id=project_id, nodes=list(nodes.values()), edges=edges)
