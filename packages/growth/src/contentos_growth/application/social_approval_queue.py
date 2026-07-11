"""Approval queue for Social Autopilot handoff.

The queue turns a governed social plan into reviewable execution items. It does
not publish content; it prepares explicit handoff contracts for the existing
Publisher and Scheduler.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Literal, Mapping

ApprovalItemStatus = Literal["ready", "needs_review", "blocked"]
ApprovalQueueStatus = Literal["ready", "review_required", "blocked", "empty"]


@dataclass(frozen=True)
class SocialApprovalItem:
    id: str
    operation_id: str
    operation_kind: str
    title: str
    platform: str
    status: ApprovalItemStatus
    priority: str = "medium"
    required_actions: list[str] = field(default_factory=list)
    publisher_payload: dict[str, Any] | None = None
    scheduler_payload: dict[str, Any] | None = None
    audit_event: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "operation_id": self.operation_id,
            "operation_kind": self.operation_kind,
            "title": self.title,
            "platform": self.platform,
            "status": self.status,
            "priority": self.priority,
            "required_actions": list(self.required_actions),
            "publisher_payload": dict(self.publisher_payload) if self.publisher_payload else None,
            "scheduler_payload": dict(self.scheduler_payload) if self.scheduler_payload else None,
            "audit_event": dict(self.audit_event),
        }


@dataclass(frozen=True)
class SocialApprovalQueue:
    project_id: str
    status: ApprovalQueueStatus
    summary: str
    items: list[SocialApprovalItem] = field(default_factory=list)
    publisher_contract: dict[str, Any] = field(default_factory=dict)
    scheduler_contract: dict[str, Any] = field(default_factory=dict)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "status": self.status,
            "summary": self.summary,
            "items": [item.to_dict() for item in self.items],
            "publisher_contract": dict(self.publisher_contract),
            "scheduler_contract": dict(self.scheduler_contract),
            "generated_at": self.generated_at,
        }


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        return dict(value.to_dict())
    return {}


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _queue_item_id(project_id: str, operation_id: str, status: str) -> str:
    raw = f"{project_id}|{operation_id}|{status}"
    return sha256(raw.encode("utf-8")).hexdigest()[:16]


def _decision_by_operation(governance_contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    decisions: dict[str, dict[str, Any]] = {}
    for decision in _as_list(governance_contract.get("decisions")):
        data = _as_dict(decision)
        operation_id = str(data.get("operation_id") or "")
        if operation_id:
            decisions[operation_id] = data
    return decisions


def _fallback_operation_id(project_id: str, operation: dict[str, Any]) -> str:
    raw = "|".join(
        [
            project_id,
            str(operation.get("kind") or "operation"),
            str(operation.get("platform") or "unknown"),
            str(operation.get("title") or ""),
            str(operation.get("calendar_item_id") or ""),
        ]
    )
    return sha256(raw.encode("utf-8")).hexdigest()[:16]


def _item_status(decision: dict[str, Any]) -> ApprovalItemStatus:
    status = str(decision.get("status") or "review_required")
    if status == "blocked":
        return "blocked"
    if status == "allowed":
        return "ready"
    return "needs_review"


def _publisher_payload(operation: dict[str, Any], operation_id: str, status: ApprovalItemStatus) -> dict[str, Any] | None:
    execution = _as_dict(operation.get("execution"))
    if str(execution.get("delegate_to") or "").lower() != "publisher":
        return None
    return {
        "delegate_to": "Publisher",
        "operation_id": operation_id,
        "platform": operation.get("platform"),
        "channel_id": operation.get("channel_id"),
        "title": operation.get("title"),
        "publish_mode": execution.get("publish_mode", "prepare_only"),
        "target_platform": execution.get("target_platform") or operation.get("platform"),
        "status": "hold" if status != "ready" else "ready",
        "requires_manual_approval": status != "ready",
    }


def _scheduler_payload(operation: dict[str, Any], operation_id: str, status: ApprovalItemStatus) -> dict[str, Any] | None:
    if status == "blocked":
        return None
    execution = _as_dict(operation.get("execution"))
    return {
        "delegate_to": "Scheduler",
        "operation_id": operation_id,
        "calendar_item_id": operation.get("calendar_item_id"),
        "platform": operation.get("platform"),
        "priority": operation.get("priority", "medium"),
        "action": "schedule_execution" if status == "ready" else "schedule_review",
        "downstream_delegate": execution.get("delegate_to"),
    }


def build_social_approval_queue(
    *,
    project_id: str,
    operations: list[Mapping[str, Any] | Any] | None = None,
    governance_contract: Mapping[str, Any] | Any | None = None,
    actor_id: str | None = None,
) -> SocialApprovalQueue:
    op_rows = [_as_dict(item) for item in operations or []]
    governance = _as_dict(governance_contract or {})
    decisions = _decision_by_operation(governance)
    generated_at = datetime.now(timezone.utc).isoformat()
    items: list[SocialApprovalItem] = []

    for operation in op_rows:
        operation_id = _fallback_operation_id(project_id, operation)
        decision = decisions.get(operation_id, {})
        status = _item_status(decision)
        required_actions = [str(item) for item in _as_list(decision.get("required_actions"))]
        if not required_actions and status == "needs_review":
            required_actions = ["Revisar e aprovar manualmente antes de executar."]
        audit_event = {
            "event": "social_approval_queue_item",
            "project_id": project_id,
            "actor_id": actor_id,
            "operation_id": operation_id,
            "status": status,
            "created_at": generated_at,
        }
        items.append(
            SocialApprovalItem(
                id=_queue_item_id(project_id, operation_id, status),
                operation_id=operation_id,
                operation_kind=str(operation.get("kind") or "operation"),
                title=str(operation.get("title") or "Operação social"),
                platform=str(operation.get("platform") or "unknown"),
                status=status,
                priority=str(operation.get("priority") or "medium"),
                required_actions=required_actions,
                publisher_payload=_publisher_payload(operation, operation_id, status),
                scheduler_payload=_scheduler_payload(operation, operation_id, status),
                audit_event=audit_event,
            )
        )

    blocked = sum(1 for item in items if item.status == "blocked")
    review = sum(1 for item in items if item.status == "needs_review")
    ready = sum(1 for item in items if item.status == "ready")
    if not items:
        status: ApprovalQueueStatus = "empty"
    elif blocked:
        status = "blocked"
    elif review:
        status = "review_required"
    else:
        status = "ready"

    return SocialApprovalQueue(
        project_id=project_id,
        status=status,
        summary=f"Fila social {status}: {ready} pronto(s), {review} revisão(ões), {blocked} bloqueado(s).",
        items=items,
        publisher_contract={
            "uses_existing_publisher": True,
            "publishes_directly": False,
            "handoff_field": "publisher_payload",
        },
        scheduler_contract={
            "uses_existing_scheduler": True,
            "creates_scheduler_engine": False,
            "handoff_field": "scheduler_payload",
        },
        generated_at=generated_at,
    )
