"""Viral sub-analyzers — compose V3 payload signals (Epic 1)."""

from __future__ import annotations

from typing import Any

HOOK_STYLE_BOOST = {"shock": 12, "curiosity": 10, "urgency": 10, "mystery": 8, "controversy": 9}


def _coerce_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    return {}


def _clamp_100(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def _scale_10_to_100(value: Any, default: float = 50.0) -> float:
    try:
        return _clamp_100(float(value) * 10.0)
    except (TypeError, ValueError):
        return default


def analyze_hook(payload: dict[str, Any]) -> float:
    """HookAnalyzer — scores opening hook strength."""
    hook = _coerce_dict(payload.get("selected_hook")) or _coerce_dict(payload.get("hook"))
    text = str(payload.get("hook_text") or hook.get("hook_text") or hook.get("hook") or "").strip()
    style = str(hook.get("style") or payload.get("hook_style") or "").lower()
    score = 45.0
    if text:
        score += 15.0
    if 15 <= len(text) <= 100:
        score += 12.0
    if "?" in text:
        score += 5.0
    score += HOOK_STYLE_BOOST.get(style, 0)
    return _clamp_100(score)


def analyze_emotion(payload: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    """EmotionPredictor — adapter over emotion step output."""
    emotion = _coerce_dict(payload.get("emotion")) or _coerce_dict(payload.get("emotion_scores"))
    if not emotion:
        return 50.0, {}
    overall = _scale_10_to_100(emotion.get("overall"), 50.0)
    details = {
        "emotion": _scale_10_to_100(emotion.get("emotion")),
        "curiosity": _scale_10_to_100(emotion.get("curiosity")),
        "retention": _scale_10_to_100(emotion.get("retention")),
        "impact": _scale_10_to_100(emotion.get("impact")),
        "dominant_emotion": emotion.get("dominant_emotion"),
        "risks": emotion.get("risks") or [],
        "strengths": emotion.get("strengths") or [],
    }
    return overall, details


def analyze_rhythm(payload: dict[str, Any]) -> float:
    """RhythmAnalyzer — scene pacing and director plan."""
    scenes = payload.get("scenes")
    scene_list = scenes if isinstance(scenes, list) else []
    count = len(scene_list)
    score = 50.0
    if 4 <= count <= 8:
        score = 85.0
    elif 2 <= count <= 10:
        score = 70.0
    elif count > 0:
        score = 58.0

    director = _coerce_dict(payload.get("director_plan"))
    if director.get("scenes") or director.get("beats"):
        score = min(100.0, score + 8.0)
    return _clamp_100(score)


def analyze_scenes(payload: dict[str, Any]) -> float:
    """SceneAnalyzer — storyboard + scene coverage."""
    storyboard = _coerce_dict(payload.get("storyboard"))
    scenes = payload.get("scenes")
    scene_list = scenes if isinstance(scenes, list) else []
    score = 55.0
    if storyboard.get("frames") or storyboard.get("scenes"):
        score += 15.0
    if len(scene_list) >= 3:
        score += 12.0
    return _clamp_100(score)


def analyze_trend(payload: dict[str, Any]) -> float:
    """TrendMatcher — adapter over trend_intelligence output."""
    explicit = payload.get("trend_score")
    if explicit is not None:
        try:
            return _clamp_100(float(explicit))
        except (TypeError, ValueError):
            pass
    trend = (
        _coerce_dict(payload.get("trend_context"))
        or _coerce_dict(payload.get("trend_brief"))
        or _coerce_dict(payload.get("trend"))
        or _coerce_dict(payload.get("trend_forecast_report"))
    )
    if not trend:
        return 50.0
    if trend.get("trend_score") is not None:
        try:
            return _clamp_100(float(trend["trend_score"]))
        except (TypeError, ValueError):
            pass
    patterns = trend.get("patterns") or trend.get("recommended_patterns") or []
    hooks = trend.get("hook_ideas") or trend.get("hooks") or trend.get("recommended_hooks") or []
    score = 50.0 + min(25.0, len(patterns) * 4.0) + min(15.0, len(hooks) * 3.0)
    return _clamp_100(score)


def analyze_cta(payload: dict[str, Any]) -> float:
    script = _coerce_dict(payload.get("script"))
    cta = str(
        script.get("call_to_action") or script.get("cta") or payload.get("cta") or ""
    ).strip()
    if not cta:
        return 40.0
    if len(cta) >= 12:
        return 78.0
    return 62.0


def predict_retention(
    hook_score: float,
    emotion_details: dict[str, Any],
    rhythm_score: float,
) -> float:
    """RetentionPredictor — heuristic retention 0–100."""
    em_ret = float(emotion_details.get("retention") or 50.0)
    return _clamp_100(hook_score * 0.35 + em_ret * 0.45 + rhythm_score * 0.20)


def compute_viral_score(
    *,
    hook_score: float,
    emotion_score: float,
    rhythm_score: float,
    scene_score: float,
    trend_score: float,
    cta_score: float,
    retention_prediction: float,
) -> float:
    """ViralityScore — weighted aggregate."""
    return _clamp_100(
        hook_score * 0.18
        + emotion_score * 0.18
        + rhythm_score * 0.14
        + scene_score * 0.10
        + trend_score * 0.10
        + cta_score * 0.10
        + retention_prediction * 0.20
    )


def build_recommendations(
    *,
    hook_score: float,
    emotion_score: float,
    rhythm_score: float,
    scene_score: float,
    trend_score: float,
    cta_score: float,
    retention_prediction: float,
    emotion_details: dict[str, Any],
) -> list[str]:
    recs: list[str] = []
    if hook_score < 65:
        recs.append("Reforce o gancho nos primeiros 3 segundos com pergunta ou afirmação chocante.")
    if emotion_score < 65:
        recs.append("Aumente curiosidade e tensão emocional no desenvolvimento do roteiro.")
    if rhythm_score < 65:
        recs.append("Ajuste o ritmo: alterne cenas a cada 3–5 segundos para retenção.")
    if scene_score < 65:
        recs.append("Enriqueça o storyboard com mais variação visual entre cenas.")
    if trend_score < 60:
        recs.append("Alinhe o tema com padrões de tendência do nicho (Trend Intelligence).")
    if cta_score < 60:
        recs.append("Inclua CTA mais claro e urgente no fechamento.")
    if retention_prediction < 65:
        recs.append("Retenção prevista baixa — encurte introdução e antecipe payoff.")
    for risk in (emotion_details.get("risks") or [])[:2]:
        text = str(risk).strip()
        if text and text not in recs:
            recs.append(f"Risco: {text}")
    return recs[:8]
