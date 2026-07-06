from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID


@dataclass
class WorkflowEvent:
    type: str
    pipeline_id: UUID | None = None
    job_id: UUID | None = None
    step: str | None = None
    status: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "pipeline_id": str(self.pipeline_id) if self.pipeline_id else None,
            "job_id": str(self.job_id) if self.job_id else None,
            "step": self.step,
            "status": self.status,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }
