"""Second-by-second retention analysis — V5.2.1."""

from __future__ import annotations

from typing import Any

from contentos_shared.payload_utils import coerce_dict

from contentos_intelligence.application.retention.post_render import (
    apply_post_render_penalties,
    enrich_payload_for_post_render,
    retention_analysis_mode,
)
from contentos_intelligence.application.viral.analyzers import predict_retention
from contentos_intelligence.domain.retention_report import (
    RetentionReport,
    RetentionSecond,
    RetentionSegment,
)

_MOVEMENT_DECAY: dict[str, float] = {
    "static": 0.18,
    "zoom-in": 0.08,
    "zoom-out": 0.10,
    "pan-left": 0.09,
    "pan-right": 0.09,
    "ken-burns": 0.07,
    "speed-ramp-up": 0.05,
    "speed-ramp-down": 0.11,
    "slow-mo": 0.14,
}

_TRANSITION_DROP: dict[str, float] = {
    "cut": 5.0,
    "fade": 2.5,
    "dissolve": 1.5,
}

# Max retention percentage points lost per second (heuristic curve stability).
_MAX_DROP_PER_SECOND = 10.0
_MIN_RETENTION_PCT = 8.0


def _clamp_pct(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def _scale_10(value: Any, default: float = 5.0) -> float:
    try:
        return max(1.0, min(10.0, float(value)))
    except (TypeError, ValueError):
        return default


def _duration_seconds(payload: dict) -> float:
    enriched = enrich_payload_for_post_render(payload)
    resolved = enriched.get("render_duration_seconds") or enriched.get("duration_seconds")
    if resolved is not None:
        try:
            return max(5.0, min(60.0, float(resolved)))
        except (TypeError, ValueError):
            pass
    script = coerce_dict(payload.get("script"))
    for key in ("duration_seconds",):
        raw = payload.get(key) or script.get(key)
        if raw is not None:
            try:
                return max(5.0, min(60.0, float(raw)))
            except (TypeError, ValueError):
                pass
    scenes = payload.get("scenes") or []
    if isinstance(scenes, list) and scenes:
        try:
            end = max(float(s.get("end_seconds") or 0) for s in scenes)
            return max(5.0, min(60.0, end))
        except (TypeError, ValueError):
            pass
    return 45.0


def _scene_at_second(scenes: list[dict], second: int) -> dict:
    for scene in scenes:
        start = float(scene.get("start_seconds") or 0)
        end = float(scene.get("end_seconds") or start + 5)
        if start <= second < end:
            return scene
    return scenes[0] if scenes else {"label": "main"}


def _directive_at_index(directives: list[dict], index: int) -> dict:
    if 0 <= index < len(directives):
        return coerce_dict(directives[index])
    return {}


def _subtitle_density(subtitle_segments: list[dict], second: int) -> float:
    chars = 0
    for seg in subtitle_segments:
        try:
            start = int(float(seg.get("start") or 0))
            end = int(float(seg.get("end") or start + 1))
        except (TypeError, ValueError):
            continue
        if start <= second < end:
            chars += len(str(seg.get("text") or ""))
    if chars >= 40:
        return 0.04
    if chars >= 15:
        return 0.02
    if chars == 0 and second > 2:
        return -0.03
    return 0.0


class RetentionAnalyzer:
    """Heuristic retention curve from timeline metadata (no per-frame vision)."""

    def analyze(self, payload: dict[str, Any]) -> RetentionReport:
        payload = enrich_payload_for_post_render(dict(payload or {}))
        duration = _duration_seconds(payload)
        duration_int = max(1, int(round(duration)))

        scenes = [coerce_dict(s) for s in (payload.get("scenes") or []) if isinstance(s, dict)]
        if not scenes:
            scenes = [{"label": "main", "start_seconds": 0, "end_seconds": duration}]

        director = coerce_dict(payload.get("director_plan"))
        directives = [coerce_dict(d) for d in (director.get("segments") or []) if isinstance(d, dict)]

        emotion = coerce_dict(payload.get("emotion_scores") or payload.get("emotion"))
        hook = coerce_dict(payload.get("selected_hook"))
        viral = coerce_dict(payload.get("viral_report"))
        subtitle_segments = payload.get("segments") or []
        if not isinstance(subtitle_segments, list):
            subtitle_segments = []

        curiosity = _scale_10(emotion.get("curiosity") or hook.get("score"), 6.0)
        retention_emotion = _scale_10(emotion.get("retention"), 6.0)
        hook_score = float(viral.get("hook_score") or curiosity * 10.0)
        rhythm_score = float(viral.get("rhythm_score") or retention_emotion * 10.0)
        baseline = predict_retention(hook_score, emotion, rhythm_score)

        hook_floor = _clamp_pct(55 + curiosity * 4.5)
        base_decay = max(0.08, min(0.35, 0.28 - baseline / 500.0))

        timeline: list[RetentionSecond] = []
        current = 100.0

        for second in range(duration_int):
            scene = _scene_at_second(scenes, second)
            scene_index = int(scene.get("scene_index", 0))
            try:
                if scene_index == 0 and scene in scenes:
                    scene_index = scenes.index(scene)
            except ValueError:
                pass
            directive = _directive_at_index(directives, scene_index)
            movement = str(directive.get("movement") or "ken-burns").lower()
            transition = str(directive.get("transition") or "fade").lower()

            decay = base_decay + _MOVEMENT_DECAY.get(movement, 0.10)
            if second < 3:
                decay *= 0.35
                boost = (curiosity - 5.0) * 0.8
            elif second < 8:
                decay *= 0.75
                boost = (retention_emotion - 5.0) * 0.4
            else:
                boost = -0.5

            boost += _subtitle_density(subtitle_segments, second) * 100

            start = float(scene.get("start_seconds") or 0)
            if second > 0 and abs(second - int(start)) < 0.5 and second > 2:
                decay += _TRANSITION_DROP.get(transition, 2.5) / 100.0

            playback = float(directive.get("playback_speed") or 1.0)
            if playback > 1.15:
                decay += 0.02
            elif playback < 0.85:
                decay -= 0.01

            net_change = -decay * 100 + boost
            net_change = max(net_change, -_MAX_DROP_PER_SECOND)
            current = current + net_change
            if second <= 3:
                current = max(current, hook_floor - second * 3.5)
            current = max(_MIN_RETENTION_PCT, _clamp_pct(current))

            timeline.append(
                RetentionSecond(
                    second=second,
                    retention_pct=current,
                    scene_label=str(scene.get("label") or f"scene_{scene_index}"),
                    factors={
                        "decay": round(decay, 4),
                        "boost": round(boost, 3),
                        "movement": _MOVEMENT_DECAY.get(movement, 0.10),
                    },
                )
            )

        drop_seconds: list[int] = []
        for i in range(len(timeline) - 1):
            drop = timeline[i].retention_pct - timeline[i + 1].retention_pct
            if drop >= 4.0:
                drop_seconds.append(i + 1)

        weak_segments: list[RetentionSegment] = []
        for i, scene in enumerate(scenes):
            start = int(float(scene.get("start_seconds") or 0))
            end = int(float(scene.get("end_seconds") or start + 5))
            slice_pts = [t.retention_pct for t in timeline if start <= t.second < end]
            if not slice_pts:
                continue
            avg = sum(slice_pts) / len(slice_pts)
            min_pct = min(slice_pts)
            directive = _directive_at_index(directives, i)
            movement = str(directive.get("movement") or "ken-burns")
            reason = ""
            if avg < 55:
                reason = f"retenção baixa ({movement})"
            elif movement == "static":
                reason = "movimento estático prolongado"
            if avg < 60 or min_pct < 45:
                weak_segments.append(
                    RetentionSegment(
                        label=str(scene.get("label") or f"scene_{i}"),
                        start_second=float(start),
                        end_second=float(end),
                        avg_retention_pct=avg,
                        min_retention_pct=min_pct,
                        reason=reason or "queda de atenção",
                    )
                )

        hook_retention = timeline[min(3, len(timeline) - 1)].retention_pct if timeline else 0.0
        completion = timeline[-1].retention_pct if timeline else 0.0
        avg_retention = sum(t.retention_pct for t in timeline) / len(timeline) if timeline else 0.0
        overall = _clamp_pct(avg_retention * 0.55 + hook_retention * 0.25 + completion * 0.20)
        overall = apply_post_render_penalties(overall, payload)

        recommendations = self._build_recommendations(
            hook_retention=hook_retention,
            completion=completion,
            drop_seconds=drop_seconds,
            weak_segments=weak_segments,
            baseline=baseline,
        )

        if payload.get("_retention_penalty_reasons"):
            for reason in payload["_retention_penalty_reasons"]:
                if reason == "quality_failed":
                    recommendations.append("Retenção penalizada — corrigir falhas técnicas do render (quality)")
                elif str(reason).startswith("missing_clips:"):
                    recommendations.append("Cenas sem clip real reduzem retenção prevista pós-render")
                elif reason == "silent_audio":
                    recommendations.append("Narração ausente/silenciosa no render final")

        return RetentionReport(
            overall_score=overall,
            avg_retention_pct=avg_retention,
            hook_retention_pct=hook_retention,
            completion_pct=completion,
            duration_seconds=duration,
            drop_seconds=drop_seconds[:12],
            weak_segments=weak_segments[:8],
            timeline=timeline,
            recommendations=recommendations,
            analysis_mode=retention_analysis_mode(payload),
            quality_score_at_analysis=payload.get("quality_score"),
            render_duration_seconds=payload.get("render_duration_seconds") or duration,
        )

    def _build_recommendations(
        self,
        *,
        hook_retention: float,
        completion: float,
        drop_seconds: list[int],
        weak_segments: list[RetentionSegment],
        baseline: float,
    ) -> list[str]:
        tips: list[str] = []
        if hook_retention < 75:
            tips.append("Reforçar hook nos primeiros 3 segundos (pergunta ou número)")
        if drop_seconds and drop_seconds[0] <= 5:
            tips.append(f"Queda precoce no segundo {drop_seconds[0]} — revisar abertura ou take")
        if weak_segments:
            labels = ", ".join(s.label for s in weak_segments[:3])
            tips.append(f"Segmentos fracos: {labels} — variar movimento ou encurtar")
        if completion < 40:
            tips.append("Retenção final baixa — CTA mais cedo ou vídeo mais curto")
        if baseline < 60:
            tips.append("Score global de retenção abaixo do ideal — revisar ritmo e emoção")
        if not tips:
            tips.append("Curva de retenção saudável para publicação")
        return tips
