"""Domain event model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from contentos_events.domain.event_types import (
    QUALITY_REJECTED,
    STEP_COMPLETED,
    STEP_FAILED,
    STEP_TO_DOMAIN_EVENT,
)


@dataclass
class DomainEvent:
    event_type: str
    pipeline_id: UUID | None = None
    project_id: UUID | None = None
    job_id: UUID | None = None
    agent: str | None = None
    step: str | None = None
    status: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.event_type,
            "event_type": self.event_type,
            "pipeline_id": str(self.pipeline_id) if self.pipeline_id else None,
            "project_id": str(self.project_id) if self.project_id else None,
            "job_id": str(self.job_id) if self.job_id else None,
            "agent": self.agent,
            "step": self.step,
            "status": self.status,
            "data": self.payload,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_workflow_event(cls, event: Any) -> "DomainEvent":
        return cls(
            event_type=getattr(event, "type", "unknown"),
            pipeline_id=getattr(event, "pipeline_id", None),
            job_id=getattr(event, "job_id", None),
            step=getattr(event, "step", None),
            agent=getattr(event, "step", None),
            status=getattr(event, "status", None),
            payload=dict(getattr(event, "data", {}) or {}),
            timestamp=getattr(event, "timestamp", datetime.now(timezone.utc)),
        )

    @classmethod
    def from_agent_callback(
        cls,
        *,
        step: str,
        project_id: UUID,
        pipeline_id: UUID,
        job_id: UUID,
        status: str,
        payload: dict[str, Any] | None = None,
    ) -> "DomainEvent":
        if status == "completed":
            event_type = STEP_TO_DOMAIN_EVENT.get(step, STEP_COMPLETED)
        elif status == "failed":
            event_type = QUALITY_REJECTED if step == "quality" else STEP_FAILED
        else:
            event_type = STEP_COMPLETED
        return cls(
            event_type=event_type,
            pipeline_id=pipeline_id,
            project_id=project_id,
            job_id=job_id,
            agent=step,
            step=step,
            status=status,
            payload=payload or {},
        )
