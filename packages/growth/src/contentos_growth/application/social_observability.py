"""Observability snapshot for the Social Autopilot lifecycle.

Aggregates plan, governance, approval queue and dispatch data into a single
readiness report for dashboards and manual operations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Mapping

SocialObservabilityStatus = Literal["healthy", "attention", "blocked", "empty"]


@dataclass(frozen=True)
class SocialObservabilityReport:
    project_id: str
    status: SocialObservabilityStatus
    readiness_score: int
    summary: str
    counts: dict[str, int] = field(default_factory=dict)
    manual_actions: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    lifecycle: dict[str, Any] = field(default_factory=dict)
    audit_events: list[dict[str, Any]] = field(default_factory=list)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "status": self.status,
            "readiness_score": self.readiness_score,
            "summary": self.summary,
            "counts": dict(self.counts),
            "manual_actions": list(self.manual_actions),
            "risks": list(self.risks),
            "lifecycle": dict(self.lifecycle),
            "audit_events": [dict(item) for item in self.audit_events],
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


def _count_by_status(rows: list[dict[str, Any]], field: str = "status") -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        status = str(row.get(field) or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out


def build_social_observability_report(
    *,
    project_id: str,
    plan: Mapping[str, Any] | Any | None = None,
    queue: Mapping[str, Any] | Any | None = None,
    dispatch: Mapping[str, Any] | Any | None = None,
) -> SocialObservabilityReport:
    plan_data = _as_dict(plan or {})
    queue_data = _as_dict(queue or {})
    dispatch_data = _as_dict(dispatch or {})

    operations = _as_list(plan_data.get("operations"))
    blocked_operations = _as_list(plan_data.get("blocked_operations"))
    governance = _as_dict(plan_data.get("governance_contract"))
    governance_decisions = [_as_dict(item) for item in _as_list(governance.get("decisions"))]
    queue_items = [_as_dict(item) for item in _as_list(queue_data.get("items"))]
    dispatch_commands = [_as_dict(item) for item in _as_list(dispatch_data.get("commands"))]
    skipped_items = [_as_dict(item) for item in _as_list(dispatch_data.get("skipped_items"))]

    blocked_count = len(blocked_operations) + sum(1 for item in queue_items if item.get("status") == "blocked")
    review_count = sum(1 for item in queue_items if item.get("status") == "needs_review")
    ready_count = sum(1 for item in queue_items if item.get("status") == "ready")
    command_count = len(dispatch_commands)
    skipped_count = len(skipped_items)
    total_operations = len(operations) + len(blocked_operations)

    risks: list[str] = []
    manual_actions: list[str] = []
    for decision in governance_decisions:
        for reason in _as_list(decision.get("reasons")):
            risks.append(str(reason))
        for action in _as_list(decision.get("required_actions")):
            manual_actions.append(str(action))
    for item in queue_items:
        if item.get("status") in {"needs_review", "blocked"}:
            for action in _as_list(item.get("required_actions")):
                manual_actions.append(str(action))
    for item in skipped_items:
        reason = str(item.get("reason") or "")
        if reason:
            manual_actions.append(reason)

    if total_operations == 0 and not queue_items and not dispatch_commands:
        status: SocialObservabilityStatus = "empty"
    elif blocked_count > 0 or any(item.get("status") == "blocked" for item in skipped_items):
        status = "blocked"
    elif review_count > 0 or skipped_count > 0 or governance.get("status") == "review_required":
        status = "attention"
    else:
        status = "healthy"

    score = 100
    score -= min(60, blocked_count * 25)
    score -= min(35, review_count * 12)
    score -= min(20, skipped_count * 8)
    if total_operations and ready_count == 0 and command_count == 0:
        score -= 15
    readiness_score = max(0, min(100, score))

    counts = {
        "operations": total_operations,
        "ready_items": ready_count,
        "review_items": review_count,
        "blocked_items": blocked_count,
        "dispatch_commands": command_count,
        "skipped_items": skipped_count,
    }
    lifecycle = {
        "plan_status": plan_data.get("status", "unknown"),
        "governance_status": governance.get("status", "unknown"),
        "queue_status": queue_data.get("status", "unknown"),
        "dispatch_status": dispatch_data.get("status", "unknown"),
        "queue_by_status": _count_by_status(queue_items),
        "dispatch_by_target": _count_by_status(dispatch_commands, field="target"),
    }
    audit_events = []
    audit_events.extend([_as_dict(item) for item in _as_list(plan_data.get("audit_log"))])
    audit_events.extend([_as_dict(item.get("audit_event")) for item in queue_items if _as_dict(item.get("audit_event"))])
    audit_events.extend([_as_dict(item.get("audit_event")) for item in dispatch_commands if _as_dict(item.get("audit_event"))])

    summary = (
        f"Social observability {status}: score {readiness_score}/100, "
        f"{ready_count} pronto(s), {review_count} revisão(ões), {blocked_count} bloqueado(s)."
    )
    return SocialObservabilityReport(
        project_id=project_id,
        status=status,
        readiness_score=readiness_score,
        summary=summary,
        counts=counts,
        manual_actions=_unique(manual_actions),
        risks=_unique(risks),
        lifecycle=lifecycle,
        audit_events=audit_events,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

