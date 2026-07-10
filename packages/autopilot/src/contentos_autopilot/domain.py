"""Pure Autopilot contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Protocol

AutopilotMode = Literal["manual", "assisted", "automatic"]
AutopilotDecisionStatus = Literal["ready", "partial", "blocked"]


@dataclass(frozen=True)
class AutopilotSignal:
    source: str
    kind: str
    title: str
    detail: str = ""
    priority: str = "medium"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "kind": self.kind,
            "title": self.title,
            "detail": self.detail,
            "priority": self.priority,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class AutopilotAction:
    action: str
    title: str
    detail: str
    priority: str = "medium"
    delegate_to: str | None = None
    can_delegate: bool = False
    block_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "title": self.title,
            "detail": self.detail,
            "priority": self.priority,
            "delegate_to": self.delegate_to,
            "can_delegate": self.can_delegate,
            "block_reason": self.block_reason,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class AutopilotContext:
    project_id: str
    mode: AutopilotMode = "assisted"
    status: str = "unknown"
    score: int = 0
    summary: str = ""
    signals: list[AutopilotSignal] = field(default_factory=list)
    candidate_actions: list[AutopilotAction] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "mode": self.mode,
            "status": self.status,
            "score": self.score,
            "summary": self.summary,
            "signals": [signal.to_dict() for signal in self.signals],
            "candidate_actions": [action.to_dict() for action in self.candidate_actions],
            "blockers": list(self.blockers),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class AutopilotDecision:
    project_id: str
    mode: AutopilotMode
    status: AutopilotDecisionStatus
    summary: str
    score: int
    actions: list[AutopilotAction] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    signals: list[AutopilotSignal] = field(default_factory=list)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "mode": self.mode,
            "status": self.status,
            "summary": self.summary,
            "score": self.score,
            "actions": [action.to_dict() for action in self.actions],
            "blockers": list(self.blockers),
            "signals": [signal.to_dict() for signal in self.signals],
            "generated_at": self.generated_at,
        }


class AutopilotContextProvider(Protocol):
    async def build_context(
        self,
        project_id: str,
        *,
        mode: AutopilotMode = "assisted",
        horizon_days: int = 7,
        max_actions: int = 5,
    ) -> AutopilotContext: ...


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
