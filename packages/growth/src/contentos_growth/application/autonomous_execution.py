"""Autonomous assisted execution planner for Growth Autopilot."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from contentos_growth.application.channel_manager import ChannelDailyPlan

ExecutionStatus = Literal["ready", "blocked", "partial"]

EXECUTABLE_ACTIONS = frozenset({"produce", "schedule", "generate_post", "analyze"})


@dataclass(frozen=True)
class AutonomousExecutionAction:
    channel_id: str
    project_id: str
    platform: str
    channel_name: str
    action: str
    title: str
    detail: str
    priority: str
    calendar_item_id: str | None = None
    can_execute: bool = False
    block_reason: str | None = None
    execution: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "project_id": self.project_id,
            "platform": self.platform,
            "channel_name": self.channel_name,
            "action": self.action,
            "title": self.title,
            "detail": self.detail,
            "priority": self.priority,
            "calendar_item_id": self.calendar_item_id,
            "can_execute": self.can_execute,
            "block_reason": self.block_reason,
            "execution": dict(self.execution),
        }


@dataclass(frozen=True)
class AutonomousExecutionPlan:
    project_id: str
    mode: str
    status: ExecutionStatus
    summary: str
    actions: list[AutonomousExecutionAction] = field(default_factory=list)
    blocked_actions: list[AutonomousExecutionAction] = field(default_factory=list)
    guardrails: list[str] = field(default_factory=list)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "mode": self.mode,
            "status": self.status,
            "summary": self.summary,
            "actions": [action.to_dict() for action in self.actions],
            "blocked_actions": [action.to_dict() for action in self.blocked_actions],
            "guardrails": list(self.guardrails),
            "generated_at": self.generated_at,
        }


def _priority_rank(priority: str) -> int:
    return {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(priority, 2)


def _action_from_channel_plan(plan: ChannelDailyPlan, action: dict[str, Any]) -> AutonomousExecutionAction:
    return AutonomousExecutionAction(
        channel_id=plan.channel_id,
        project_id=plan.project_id,
        platform=plan.platform,
        channel_name=plan.channel_name,
        action=str(action.get("action") or ""),
        title=str(action.get("title") or ""),
        detail=str(action.get("detail") or ""),
        priority=str(action.get("priority") or "medium"),
        calendar_item_id=str(action.get("calendar_item_id")) if action.get("calendar_item_id") else None,
        can_execute=bool(action.get("can_execute")),
        block_reason=action.get("block_reason"),
        execution=dict(action.get("execution") or {}),
    )


def build_autonomous_execution_plan(
    *,
    project_id: str,
    channel_plans: list[ChannelDailyPlan],
    mode: str = "assisted",
    max_actions: int = 5,
) -> AutonomousExecutionPlan:
    guardrails = [
        "dry_run deve ser usado para revisar antes da execução real.",
        "Publicação direta continua bloqueada quando OAuth/API da plataforma não estiver conectado.",
        "A execução real respeita rate limit, permissões de editor, quotas e billing.",
    ]
    ready: list[AutonomousExecutionAction] = []
    blocked: list[AutonomousExecutionAction] = []

    for plan in channel_plans:
        for raw_action in plan.to_dict().get("actions") or []:
            action = _action_from_channel_plan(plan, raw_action)
            if action.action not in EXECUTABLE_ACTIONS:
                continue
            if action.can_execute:
                ready.append(action)
            else:
                blocked.append(action)

    ready.sort(key=lambda item: (_priority_rank(item.priority), item.channel_name, item.title))
    blocked.sort(key=lambda item: (_priority_rank(item.priority), item.channel_name, item.title))
    limited = ready[: max(1, max_actions)]

    if limited:
        status: ExecutionStatus = "ready"
    elif blocked:
        status = "blocked"
    else:
        status = "partial"

    summary = (
        f"Plano de execução {mode}: {len(limited)} ação(ões) pronta(s), "
        f"{len(blocked)} bloqueada(s), {len(channel_plans)} canal(is) analisado(s)."
    )
    return AutonomousExecutionPlan(
        project_id=project_id,
        mode=mode,
        status=status,
        summary=summary,
        actions=limited,
        blocked_actions=blocked,
        guardrails=guardrails,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
