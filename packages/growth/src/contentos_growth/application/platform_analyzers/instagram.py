"""Instagram channel analyzer."""

from __future__ import annotations

from datetime import datetime
from statistics import mean
from typing import Any

from contentos_growth.application.channel_analysis_types import ChannelAnalysisResult
from contentos_growth.application.platform_analyzers.base import (
    avg_metric,
    build_recommendations,
    clamp_score,
    detect_cta_patterns,
    extract_hashtags,
    posting_frequency_days,
)


def analyze_instagram_channel(
    *,
    channel_id: str,
    project_id: str,
    channel_name: str,
    overview: dict[str, Any],
) -> ChannelAnalysisResult:
    totals = overview.get("channel_totals") or {}
    media_items = overview.get("media_items") or []

    username = str(totals.get("username") or channel_name)
    followers = int(totals.get("followers_count") or 0)
    media_count = int(totals.get("media_count") or len(media_items))

    captions = [str((item.get("metrics") or {}).get("title") or item.get("title") or "") for item in media_items]
    hashtags = extract_hashtags(*captions)
    cta_patterns = detect_cta_patterns(*captions)
    avg_engagement = avg_metric(media_items, "engagement_rate")
    avg_views = avg_metric(media_items, "views")
    posting_gap_days = posting_frequency_days(media_items)

    branding_score = 45.0
    if username:
        branding_score += 20
    if followers >= 500:
        branding_score += 15
    if media_count >= 5:
        branding_score += 10

    consistency_score = 35.0
    if posting_gap_days is not None:
        if posting_gap_days <= 2:
            consistency_score += 35
        elif posting_gap_days <= 5:
            consistency_score += 25
        elif posting_gap_days <= 10:
            consistency_score += 15
    if media_count >= 10:
        consistency_score += 10

    format_score = 40.0
    if media_count >= 3:
        format_score += 25
    if avg_views and avg_views >= 500:
        format_score += 20

    engagement_score = 30.0
    if avg_engagement is not None:
        engagement_score += min(avg_engagement * 600, 45)
    if followers >= 1000:
        engagement_score += 15

    metadata_score = 30.0
    if len(hashtags) >= 5:
        metadata_score += 25
    elif hashtags:
        metadata_score += 12
    if cta_patterns:
        metadata_score += 20
    if any(len(caption) >= 80 for caption in captions):
        metadata_score += 10

    dimensions = {
        "branding": clamp_score(branding_score),
        "consistency": clamp_score(consistency_score),
        "format_mix": clamp_score(format_score),
        "engagement": clamp_score(engagement_score),
        "metadata": clamp_score(metadata_score),
    }
    growth_score = clamp_score(mean(dimensions.values()))
    tone = "visual" if avg_views and avg_views >= 1000 else "comunitário"

    report = {
        "channel_name": username,
        "bio": None,
        "content_style": {
            "avg_impressions": avg_views,
            "media_count": media_count,
            "tone": tone,
        },
        "frequency": {"avg_days_between_posts": posting_gap_days},
        "hashtags": hashtags,
        "cta_patterns": cta_patterns,
        "audience": {"likely_profile": "seguidores Instagram", "followers_count": followers},
        "dimensions": dimensions,
        "data_source": {
            "snapshot_id": overview.get("id"),
            "fetched_at": overview.get("fetched_at"),
            "media_sample_size": len(media_items),
            "platform": "instagram",
        },
    }

    profile = {
        "audience": "seguidores Instagram",
        "tone": tone,
        "posting_gap_days": posting_gap_days,
        "followers_count": followers,
        "hashtags": hashtags[:10],
        "cta_patterns": cta_patterns,
    }

    recommendations = build_recommendations(
        project_id=project_id,
        channel_id=channel_id,
        dimensions=dimensions,
        hashtags=hashtags,
        cta_patterns=cta_patterns,
        posting_gap_days=posting_gap_days,
        format_hint="Reels",
    )

    summary = (
        f"Instagram @{username} analisado com score {growth_score:.0f}/100. "
        f"{followers:,} seguidores, {len(media_items)} posts amostrados, "
        f"{len(recommendations)} recomendação(ões)."
    ).replace(",", ".")

    return ChannelAnalysisResult(
        channel_id=channel_id,
        project_id=project_id,
        platform="instagram",
        channel_name=channel_name,
        score=growth_score,
        summary=summary,
        report=report,
        profile=profile,
        recommendations=recommendations,
        analyzed_at=datetime.utcnow().isoformat() + "Z",
    )
