"""Extract learning signals from completed pipeline payload — Epic 7."""

from __future__ import annotations

from typing import Any

from contentos_shared.payload_utils import coerce_dict

from contentos_intelligence.application.performance_learning.pipeline_feedback import (
    build_pipeline_performance_feedback,
)
from contentos_intelligence.domain.learning import LearningSignal


def _first_str(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def extract_hook(payload: dict[str, Any]) -> str:
    script = coerce_dict(payload.get("script"))
    ab = coerce_dict(payload.get("ab_test"))
    winners = ab.get("winners") if isinstance(ab.get("winners"), dict) else {}
    hook_winner = winners.get("hook") if isinstance(winners, dict) else None
    if isinstance(hook_winner, dict):
        return _first_str(hook_winner.get("text"), hook_winner.get("hook"))
    return _first_str(
        payload.get("selected_hook"),
        payload.get("hook_text"),
        payload.get("hook"),
        script.get("hook"),
    )


def extract_cta(payload: dict[str, Any]) -> str:
    script = coerce_dict(payload.get("script"))
    return _first_str(script.get("call_to_action"), payload.get("cta"))


def extract_specialist(payload: dict[str, Any]) -> tuple[str, str, str]:
    selection = coerce_dict(payload.get("specialist_selection"))
    specialist = coerce_dict(selection.get("specialist"))
    specialist_id = _first_str(selection.get("specialist_id"), specialist.get("id"), payload.get("specialist_id"))
    name = _first_str(specialist.get("name"), specialist.get("label"))
    context = _first_str(selection.get("specialist_context"), payload.get("specialist_context"))
    return specialist_id, name, context


def extract_scores(payload: dict[str, Any]) -> tuple[float | None, float | None]:
    score_report = coerce_dict(payload.get("content_score_report"))
    viral = coerce_dict(payload.get("viral_report"))
    content_score = _float_or_none(score_report.get("total_score") or score_report.get("score"))
    viral_score = _float_or_none(viral.get("viral_score"))
    return content_score, viral_score


def extract_prompt_signals(payload: dict[str, Any]) -> list[LearningSignal]:
    signals: list[LearningSignal] = []
    prompts_used = payload.get("prompts_used")
    if isinstance(prompts_used, dict):
        for prompt_id, version in prompts_used.items():
            if version:
                signals.append(
                    LearningSignal(
                        signal_type="prompt",
                        value=str(prompt_id),
                        metadata={"version": str(version)},
                    )
                )
    pack = coerce_dict(payload.get("specialist_prompt_pack"))
    for key, value in pack.items():
        if value:
            signals.append(
                LearningSignal(
                    signal_type="prompt",
                    value=str(key),
                    metadata={"pack": "specialist", "snippet": str(value)[:200]},
                )
            )
    return signals


def extract_signals(payload: dict[str, Any]) -> list[LearningSignal]:
    hook = extract_hook(payload)
    cta = extract_cta(payload)
    specialist_id, specialist_name, specialist_context = extract_specialist(payload)
    content_score, viral_score = extract_scores(payload)

    signals: list[LearningSignal] = []
    if hook:
        signals.append(LearningSignal(signal_type="hook", value=hook, score=viral_score))
    if cta:
        signals.append(LearningSignal(signal_type="cta", value=cta, score=content_score))
    if specialist_id or specialist_name:
        signals.append(
            LearningSignal(
                signal_type="specialist",
                value=specialist_id or specialist_name,
                metadata={"name": specialist_name, "context": specialist_context[:500]},
            )
        )
    if content_score is not None:
        signals.append(LearningSignal(signal_type="content_score", value=str(content_score), score=content_score))
    if viral_score is not None:
        signals.append(LearningSignal(signal_type="viral_score", value=str(viral_score), score=viral_score))
    performance = build_pipeline_performance_feedback(payload)
    if performance.get("learning_ready"):
        metadata = {
            "total_views": performance.get("total_views", 0),
            "total_engagement": performance.get("total_engagement", 0),
            "published_count": performance.get("published_count", 0),
            "failed_count": performance.get("failed_count", 0),
            "best_platform": performance.get("best_platform"),
        }
        signals.append(
            LearningSignal(
                signal_type="performance_feedback",
                value=str(performance.get("best_platform") or "pipeline"),
                score=_float_or_none(coerce_dict(performance.get("signals")).get("content_score")),
                source="performance",
                metadata=metadata,
            )
        )
    signals.extend(extract_prompt_signals(payload))
    return signals
