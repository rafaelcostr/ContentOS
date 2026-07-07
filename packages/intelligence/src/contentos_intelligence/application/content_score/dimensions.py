"""Dimension extractors for unified content score — Epic 9."""

from __future__ import annotations

from typing import Any

from contentos_intelligence.application.viral import analyzers


def _clamp_100(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def _scale_10_to_100(value: Any, default: float = 50.0) -> float:
    try:
        return _clamp_100(float(value) * 10.0)
    except (TypeError, ValueError):
        return default


def _viral(payload: dict) -> dict:
    viral = payload.get("viral_report")
    return viral if isinstance(viral, dict) else {}


def _ab_winners(payload: dict) -> dict:
    ab = payload.get("ab_test")
    if isinstance(ab, dict):
        winners = ab.get("winners")
        if isinstance(winners, dict):
            return winners
    winners = payload.get("ab_winners")
    return winners if isinstance(winners, dict) else {}


def extract_hook(payload: dict) -> tuple[float, str]:
    viral = _viral(payload)
    score = viral.get("hook_score")
    if score is not None:
        return _clamp_100(score), "viral_report.hook_score"
    return _clamp_100(viral.get("viral_score", 50)), "viral_report.viral_score"


def extract_retention(payload: dict) -> tuple[float, str]:
    retention = payload.get("retention_report")
    if isinstance(retention, dict) and retention.get("overall_score") is not None:
        return _clamp_100(retention["overall_score"]), "retention_report.overall_score"
    score = payload.get("retention_score") or payload.get("retention_prediction")
    if score is not None:
        return _clamp_100(score), "retention_score"
    viral = _viral(payload)
    score = viral.get("retention_prediction")
    if score is not None:
        return _clamp_100(score), "viral_report.retention_prediction"
    emotion = payload.get("emotion") or {}
    if isinstance(emotion, dict) and emotion.get("retention") is not None:
        return _scale_10_to_100(emotion["retention"]), "emotion.retention"
    return 50.0, "neutral"


def extract_emotion(payload: dict) -> tuple[float, str]:
    emotion = payload.get("emotion") or {}
    if not isinstance(emotion, dict):
        return 50.0, "neutral"
    if emotion.get("overall") is not None:
        return _scale_10_to_100(emotion["overall"]), "emotion.overall"
    parts = [emotion.get(k) for k in ("emotion", "curiosity", "impact", "retention") if emotion.get(k) is not None]
    if parts:
        avg = sum(float(p) for p in parts) / len(parts)
        return _scale_10_to_100(avg), "emotion.average"
    return 50.0, "neutral"


def extract_cta(payload: dict) -> tuple[float, str]:
    viral = _viral(payload)
    if viral.get("cta_score") is not None:
        return _clamp_100(viral["cta_score"]), "viral_report.cta_score"
    script = payload.get("script") or {}
    if isinstance(script, dict):
        cta = str(script.get("call_to_action") or script.get("cta") or "")
        if cta:
            return _clamp_100(analyzers.analyze_cta({"script": script})), "script.call_to_action"
    dna = payload.get("dna_context") or payload.get("project_dna") or {}
    if isinstance(dna, dict) and dna.get("cta_style"):
        return 65.0, "project_dna.cta_style"
    return 50.0, "neutral"


def extract_seo(payload: dict) -> tuple[float, str]:
    """SEO from seo_package, multi_content seo_article, or heuristics."""
    seo_pkg = payload.get("seo_package") or {}
    if isinstance(seo_pkg, dict) and seo_pkg.get("title"):
        score = float(seo_pkg.get("seo_score") or 70.0)
        if seo_pkg.get("hashtags"):
            score = min(100.0, score + 5.0)
        return _clamp_100(score), "seo_package.seo_score"
    multi = payload.get("multi_content") or payload.get("multi_content_report") or {}
    if isinstance(multi, dict):
        by_fmt = multi.get("by_format") or {}
        seo = by_fmt.get("seo_article") if isinstance(by_fmt, dict) else None
        if isinstance(seo, dict) and seo.get("content"):
            score = 70.0
            meta = (seo.get("data") or {}).get("meta_description") or ""
            if meta and 50 <= len(str(meta)) <= 160:
                score += 15.0
            keywords = (seo.get("data") or {}).get("keywords") or []
            if keywords:
                score += 10.0
            return _clamp_100(score), "multi_content.seo_article"
    script = payload.get("script") or {}
    title = ""
    if isinstance(script, dict):
        title = str(script.get("title") or "")
    title = title or str(payload.get("topic") or "")
    if not title:
        return 50.0, "pending_v4.2"
    score = 45.0
    if 20 <= len(title) <= 70:
        score += 25.0
    if any(w in title.lower() for w in ("como", "guia", "dicas", "tutorial")):
        score += 15.0
    return _clamp_100(score), "heuristic_seo_preview"


def extract_title(payload: dict) -> tuple[float, str]:
    winners = _ab_winners(payload)
    title_w = winners.get("title")
    if isinstance(title_w, dict) and title_w.get("score") is not None:
        return _clamp_100(title_w["score"]), "ab_test.title_winner"
    script = payload.get("script") or {}
    title = str(script.get("title") or payload.get("topic") or "") if isinstance(script, dict) else ""
    if not title:
        return 50.0, "neutral"
    score = 55.0
    if 10 <= len(title) <= 70:
        score += 15.0
    return _clamp_100(score), "script.title"


def extract_thumbnail(payload: dict) -> tuple[float, str]:
    winners = _ab_winners(payload)
    thumb_w = winners.get("thumbnail")
    if isinstance(thumb_w, dict) and thumb_w.get("score") is not None:
        return _clamp_100(thumb_w["score"]), "ab_test.thumbnail_winner"
    if payload.get("thumbnail_concept"):
        return 60.0, "ab_test.thumbnail_concept"
    return 50.0, "neutral"


def extract_technical(payload: dict) -> tuple[float, str]:
    if payload.get("quality_score") is not None:
        return _scale_10_to_100(payload["quality_score"]), "quality_score"
    quality = payload.get("quality") or {}
    if isinstance(quality, dict) and quality.get("score") is not None:
        return _scale_10_to_100(quality["score"]), "quality.score"
    if payload.get("video_score") is not None:
        return _scale_10_to_100(payload["video_score"]), "video_score"
    video_review = payload.get("video_review") or {}
    if isinstance(video_review, dict) and video_review.get("score") is not None:
        return _scale_10_to_100(video_review["score"]), "video_review.score"
    return 50.0, "unavailable_pre_render"


def extract_rhythm(payload: dict) -> tuple[float, str]:
    viral = _viral(payload)
    if viral.get("rhythm_score") is not None:
        return _clamp_100(viral["rhythm_score"]), "viral_report.rhythm_score"
    return _clamp_100(analyzers.analyze_rhythm(payload)), "payload.scenes"


EXTRACTORS = {
    "hook": extract_hook,
    "retention": extract_retention,
    "emotion": extract_emotion,
    "cta": extract_cta,
    "seo": extract_seo,
    "title": extract_title,
    "thumbnail": extract_thumbnail,
    "technical": extract_technical,
    "rhythm": extract_rhythm,
}

DEFAULT_WEIGHTS: dict[str, float] = {
    "hook": 0.15,
    "retention": 0.15,
    "emotion": 0.10,
    "cta": 0.10,
    "seo": 0.10,
    "title": 0.10,
    "thumbnail": 0.10,
    "technical": 0.10,
    "originality": 0.05,
    "rhythm": 0.05,
}
