"""Trend forecast heuristics — score, growth, recommendation (Epic 10)."""

from __future__ import annotations

from typing import Any

from contentos_shared.payload_utils import coerce_dict


def _clamp_100(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def _insight_score(insight: dict) -> float:
    analysis = coerce_dict(insight.get("analysis"))
    for key in ("score", "overall", "performance_score"):
        try:
            val = analysis.get(key) or insight.get(key)
            if val is not None:
                return float(val)
        except (TypeError, ValueError):
            continue
    return 0.0


def _avg_insight_score(insights: list[dict]) -> float:
    scores = [_insight_score(i) for i in insights if _insight_score(i) > 0]
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def _avg_learning_score(rows: list[dict]) -> float:
    scores: list[float] = []
    for row in rows:
        try:
            cs = row.get("content_score")
            if cs is not None:
                scores.append(float(cs))
        except (TypeError, ValueError):
            continue
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def compute_trend_score(
    *,
    brief: dict[str, Any],
    memory: dict[str, Any],
    insights: list[dict],
    learning_rows: list[dict],
    kb_entry_count: int = 0,
) -> tuple[float, dict[str, Any]]:
    score = 45.0
    signals: dict[str, Any] = {}

    patterns = brief.get("patterns") or []
    keywords = brief.get("keywords") or []
    sources = list(brief.get("sources") or [])
    pattern_boost = min(22.0, len(patterns) * 2.0)
    score += pattern_boost
    signals["pattern_boost"] = pattern_boost

    if keywords:
        kw_boost = min(12.0, len(keywords) * 2.5)
        score += kw_boost
        signals["keyword_boost"] = kw_boost

    analytics_avg = _avg_insight_score(insights)
    if analytics_avg > 0:
        analytics_boost = analytics_avg * 0.28
        score += analytics_boost
        signals["analytics_avg"] = round(analytics_avg, 1)
        signals["analytics_boost"] = round(analytics_boost, 1)

    hook_patterns = memory.get("hook_patterns") or []
    if hook_patterns:
        memory_boost = min(10.0, len(hook_patterns) * 2.0)
        score += memory_boost
        signals["memory_boost"] = memory_boost

    learning_avg = _avg_learning_score(learning_rows)
    if learning_avg > 0:
        learning_boost = learning_avg * 0.12
        score += learning_boost
        signals["learning_avg"] = round(learning_avg, 1)
        signals["learning_boost"] = round(learning_boost, 1)

    if kb_entry_count > 0:
        kb_boost = min(8.0, kb_entry_count * 0.4)
        score += kb_boost
        signals["kb_entry_count"] = kb_entry_count
        signals["kb_boost"] = round(kb_boost, 1)

    if "analytics" in sources and "memory" in sources:
        score += 6.0
        signals["dual_source"] = True
    elif "default" in sources:
        score -= 5.0
        signals["default_fallback"] = True

    pacing = str(brief.get("pacing_hint") or "")
    if pacing in ("rápido", "rapido", "fast"):
        score += 4.0
        signals["pacing_fast"] = True

    return _clamp_100(score), signals


def compute_expected_growth(trend_score: float, insights: list[dict], learning_rows: list[dict]) -> str:
    analytics_avg = _avg_insight_score(insights)
    learning_avg = _avg_learning_score(learning_rows)
    composite = trend_score * 0.55 + analytics_avg * 0.25 + learning_avg * 0.20

    if composite >= 78:
        return "very_high"
    if composite >= 62:
        return "high"
    if composite >= 45:
        return "moderate"
    return "low"


_GROWTH_LABELS = {
    "very_high": "muito alto",
    "high": "alto",
    "moderate": "moderado",
    "low": "baixo",
}


def build_production_recommendation(
    *,
    trend_score: float,
    expected_growth: str,
    brief: dict[str, Any],
    topic: str,
) -> str:
    growth_label = _GROWTH_LABELS.get(expected_growth, expected_growth)
    pacing = brief.get("pacing_hint") or "dinâmico"
    keywords = brief.get("keywords") or []

    if trend_score >= 75 and expected_growth in ("high", "very_high"):
        return (
            f"Produza agora — tendência {growth_label} para «{topic}». "
            f"Ritmo {pacing}; priorize ganchos {', '.join((brief.get('recommended_hooks') or [])[:2]) or 'fortes'}."
        )
    if trend_score >= 55:
        kw = f" Ângulos: {', '.join(keywords[:3])}." if keywords else ""
        return (
            f"Bom momento para produzir — crescimento {growth_label}.{kw} "
            f"Mantenha ritmo {pacing} e valide CTA no roteiro."
        )
    if brief.get("avoid"):
        return (
            f"Cautela — crescimento {growth_label}. "
            f"Evite: {'; '.join((brief.get('avoid') or [])[:2])}. Reforce pesquisa antes de gravar."
        )
    return (
        f"Produção moderada — score {trend_score:.0f}, crescimento {growth_label}. "
        "Amplie pesquisa e teste 2–3 ganchos antes do render."
    )
