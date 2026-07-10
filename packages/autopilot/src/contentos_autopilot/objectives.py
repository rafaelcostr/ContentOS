"""Objective Engine contracts for Autopilot.

The objective engine is pure. It models why a piece of content should exist and
returns metadata that other modules can attach to plans or calendar items.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha1
from typing import Any, Literal, Mapping

ObjectiveLevel = Literal[
    "company",
    "project",
    "channel",
    "monthly",
    "weekly",
    "daily",
    "campaign",
    "series",
    "content",
]


@dataclass(frozen=True)
class ObjectiveNode:
    id: str
    level: ObjectiveLevel
    title: str
    parent_id: str | None = None
    priority: str = "medium"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "level": self.level,
            "title": self.title,
            "parent_id": self.parent_id,
            "priority": self.priority,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ObjectiveTree:
    project_id: str
    nodes: list[ObjectiveNode] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "nodes": [node.to_dict() for node in self.nodes],
        }

    def node_by_id(self) -> dict[str, ObjectiveNode]:
        return {node.id: node for node in self.nodes}

    def path_for(self, objective_id: str) -> list[ObjectiveNode]:
        by_id = self.node_by_id()
        path: list[ObjectiveNode] = []
        current = by_id.get(objective_id)
        while current:
            path.append(current)
            current = by_id.get(current.parent_id or "")
        path.reverse()
        return path

    def best_for_topic(self, topic: str, *, channel_id: str | None = None) -> ObjectiveNode | None:
        text = topic.lower()
        channel_nodes = [node for node in self.nodes if node.level == "channel"]
        if channel_id:
            channel_nodes = [node for node in channel_nodes if node.metadata.get("channel_id") == channel_id]
        candidates = [
            node
            for node in self.nodes
            if node.level in {"campaign", "series", "weekly", "daily", "project"}
            and (node.title.lower() in text or text in node.title.lower())
        ]
        if candidates:
            return candidates[0]
        if channel_nodes:
            return channel_nodes[0]
        return next((node for node in self.nodes if node.level == "project"), None)


def _slug(value: str, *, limit: int = 64) -> str:
    cleaned = "-".join(str(value or "").lower().strip().split())
    return cleaned[:limit] or "objective"


def _stable_id(*parts: str) -> str:
    raw = ":".join(parts)
    digest = sha1(raw.encode("utf-8")).hexdigest()[:10]
    return f"{_slug(parts[-1])}-{digest}"


def _as_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return {}


def build_objective_tree(
    *,
    project_id: str,
    strategy: Mapping[str, Any] | Any | None = None,
    channels: list[Mapping[str, Any] | Any] | None = None,
) -> ObjectiveTree:
    strategy_data = _as_mapping(strategy or {})
    goals = [str(goal).strip() for goal in strategy_data.get("goals") or [] if str(goal).strip()]
    positioning = str(strategy_data.get("positioning") or "").strip()
    project_title = positioning or (goals[0] if goals else "Crescer o projeto com conteudo consistente")

    project = ObjectiveNode(
        id=_stable_id(project_id, "project", project_title),
        level="project",
        title=project_title,
        priority="high",
        metadata={"project_id": project_id, "source": "growth_strategy"},
    )
    nodes = [project]

    cadence = dict(strategy_data.get("cadence") or {})
    monthly = ObjectiveNode(
        id=_stable_id(project.id, "monthly", project_title),
        level="monthly",
        title=f"Meta mensal: {project_title}",
        parent_id=project.id,
        priority="high",
        metadata={"weekly_posts": cadence.get("weekly_posts"), "monthly_posts": cadence.get("monthly_posts")},
    )
    weekly = ObjectiveNode(
        id=_stable_id(monthly.id, "weekly", project_title),
        level="weekly",
        title=f"Meta semanal: {project_title}",
        parent_id=monthly.id,
        priority="high",
        metadata={"posting_hours": cadence.get("posting_hours") or []},
    )
    daily = ObjectiveNode(
        id=_stable_id(weekly.id, "daily", project_title),
        level="daily",
        title=f"Decidir o melhor conteudo do dia para {project_title}",
        parent_id=weekly.id,
        priority="medium",
    )
    nodes.extend([monthly, weekly, daily])

    for channel in channels or []:
        channel_data = _as_mapping(channel)
        channel_id = str(channel_data.get("channel_id") or channel_data.get("id") or "").strip()
        channel_name = str(channel_data.get("name") or channel_id or "Canal").strip()
        node = ObjectiveNode(
            id=_stable_id(project.id, "channel", channel_id or channel_name),
            level="channel",
            title=f"{channel_name}: executar estrategia do projeto",
            parent_id=project.id,
            priority="high",
            metadata={
                "channel_id": channel_id,
                "platform": channel_data.get("platform"),
                "score": channel_data.get("score"),
            },
        )
        nodes.append(node)

    for index, goal in enumerate(goals[:8]):
        nodes.append(
            ObjectiveNode(
                id=_stable_id(project.id, "campaign", goal),
                level="campaign",
                title=goal,
                parent_id=weekly.id,
                priority="high" if index == 0 else "medium",
                metadata={"source": "growth_strategy_goal", "rank": index + 1},
            )
        )

    return ObjectiveTree(project_id=project_id, nodes=nodes)


def objective_metadata_for_topic(
    *,
    tree: ObjectiveTree,
    topic: str,
    channel_id: str | None = None,
) -> dict[str, Any]:
    objective = tree.best_for_topic(topic, channel_id=channel_id)
    if not objective:
        return {"objective_status": "missing", "objective_path": []}
    path = tree.path_for(objective.id)
    return {
        "objective_id": objective.id,
        "objective_title": objective.title,
        "objective_level": objective.level,
        "objective_path": [node.title for node in path],
        "objective_status": "linked",
    }
