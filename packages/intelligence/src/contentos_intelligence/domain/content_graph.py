"""Content Relation Graph domain — Epic 11."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

NODE_TYPES = frozenset({
    "pipeline",
    "video",
    "script",
    "asset",
    "specialist",
    "prompt",
    "knowledge_entry",
    "learning_insight",
})

RELATION_TYPES = frozenset({
    "produces",
    "derived_from",
    "uses",
    "selected",
    "indexed_from",
    "references",
    "learned_from",
})


def node_key(node_type: str, node_id: str) -> str:
    return f"{node_type}:{node_id}"


@dataclass
class GraphNode:
    node_type: str
    node_id: str
    label: str = ""
    pipeline_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> str:
        return node_key(self.node_type, self.node_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.key,
            "type": self.node_type,
            "node_id": self.node_id,
            "label": self.label,
            "pipeline_id": self.pipeline_id,
            "metadata": dict(self.metadata),
        }


@dataclass
class GraphEdge:
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    relation_type: str
    pipeline_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def source_key(self) -> str:
        return node_key(self.source_type, self.source_id)

    @property
    def target_key(self) -> str:
        return node_key(self.target_type, self.target_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source_key,
            "target": self.target_key,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "relation": self.relation_type,
            "pipeline_id": self.pipeline_id,
            "metadata": dict(self.metadata),
        }


@dataclass
class GraphView:
    project_id: str
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }


@dataclass
class NeighborsView:
    node: GraphNode
    outgoing: list[GraphEdge] = field(default_factory=list)
    incoming: list[GraphEdge] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node": self.node.to_dict(),
            "outgoing": [e.to_dict() for e in self.outgoing],
            "incoming": [e.to_dict() for e in self.incoming],
        }
