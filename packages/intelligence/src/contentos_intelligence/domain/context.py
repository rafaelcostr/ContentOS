"""Pipeline intelligence context passed between V4 services."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass
class IntelligenceContext:
    """Snapshot of pipeline state for V4 intelligence services."""

    project_id: UUID
    pipeline_id: UUID | None = None
    topic: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    org_id: UUID | None = None
    workflow_name: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": str(self.project_id),
            "pipeline_id": str(self.pipeline_id) if self.pipeline_id else None,
            "topic": self.topic,
            "payload": dict(self.payload),
            "org_id": str(self.org_id) if self.org_id else None,
            "workflow_name": self.workflow_name,
        }
