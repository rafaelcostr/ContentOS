"""Temporal closed-learning contracts for Autopilot.

This module plans post-publication review cycles. It does not create scheduler
rows, call platform APIs, mutate memory, or rewrite prompts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Mapping

CycleMilestone = Literal["24h", "48h", "7d", "30d"]
CycleStatus = Literal["scheduled", "due", "blocked", "completed"]
TemporalPlanStatus = Literal["ready", "learning", "blocked"]

DEFAULT_MILESTONES: tuple[tuple[CycleMilestone, timedelta], ...] = (
    ("24h", timedelta(hours=24)),
    ("48h", timedelta(hours=48)),
    ("7d", timedelta(days=7)),
    ("30d", timedelta(days=30)),
)


@dataclass(frozen=True)
class ClosedLoopCycle:
    milestone: CycleMilestone
    due_at: str
    status: CycleStatus
    objective_status: str = "unknown"
    scheduler_action: str = "closed_loop_sync"
    compare_with_objectives: bool = True
    recommendations_version: int = 1
    memory_update_mode: str = "assisted"
    summary: str = ""
    actions: list[dict[str, Any]] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "milestone": self.milestone,
            "due_at": self.due_at,
            "status": self.status,
            "objective_status": self.objective_status,
            "scheduler_action": self.scheduler_action,
            "compare_with_objectives": self.compare_with_objectives,
            "recommendations_version": self.recommendations_version,
            "memory_update_mode": self.memory_update_mode,
            "summary": self.summary,
            "actions": [dict(item) for item in self.actions],
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class ClosedLoopCyclePolicy:
    project_id: str
    status: TemporalPlanStatus
    summary: str
    cycles: list[ClosedLoopCycle] = field(default_factory=list)
    objective_comparison: dict[str, Any] = field(default_factory=dict)
    versioned_recommendations: list[dict[str, Any]] = field(default_factory=list)
    memory_update_proposals: list[dict[str, Any]] = field(default_factory=list)
    scheduler_contract: dict[str, Any] = field(default_factory=dict)
    guardrails: list[str] = field(default_factory=list)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "status": self.status,
            "summary": self.summary,
            "cycles": [cycle.to_dict() for cycle in self.cycles],
            "objective_comparison": dict(self.objective_comparison),
            "versioned_recommendations": [dict(item) for item in self.versioned_recommendations],
            "memory_update_proposals": [dict(item) for item in self.memory_update_proposals],
            "scheduler_contract": dict(self.scheduler_contract),
            "guardrails": list(self.guardrails),
            "generated_at": self.generated_at,
        }


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        return dict(value.to_dict())
    return {}


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list | tuple) else []


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    raw = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _objective_status(score: int, blockers: list[Any], objective_count: int) -> str:
    if blockers:
        return "blocked"
    if objective_count <= 0:
        return "learning"
    if score >= 70:
        return "on_track"
    if score >= 45:
        return "at_risk"
    return "missed"


def _recommendations(
    *,
    project_id: str,
    closed_loop: dict[str, Any],
    objective_status: str,
    version: int,
) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []
    if objective_status in {"at_risk", "missed", "blocked"}:
        recommendations.append(
            {
                "project_id": project_id,
                "channel_id": None,
                "kind": "closed_learning",
                "title": f"Revisar objetivos do ciclo temporal v{version}",
                "detail": "Comparar score, retenção, CTR e aprendizados do ciclo com os objetivos ativos.",
                "priority": "high" if objective_status in {"missed", "blocked"} else "medium",
                "source": f"closed_learning_temporal:v{version}",
                "status": "open",
            }
        )
    for update in _as_list(closed_loop.get("calendar_updates"))[:2]:
        detail = str(_as_dict(update).get("detail") or _as_dict(update).get("title") or "")
        if detail:
            recommendations.append(
                {
                    "project_id": project_id,
                    "channel_id": None,
                    "kind": "calendar",
                    "title": f"Criar variação do aprendizado v{version}",
                    "detail": detail,
                    "priority": "medium",
                    "source": f"closed_learning_temporal:v{version}",
                    "status": "open",
                }
            )
    return recommendations[:5]


def build_closed_loop_cycle_policy(
    *,
    project_id: str,
    published_at: str | None = None,
    closed_loop_report: Mapping[str, Any] | Any | None = None,
    objectives: Mapping[str, Any] | Any | None = None,
    now: datetime | None = None,
    recommendations_version: int = 1,
) -> ClosedLoopCyclePolicy:
    baseline = _parse_dt(published_at)
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    loop = _as_dict(closed_loop_report or {})
    objective_data = _as_dict(objectives or {})
    objective_nodes = _as_list(objective_data.get("nodes"))
    blockers = _as_list(loop.get("blockers"))
    score = int(float(loop.get("score") or 0))
    objective_status = _objective_status(score, blockers, len(objective_nodes))

    cycles: list[ClosedLoopCycle] = []
    for milestone, offset in DEFAULT_MILESTONES:
        due = baseline + offset
        due_at = due.isoformat()
        status: CycleStatus = "due" if due <= current else "scheduled"
        if blockers and milestone in {"24h", "48h"}:
            status = "blocked"
        actions = [
            {
                "type": "scheduler",
                "delegate_to": "Scheduler",
                "action": "closed_loop_sync",
                "due_at": due_at,
                "milestone": milestone,
            },
            {
                "type": "growth_history",
                "action": "persist_cycle_result",
                "source": "closed_learning_temporal",
            },
        ]
        if status == "due":
            actions.append({"type": "performance_learning", "action": "sync_platform_analytics"})
        cycles.append(
            ClosedLoopCycle(
                milestone=milestone,
                due_at=due_at,
                status=status,
                objective_status=objective_status,
                recommendations_version=recommendations_version,
                summary=f"Ciclo {milestone}: {status}, objetivo {objective_status}.",
                actions=actions,
                blockers=[str(item) for item in blockers[:3]],
            )
        )

    memory_updates = [
        {
            "mode": "assisted",
            "area": str(_as_dict(item).get("area") or "memory"),
            "title": str(_as_dict(item).get("title") or "Atualizar memória"),
            "detail": str(_as_dict(item).get("detail") or ""),
            "requires_approval": True,
        }
        for item in _as_list(loop.get("memory_updates"))[:5]
    ]
    versioned = _recommendations(
        project_id=project_id,
        closed_loop=loop,
        objective_status=objective_status,
        version=recommendations_version,
    )
    due_count = sum(1 for cycle in cycles if cycle.status == "due")
    blocked_count = sum(1 for cycle in cycles if cycle.status == "blocked")
    if blocked_count:
        status: TemporalPlanStatus = "blocked"
    elif due_count:
        status = "ready"
    else:
        status = "learning"

    scheduler_contract = {
        "uses_existing_scheduler": True,
        "creates_scheduler_engine": False,
        "cycle_offsets": [item[0] for item in DEFAULT_MILESTONES],
        "due_cycles": due_count,
    }
    summary = f"Closed Learning Temporal {status}: {due_count} ciclo(s) vencido(s), {blocked_count} bloqueado(s)."
    return ClosedLoopCyclePolicy(
        project_id=project_id,
        status=status,
        summary=summary,
        cycles=cycles,
        objective_comparison={
            "status": objective_status,
            "score": score,
            "objective_count": len(objective_nodes),
            "blockers": [str(item) for item in blockers[:5]],
        },
        versioned_recommendations=versioned,
        memory_update_proposals=memory_updates,
        scheduler_contract=scheduler_contract,
        guardrails=[
            "Usa Scheduler existente; não recria mecanismo de agendamento.",
            "Memória só recebe propostas assistidas com aprovação.",
            "Prompts não são alterados automaticamente por ciclos temporais.",
        ],
        generated_at=current.isoformat(),
    )
