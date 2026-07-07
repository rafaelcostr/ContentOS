"""Retention-driven retry planning — V5.2.2 (hook, take, CTA)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from contentos_shared.payload_utils import coerce_dict

HOOK_LABELS = frozenset({"hook", "intro", "opening", "abertura", "gancho"})
CTA_LABELS = frozenset({"cta", "outro", "close", "fechamento", "ending", "final"})
BODY_LABELS = frozenset({"body", "main", "meio", "middle", "core"})

RETRY_TARGETS = frozenset({"hook", "take", "cta"})

TARGET_TO_STEP = {
    "hook": "hook",
    "take": "takes",
    "cta": "script",
}


def _retention_min_score() -> float:
    try:
        return max(0.0, min(100.0, float(os.getenv("RETENTION_MIN_SCORE", "65"))))
    except ValueError:
        return 65.0


def _retention_min_hook_pct() -> float:
    try:
        return max(0.0, min(100.0, float(os.getenv("RETENTION_MIN_HOOK_PCT", "70"))))
    except ValueError:
        return 70.0


def _retention_min_completion_pct() -> float:
    try:
        return max(0.0, min(100.0, float(os.getenv("RETENTION_MIN_COMPLETION_PCT", "40"))))
    except ValueError:
        return 40.0


def retention_retry_enabled() -> bool:
    return os.getenv("RETENTION_RETRY_ENABLED", "true").lower() in ("1", "true", "yes")


def _label_matches(label: str, keywords: frozenset[str]) -> bool:
    text = label.lower().strip()
    return any(word in text for word in keywords)


@dataclass
class RetentionRetryPlan:
    passed: bool
    target: str
    retry_from: str
    reason: str
    retention_score: float
    hook_retention_pct: float
    completion_pct: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "target": self.target,
            "retry_from": self.retry_from,
            "reason": self.reason,
            "retention_score": round(self.retention_score, 2),
            "hook_retention_pct": round(self.hook_retention_pct, 2),
            "completion_pct": round(self.completion_pct, 2),
        }


def plan_retention_retry(
    retention_report: dict[str, Any] | None,
    *,
    min_score: float | None = None,
    min_hook_pct: float | None = None,
    min_completion_pct: float | None = None,
) -> RetentionRetryPlan:
    """Map retention analysis to a targeted pipeline retry (hook / takes / script)."""
    report = coerce_dict(retention_report)
    score = float(report.get("overall_score") or 0)
    hook_pct = float(report.get("hook_retention_pct") or 0)
    completion = float(report.get("completion_pct") or 0)
    weak = report.get("weak_segments") or []
    drops = report.get("drop_seconds") or []

    min_score_v = min_score if min_score is not None else _retention_min_score()
    min_hook_v = min_hook_pct if min_hook_pct is not None else _retention_min_hook_pct()
    min_completion_v = min_completion_pct if min_completion_pct is not None else _retention_min_completion_pct()

    if not report:
        return RetentionRetryPlan(
            passed=True,
            target="",
            retry_from="",
            reason="no retention report",
            retention_score=score,
            hook_retention_pct=hook_pct,
            completion_pct=completion,
        )

    passed = score >= min_score_v and hook_pct >= min_hook_v and completion >= min_completion_v
    if passed:
        return RetentionRetryPlan(
            passed=True,
            target="",
            retry_from="",
            reason="retention within thresholds",
            retention_score=score,
            hook_retention_pct=hook_pct,
            completion_pct=completion,
        )

    target = "cta"
    retry_from = TARGET_TO_STEP["cta"]
    reason = f"overall score {score:.0f} below {min_score_v:.0f}"

    if hook_pct < min_hook_v or (drops and int(drops[0]) <= 5):
        target = "hook"
        retry_from = TARGET_TO_STEP["hook"]
        reason = f"hook retention {hook_pct:.0f}% below {min_hook_v:.0f}"
    elif completion < min_completion_v or any(
        _label_matches(str(seg.get("label") or ""), CTA_LABELS) for seg in weak if isinstance(seg, dict)
    ):
        target = "cta"
        retry_from = TARGET_TO_STEP["cta"]
        reason = f"completion {completion:.0f}% below {min_completion_v:.0f} or weak CTA"
    else:
        for seg in weak:
            if not isinstance(seg, dict):
                continue
            label = str(seg.get("label") or "")
            if _label_matches(label, BODY_LABELS) or (
                label and not _label_matches(label, HOOK_LABELS | CTA_LABELS)
            ):
                target = "take"
                retry_from = TARGET_TO_STEP["take"]
                reason = f"weak segment '{label}' — retry takes"
                break

    return RetentionRetryPlan(
        passed=False,
        target=target,
        retry_from=retry_from,
        reason=reason,
        retention_score=score,
        hook_retention_pct=hook_pct,
        completion_pct=completion,
    )


def resolve_retry_from_steps(retry_from: str, available_steps: list[str]) -> str:
    if retry_from in available_steps:
        return retry_from
    fallbacks = ("hook", "script", "takes", "scene", "research")
    for step in fallbacks:
        if step in available_steps:
            return step
    return available_steps[0] if available_steps else retry_from
