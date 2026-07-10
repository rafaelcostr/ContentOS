"""Post-render retention enrichment — uses quality probe + render diagnostics."""

from __future__ import annotations

from typing import Any

from contentos_shared.payload_utils import coerce_dict


def retention_analysis_mode(payload: dict[str, Any]) -> str:
    """post_render when quality step already ran on the rendered MP4."""
    if payload.get("quality_passed") is not None or payload.get("quality_score") is not None:
        return "post_render"
    if payload.get("render_ref") or payload.get("render_diagnostics"):
        return "post_render_partial"
    return "pre_render"


def enrich_payload_for_post_render(payload: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(payload or {})
    diagnostics = coerce_dict(enriched.get("render_diagnostics"))

    duration = _resolve_render_duration(enriched, diagnostics)
    if duration is not None:
        enriched["duration_seconds"] = duration
        enriched["render_duration_seconds"] = duration

    mode = retention_analysis_mode(enriched)
    enriched["_retention_analysis_mode"] = mode

    quality_passed = enriched.get("quality_passed")
    if quality_passed is False:
        enriched.setdefault("_retention_penalty_reasons", []).append("quality_failed")
    missing_clips = int(diagnostics.get("missing_clip_count") or 0)
    if missing_clips and not enriched.get("quality_passed"):
        enriched.setdefault("_retention_penalty_reasons", []).append(f"missing_clips:{missing_clips}")
    if diagnostics.get("used_silent_audio"):
        enriched.setdefault("_retention_penalty_reasons", []).append("silent_audio")

    return enriched


def _resolve_render_duration(payload: dict[str, Any], diagnostics: dict[str, Any]) -> float | None:
    for raw in (
        payload.get("render_duration_seconds"),
        payload.get("duration_seconds"),
        diagnostics.get("duration_seconds"),
        coerce_dict(payload.get("script")).get("duration_seconds"),
    ):
        if raw is None:
            continue
        try:
            return max(5.0, min(60.0, float(raw)))
        except (TypeError, ValueError):
            continue
    scenes = payload.get("scenes") or []
    if isinstance(scenes, list) and scenes:
        try:
            end = max(float(s.get("end_seconds") or 0) for s in scenes if isinstance(s, dict))
            if end > 0:
                return max(5.0, min(60.0, end))
        except (TypeError, ValueError):
            pass
    return None


def apply_post_render_penalties(baseline: float, payload: dict[str, Any]) -> float:
    score = float(baseline)
    reasons = payload.get("_retention_penalty_reasons") or []
    if "quality_failed" in reasons:
        score -= 12.0
    for reason in reasons:
        if str(reason).startswith("missing_clips:"):
            try:
                count = int(str(reason).split(":", 1)[1])
                score -= min(12.0, count * 2.0)
            except ValueError:
                score -= 2.0
        elif reason == "silent_audio":
            score -= 6.0
    return max(0.0, min(100.0, score))
