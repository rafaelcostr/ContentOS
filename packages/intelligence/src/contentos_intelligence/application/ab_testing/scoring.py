"""Score A/B variants using viral report signals."""

from __future__ import annotations

from contentos_intelligence.application.viral import analyzers
from contentos_intelligence.domain.ab_testing import AbVariant


def score_hook_variant(variant: AbVariant, viral_report: dict) -> float:
    payload = {"selected_hook": {"hook_text": variant.value, "style": "curiosity"}, "hook_text": variant.value}
    base = analyzers.analyze_hook(payload)
    viral_boost = float(viral_report.get("hook_score") or 50) * 0.15
    length_bonus = 8.0 if 20 <= len(variant.value) <= 100 else 0.0
    return min(100.0, base * 0.85 + viral_boost + length_bonus)


def score_title_variant(variant: AbVariant, viral_report: dict) -> float:
    text = variant.value.lower()
    score = 50.0
    if 10 <= len(variant.value) <= 70:
        score += 15.0
    if any(w in text for w in ("segredo", "verdade", "chocante", "ninguém")):
        score += 12.0
    score += float(viral_report.get("viral_score") or 50) * 0.1
    return min(100.0, score)


def score_cta_variant(variant: AbVariant, viral_report: dict) -> float:
    payload = {"script": {"call_to_action": variant.value}}
    base = analyzers.analyze_cta(payload)
    if "!" in variant.value:
        base = min(100.0, base + 8.0)
    cta_boost = float(viral_report.get("cta_score") or 50) * 0.2
    return min(100.0, base * 0.8 + cta_boost)


def score_thumbnail_variant(variant: AbVariant, viral_report: dict) -> float:
    text = variant.value.upper()
    score = 55.0
    if "⚠" in text or "!" in variant.value:
        score += 10.0
    if len(variant.value) <= 40:
        score += 8.0
    score += float(viral_report.get("viral_score") or 50) * 0.08
    return min(100.0, score)


def score_opener_variant(variant: AbVariant, viral_report: dict) -> float:
    payload = {"hook_text": variant.value, "selected_hook": {"hook_text": variant.value}}
    hook = analyzers.analyze_hook(payload)
    retention = float(viral_report.get("retention_prediction") or 50) * 0.25
    return min(100.0, hook * 0.6 + retention)


SCORERS = {
    "hook": score_hook_variant,
    "title": score_title_variant,
    "cta": score_cta_variant,
    "thumbnail": score_thumbnail_variant,
    "opener": score_opener_variant,
}


def score_variant(dimension: str, variant: AbVariant, viral_report: dict) -> float:
    scorer = SCORERS.get(dimension)
    if not scorer:
        return 50.0
    return scorer(variant, viral_report)
