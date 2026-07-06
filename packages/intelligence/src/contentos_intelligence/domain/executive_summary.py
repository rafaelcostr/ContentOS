"""Executive Dashboard summary — Epic 12."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModuleStatus:
    key: str
    label: str
    status: str
    metric: str
    href: str
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "status": self.status,
            "metric": self.metric,
            "href": self.href,
            "detail": self.detail,
        }


@dataclass
class ExecutiveSummary:
    project_id: str
    project_name: str
    pipelines_total: int = 0
    pipelines_completed: int = 0
    knowledge_entries: int = 0
    learning_insights: int = 0
    graph_nodes: int = 0
    graph_edges: int = 0
    ab_variant_sets: int = 0
    specialists_available: int = 0
    avg_content_score: float | None = None
    avg_viral_score: float | None = None
    latest_trend_score: float | None = None
    latest_trend_growth: str | None = None
    dna_preview: str = ""
    hook_patterns: list[str] = field(default_factory=list)
    latest_learning_topic: str | None = None
    modules: list[ModuleStatus] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "pipelines_total": self.pipelines_total,
            "pipelines_completed": self.pipelines_completed,
            "knowledge_entries": self.knowledge_entries,
            "learning_insights": self.learning_insights,
            "graph_nodes": self.graph_nodes,
            "graph_edges": self.graph_edges,
            "ab_variant_sets": self.ab_variant_sets,
            "specialists_available": self.specialists_available,
            "avg_content_score": self.avg_content_score,
            "avg_viral_score": self.avg_viral_score,
            "latest_trend_score": self.latest_trend_score,
            "latest_trend_growth": self.latest_trend_growth,
            "dna_preview": self.dna_preview,
            "hook_patterns": list(self.hook_patterns),
            "latest_learning_topic": self.latest_learning_topic,
            "modules": [m.to_dict() for m in self.modules],
        }
