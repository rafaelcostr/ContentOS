"""Multi-content text artifacts — Epic 2a."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

TEXT_FORMATS = frozenset({"thread_x", "linkedin_post", "newsletter", "seo_article", "email_marketing"})


@dataclass
class TextArtifact:
    format: str
    title: str
    content: str
    data: dict[str, Any] = field(default_factory=dict)
    source: str = "heuristic"

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": self.format,
            "title": self.title,
            "content": self.content,
            "data": dict(self.data),
            "source": self.source,
        }


@dataclass
class MultiContentReport:
    project_id: str
    pipeline_id: str | None
    topic: str
    artifacts: list[TextArtifact] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "pipeline_id": self.pipeline_id,
            "topic": self.topic,
            "artifact_count": len(self.artifacts),
            "artifacts": [a.to_dict() for a in self.artifacts],
            "by_format": {a.format: a.to_dict() for a in self.artifacts},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MultiContentReport:
        artifacts = [
            TextArtifact(
                format=str(a.get("format", "")),
                title=str(a.get("title", "")),
                content=str(a.get("content", "")),
                data=dict(a.get("data") or {}),
                source=str(a.get("source", "heuristic")),
            )
            for a in data.get("artifacts") or []
        ]
        return cls(
            project_id=str(data.get("project_id", "")),
            pipeline_id=str(data["pipeline_id"]) if data.get("pipeline_id") else None,
            topic=str(data.get("topic", "")),
            artifacts=artifacts,
        )
