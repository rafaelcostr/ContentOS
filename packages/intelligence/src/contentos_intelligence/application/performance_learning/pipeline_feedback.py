"""Normalize pipeline/publication performance feedback for learning loops."""

from __future__ import annotations

from typing import Any

from contentos_shared.payload_utils import coerce_dict

from contentos_intelligence.application.performance_learning.scoring import compute_ctr

METRIC_KEYS = {
    "views": ("views", "view_count", "play_count", "impressions"),
    "likes": ("likes", "like_count"),
    "comments": ("comments", "comment_count"),
    "shares": ("shares", "share_count"),
}


def _int_metric(data: dict[str, Any], names: tuple[str, ...]) -> int:
    for name in names:
        value = data.get(name)
        if value is None:
            continue
        try:
            return max(0, int(float(value)))
        except (TypeError, ValueError):
            continue
    return 0


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _score_from_nested(payload: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        data = coerce_dict(payload.get(key))
        for score_key in ("total_score", "score", "viral_score", "overall_score"):
            score = _float_or_none(data.get(score_key))
            if score is not None:
                return score
    return None


def _platform_publications(payload: dict[str, Any]) -> dict[str, Any]:
    publication = coerce_dict(payload.get("publication"))
    platforms = publication.get("platforms")
    if isinstance(platforms, dict) and platforms:
        return platforms
    platform_pubs = payload.get("platform_publications")
    if isinstance(platform_pubs, dict):
        return platform_pubs
    publisher = coerce_dict(payload.get("publisher"))
    publisher_platforms = publisher.get("platforms")
    if isinstance(publisher_platforms, dict):
        return publisher_platforms
    return {}


def build_pipeline_performance_feedback(payload: dict[str, Any]) -> dict[str, Any]:
    """Build a stable performance block from local pipeline outputs.

    The block is intentionally database-free: it can be used by Learning during
    the same run and by Analytics after publication metrics arrive.
    """

    publications = _platform_publications(payload)
    platform_rows: list[dict[str, Any]] = []
    total_views = 0
    total_likes = 0
    total_comments = 0
    total_shares = 0
    published_count = 0
    failed_count = 0

    for platform, raw in publications.items():
        if not isinstance(raw, dict):
            continue
        metrics = coerce_dict(raw.get("metrics")) or raw
        views = _int_metric(metrics, METRIC_KEYS["views"])
        likes = _int_metric(metrics, METRIC_KEYS["likes"])
        comments = _int_metric(metrics, METRIC_KEYS["comments"])
        shares = _int_metric(metrics, METRIC_KEYS["shares"])
        ctr = compute_ctr(
            {
                "views": views,
                "likes": likes,
                "comments": comments,
                "shares": shares,
                "engagement_rate": metrics.get("engagement_rate"),
            }
        )
        status = str(raw.get("status") or raw.get("mode") or "").lower()
        if status in ("published", "live", "success", "ready", "prepared"):
            published_count += 1
        elif status in ("failed", "error"):
            failed_count += 1

        total_views += views
        total_likes += likes
        total_comments += comments
        total_shares += shares
        platform_rows.append(
            {
                "platform": str(platform),
                "status": status or None,
                "external_media_id": raw.get("external_media_id") or raw.get("video_id") or raw.get("id"),
                "publish_url": raw.get("publish_url") or raw.get("url"),
                "views": views,
                "likes": likes,
                "comments": comments,
                "shares": shares,
                "engagement_rate": ctr,
            }
        )

    best_platform = None
    if platform_rows:
        best_platform = max(platform_rows, key=lambda item: (item["views"], item["likes"])).get("platform")

    signals = {
        "content_score": _score_from_nested(payload, "content_score_report"),
        "viral_score": _score_from_nested(payload, "viral_report"),
        "quality_score": _score_from_nested(payload, "quality_report", "video_quality_report"),
        "video_review_score": _score_from_nested(payload, "video_review_report"),
        "retention_pct": _float_or_none(
            coerce_dict(payload.get("retention_report")).get("completion_pct")
            or coerce_dict(payload.get("retention_report")).get("avg_retention_pct")
            or payload.get("retention_pct")
        ),
    }

    total_engagement = total_likes + total_comments + total_shares
    feedback = {
        "platforms": platform_rows,
        "signals": signals,
        "total_views": total_views,
        "total_engagement": total_engagement,
        "published_count": published_count,
        "failed_count": failed_count,
        "best_platform": best_platform,
        "learning_ready": bool(platform_rows or any(v is not None for v in signals.values())),
    }
    return feedback
