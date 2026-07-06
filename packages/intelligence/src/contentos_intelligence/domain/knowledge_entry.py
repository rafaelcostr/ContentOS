"""Knowledge entry domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

VALID_RESOURCE_TYPES = frozenset({
    "script",
    "hook",
    "video",
    "asset",
    "analytics",
    "title",
    "cta",
    "prompt",
})


@dataclass
class KnowledgeEntryData:
    id: UUID | None
    project_id: UUID
    org_id: UUID | None
    pipeline_id: UUID | None
    resource_type: str
    resource_id: UUID | None
    title: str
    content_text: str
    snippet: str = ""
    embedding: list[float] = field(default_factory=list)
    embedding_model: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    version: int = 1
    parent_entry_id: UUID | None = None
    created_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id) if self.id else None,
            "project_id": str(self.project_id),
            "org_id": str(self.org_id) if self.org_id else None,
            "pipeline_id": str(self.pipeline_id) if self.pipeline_id else None,
            "resource_type": self.resource_type,
            "resource_id": str(self.resource_id) if self.resource_id else None,
            "title": self.title,
            "content_text": self.content_text,
            "snippet": self.snippet,
            "embedding_model": self.embedding_model,
            "metadata": dict(self.metadata),
            "version": self.version,
            "parent_entry_id": str(self.parent_entry_id) if self.parent_entry_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "has_embedding": bool(self.embedding),
        }
