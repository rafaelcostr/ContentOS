from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from contentos_shared.schemas.asset import AssetRef


@dataclass
class AgentTaskInput:
    job_id: UUID
    pipeline_id: UUID
    project_id: UUID
    step: str
    payload: dict[str, Any] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentTaskOutput:
    job_id: UUID
    status: str
    artifacts: list[AssetRef] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    logs: list[str] = field(default_factory=list)
    error: str | None = None
