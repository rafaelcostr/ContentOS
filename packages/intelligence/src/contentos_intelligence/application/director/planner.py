"""AI Director — partial re-run planning by score (V5.2.4)."""

from __future__ import annotations

import os
from typing import Any

from contentos_shared.payload_utils import coerce_dict

from contentos_intelligence.application.retention.retry_policy import plan_retention_retry, retention_retry_enabled
from contentos_intelligence.domain.director_decision import DirectorDecision, DirectorWeakSignal

DIMENSION_TARGETS: dict[str, tuple[str, str]] = {
    "hook": ("hook", "hook"),
    "retention": ("retention", "takes"),
    "emotion": ("emotion", "emotion"),
    "cta": ("cta", "script"),
    "seo": ("seo", "seo"),
    "title": ("title", "script"),
    "thumbnail": ("thumbnail", "thumbnail"),
    "technical": ("edit", "editor"),
    "rhythm": ("rhythm", "scene_director"),
}


def ai_director_enabled() -> bool:
    return os.getenv("AI_DIRECTOR_ENABLED", "true").lower() in ("1", "true", "yes")


def _director_min_score() -> float:
    try:
        return max(0.0, min(100.0, float(os.getenv("AI_DIRECTOR_MIN_SCORE", "65"))))
    except ValueError:
        return 65.0


def _dimension_min_score() -> float:
    try:
        return max(0.0, min(100.0, float(os.getenv("AI_DIRECTOR_DIMENSION_MIN", "55"))))
    except ValueError:
        return 55.0


def _collect_signals(payload: dict[str, Any]) -> list[DirectorWeakSignal]:
    signals: list[DirectorWeakSignal] = []

    report = coerce_dict(payload.get("content_score_report"))
    for dim in report.get("dimensions") or []:
        if not isinstance(dim, dict):
            continue
        name = str(dim.get("name") or "").strip()
        if not name:
            continue
        signals.append(
            DirectorWeakSignal(
                name=name,
                score=float(dim.get("score") or 0),
                weight=float(dim.get("weight") or 0.1),
                source="content_score",
            )
        )

    retention = coerce_dict(payload.get("retention_report"))
    if retention:
        signals.append(
            DirectorWeakSignal(
                name="retention",
                score=float(retention.get("overall_score") or payload.get("retention_score") or 0),
                weight=0.15,
                source="retention_report",
            )
        )

    quality_score = payload.get("quality_score")
    if quality_score is not None:
        signals.append(
            DirectorWeakSignal(
                name="technical",
                score=float(quality_score) * 10.0,
                weight=0.12,
                source="quality_score",
            )
        )

    seo_pkg = coerce_dict(payload.get("seo_package"))
    if seo_pkg.get("seo_score") is not None:
        signals.append(
            DirectorWeakSignal(
                name="seo",
                score=float(seo_pkg["seo_score"]),
                weight=0.10,
                source="seo_package",
            )
        )
    elif payload.get("seo_score") is not None:
        signals.append(
            DirectorWeakSignal(
                name="seo",
                score=float(payload["seo_score"]),
                weight=0.10,
                source="seo_score",
            )
        )

    video_score = payload.get("video_score")
    if video_score is not None and not any(s.name == "technical" for s in signals):
        signals.append(
            DirectorWeakSignal(
                name="technical",
                score=float(video_score) * 10.0,
                weight=0.10,
                source="video_score",
            )
        )

    return signals


def _overall_score(payload: dict[str, Any], signals: list[DirectorWeakSignal]) -> float:
    if payload.get("content_score") is not None:
        return float(payload["content_score"])
    report = coerce_dict(payload.get("content_score_report"))
    if report.get("total_score") is not None:
        return float(report["total_score"])
    if not signals:
        return 100.0
    total_weight = sum(s.weight for s in signals) or 1.0
    return sum(s.score * s.weight for s in signals) / total_weight


def plan_director_decision(payload: dict[str, Any] | None) -> DirectorDecision:
    """Decide whether to advance or partially re-run the pipeline from a weak dimension."""
    data = dict(payload or {})
    min_score = _director_min_score()
    dim_min = _dimension_min_score()
    signals = _collect_signals(data)
    overall = _overall_score(data, signals)

    if not signals:
        return DirectorDecision(
            passed=True,
            overall_score=overall,
            min_score=min_score,
            target="",
            retry_from="",
            reason="no score signals available",
            weak_signals=[],
            action="advance",
        )

    weak = [s for s in signals if s.score < dim_min]
    passed = overall >= min_score and not weak

    retention_plan = None
    if retention_retry_enabled():
        retention_plan = plan_retention_retry(coerce_dict(data.get("retention_report"))).to_dict()
        if retention_plan and not retention_plan.get("passed"):
            passed = False

    if passed:
        return DirectorDecision(
            passed=True,
            overall_score=overall,
            min_score=min_score,
            target="",
            retry_from="",
            reason="scores within thresholds",
            weak_signals=sorted(signals, key=lambda s: s.score)[:5],
            action="advance",
        )

    ranked = sorted(weak or signals, key=lambda s: s.score * max(s.weight, 0.05))
    worst = ranked[0]
    target, retry_from = DIMENSION_TARGETS.get(worst.name, ("script", "script"))

    if retention_plan and not retention_plan.get("passed"):
        retry_from = str(retention_plan.get("retry_from") or retry_from)
        target = str(retention_plan.get("target") or target)
        reason = f"retention override — {retention_plan.get('reason', '')}"
    else:
        reason = f"weak {worst.name} score {worst.score:.0f} < {dim_min:.0f}"

    return DirectorDecision(
        passed=False,
        overall_score=overall,
        min_score=min_score,
        target=target,
        retry_from=retry_from,
        reason=reason,
        weak_signals=ranked[:5],
        action="retry",
    )


def resolve_director_retry_from(retry_from: str, available_steps: list[str]) -> str:
    if retry_from in available_steps:
        return retry_from
    for step in ("hook", "script", "takes", "editor", "scene_director", "seo", "scene"):
        if step in available_steps:
            return step
    return available_steps[0] if available_steps else retry_from
