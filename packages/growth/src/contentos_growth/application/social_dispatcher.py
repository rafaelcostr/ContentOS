"""Safe dispatcher for Social Approval Queue.

The dispatcher converts approval queue items into explicit commands for the
existing Publisher, Scheduler and Growth Execution services. It does not call
external platforms directly and defaults to dry-run unless execution is
explicitly enabled by the caller and the queue item is ready.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Literal, Mapping

DispatchCommandStatus = Literal["prepared", "skipped", "blocked"]
DispatchPlanStatus = Literal["prepared", "partial", "blocked", "empty"]
DispatchTarget = Literal["Publisher", "Scheduler", "Growth Execution"]


@dataclass(frozen=True)
class SocialDispatchCommand:
    id: str
    queue_item_id: str
    operation_id: str
    target: DispatchTarget
    status: DispatchCommandStatus
    dry_run: bool = True
    payload: dict[str, Any] = field(default_factory=dict)
    reason: str | None = None
    audit_event: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "queue_item_id": self.queue_item_id,
            "operation_id": self.operation_id,
            "target": self.target,
            "status": self.status,
            "dry_run": self.dry_run,
            "payload": dict(self.payload),
            "reason": self.reason,
            "audit_event": dict(self.audit_event),
        }


@dataclass(frozen=True)
class SocialDispatchPlan:
    project_id: str
    status: DispatchPlanStatus
    summary: str
    commands: list[SocialDispatchCommand] = field(default_factory=list)
    skipped_items: list[dict[str, Any]] = field(default_factory=list)
    execution_contract: dict[str, Any] = field(default_factory=dict)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "status": self.status,
            "summary": self.summary,
            "commands": [command.to_dict() for command in self.commands],
            "skipped_items": [dict(item) for item in self.skipped_items],
            "execution_contract": dict(self.execution_contract),
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


def _command_id(project_id: str, item_id: str, target: str) -> str:
    raw = f"{project_id}|{item_id}|{target}"
    return sha256(raw.encode("utf-8")).hexdigest()[:16]


def _audit_event(
    *,
    project_id: str,
    actor_id: str | None,
    queue_item_id: str,
    operation_id: str,
    target: str,
    status: str,
    dry_run: bool,
    generated_at: str,
) -> dict[str, Any]:
    return {
        "event": "social_dispatch_command",
        "project_id": project_id,
        "actor_id": actor_id,
        "queue_item_id": queue_item_id,
        "operation_id": operation_id,
        "target": target,
        "status": status,
        "dry_run": dry_run,
        "created_at": generated_at,
    }


def _build_command(
    *,
    project_id: str,
    item: dict[str, Any],
    target: DispatchTarget,
    payload: dict[str, Any],
    execute: bool,
    actor_id: str | None,
    generated_at: str,
) -> SocialDispatchCommand:
    item_id = str(item.get("id") or "")
    operation_id = str(item.get("operation_id") or "")
    dry_run = not execute
    status: DispatchCommandStatus = "prepared"
    command_payload = dict(payload)
    command_payload["dispatch_mode"] = "execute" if execute else "dry_run"
    command_payload["queue_item_id"] = item_id
    return SocialDispatchCommand(
        id=_command_id(project_id, item_id, target),
        queue_item_id=item_id,
        operation_id=operation_id,
        target=target,
        status=status,
        dry_run=dry_run,
        payload=command_payload,
        audit_event=_audit_event(
            project_id=project_id,
            actor_id=actor_id,
            queue_item_id=item_id,
            operation_id=operation_id,
            target=target,
            status=status,
            dry_run=dry_run,
            generated_at=generated_at,
        ),
    )


def build_social_dispatch_plan(
    *,
    project_id: str,
    queue_items: list[Mapping[str, Any] | Any] | None = None,
    execute: bool = False,
    actor_id: str | None = None,
    allow_review_items: bool = False,
) -> SocialDispatchPlan:
    items = [_as_dict(item) for item in queue_items or []]
    generated_at = datetime.now(timezone.utc).isoformat()
    commands: list[SocialDispatchCommand] = []
    skipped: list[dict[str, Any]] = []

    for item in items:
        item_id = str(item.get("id") or "")
        operation_id = str(item.get("operation_id") or "")
        status = str(item.get("status") or "needs_review")
        if status == "blocked":
            skipped.append(
                {
                    "queue_item_id": item_id,
                    "operation_id": operation_id,
                    "status": "blocked",
                    "reason": "Item bloqueado pela governança ou aprovação.",
                }
            )
            continue
        if status == "needs_review" and not allow_review_items:
            skipped.append(
                {
                    "queue_item_id": item_id,
                    "operation_id": operation_id,
                    "status": "needs_review",
                    "reason": "Item exige revisão manual antes do dispatch.",
                }
            )
            continue

        publisher_payload = _as_dict(item.get("publisher_payload"))
        scheduler_payload = _as_dict(item.get("scheduler_payload"))
        if publisher_payload:
            commands.append(
                _build_command(
                    project_id=project_id,
                    item=item,
                    target="Publisher",
                    payload=publisher_payload,
                    execute=execute and status == "ready",
                    actor_id=actor_id,
                    generated_at=generated_at,
                )
            )
        if scheduler_payload:
            commands.append(
                _build_command(
                    project_id=project_id,
                    item=item,
                    target="Scheduler",
                    payload=scheduler_payload,
                    execute=execute and status == "ready",
                    actor_id=actor_id,
                    generated_at=generated_at,
                )
            )

        if not publisher_payload and not scheduler_payload:
            commands.append(
                _build_command(
                    project_id=project_id,
                    item=item,
                    target="Growth Execution",
                    payload={
                        "delegate_to": "Growth Execution",
                        "operation_id": operation_id,
                        "operation_kind": item.get("operation_kind"),
                        "platform": item.get("platform"),
                        "title": item.get("title"),
                    },
                    execute=execute and status == "ready",
                    actor_id=actor_id,
                    generated_at=generated_at,
                )
            )

    prepared = sum(1 for command in commands if command.status == "prepared")
    blocked = sum(1 for item in skipped if item.get("status") == "blocked")
    review = sum(1 for item in skipped if item.get("status") == "needs_review")
    if not commands and not skipped:
        status: DispatchPlanStatus = "empty"
    elif commands and not skipped:
        status = "prepared"
    elif commands:
        status = "partial"
    else:
        status = "blocked"

    return SocialDispatchPlan(
        project_id=project_id,
        status=status,
        summary=f"Dispatch social {status}: {prepared} comando(s), {review} revisão(ões), {blocked} bloqueado(s).",
        commands=commands,
        skipped_items=skipped,
        execution_contract={
            "default_dry_run": True,
            "execute_requested": bool(execute),
            "publishes_directly": False,
            "delegates_to_existing_services": ["Publisher", "Scheduler", "Growth Execution"],
            "review_items_require_override": True,
        },
        generated_at=generated_at,
    )
