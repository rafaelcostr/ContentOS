"""SLO domain models — V5.5.3."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

SloState = Literal["ok", "warning", "critical", "unknown"]


@dataclass
class SloDefinition:
    id: str
    name: str
    description: str
    target: str
    runbook_id: str
    category: str = "platform"


@dataclass
class SloInfraSnapshot:
    redis_healthy: bool | None = None
    postgres_healthy: bool | None = None
    postgres_latency_ms: float | None = None
    celery_workers: int = 0
    celery_pending_total: int = 0
    pipeline_completed_24h: int = 0
    pipeline_failed_24h: int = 0
    job_completed_24h: int = 0
    job_failed_24h: int = 0


@dataclass
class SloStatus:
    id: str
    name: str
    state: SloState
    target: str
    current: str
    runbook_id: str
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "state": self.state,
            "target": self.target,
            "current": self.current,
            "runbook_id": self.runbook_id,
            "message": self.message,
        }


@dataclass
class SloReport:
    items: list[SloStatus] = field(default_factory=list)
    evaluated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluated_at": self.evaluated_at,
            "items": [i.to_dict() for i in self.items],
            "summary": {
                "ok": sum(1 for i in self.items if i.state == "ok"),
                "warning": sum(1 for i in self.items if i.state == "warning"),
                "critical": sum(1 for i in self.items if i.state == "critical"),
            },
        }
