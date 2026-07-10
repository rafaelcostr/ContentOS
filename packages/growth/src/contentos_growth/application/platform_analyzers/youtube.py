"""YouTube channel analyzer."""

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


def analyze_youtube_channel(
    *,
    channel_id: str,
    project_id: str,
    channel_name: str,
    overview: dict[str, Any],
) -> ChannelAnalysisResult:
    totals = overview.get("channel_totals") or {}
    media_items = overview.get("media_items") or []

    description = str(totals.get("description") or "")
    title = str(totals.get("title") or channel_name)
    keywords = str(totals.get("keywords") or "")
    playlists = totals.get("playlists") or []
    subscriber_count = int(totals.get("subscriber_count") or 0)
    shorts_count = int(totals.get("shorts_count") or 0)
    videos_count = int(totals.get("videos_count") or 0)
    total_media = shorts_count + videos_count

    titles = [str((item.get("metrics") or {}).get("title") or item.get("title") or "") for item in media_items]
    hashtags = extract_hashtags(description, keywords, *titles)
    cta_patterns = detect_cta_patterns(description, *titles)
    avg_duration = avg_metric(media_items, "duration_seconds")
    avg_engagement = avg_metric(media_items, "engagement_rate")
    posting_gap_days = posting_frequency_days(media_items)
    shorts_ratio = (shorts_count / total_media) if total_media else 0.0

    branding_score = 40.0
    if totals.get("thumbnail_url"):
        branding_score += 20
    if description.strip():
        branding_score += 15
    if keywords.strip():
        branding_score += 10
    if totals.get("custom_url"):
        branding_score += 10

    consistency_score = 35.0
    if posting_gap_days is not None:
        if posting_gap_days <= 3:
            consistency_score += 35
        elif posting_gap_days <= 7:
            consistency_score += 25
        elif posting_gap_days <= 14:
            consistency_score += 15
    if len(playlists) >= 2:
        consistency_score += 15

    format_score = 30.0
    if total_media >= 3:
        format_score += 20
    if shorts_ratio >= 0.3:
        format_score += 25
    elif shorts_ratio > 0:
        format_score += 10
    if avg_duration and avg_duration <= 90:
        format_score += 15

    engagement_score = 25.0
    if avg_engagement is not None:
        engagement_score += min(avg_engagement * 500, 50)
    if subscriber_count >= 1000:
        engagement_score += 15
    elif subscriber_count >= 100:
        engagement_score += 8

    metadata_score = 30.0
    if len(hashtags) >= 3:
        metadata_score += 25
    elif hashtags:
        metadata_score += 10
    if cta_patterns:
        metadata_score += 20
    if len(description) >= 120:
        metadata_score += 15

    dimensions = {
        "branding": clamp_score(branding_score),
        "consistency": clamp_score(consistency_score),
        "format_mix": clamp_score(format_score),
        "engagement": clamp_score(engagement_score),
        "metadata": clamp_score(metadata_score),
    }
    growth_score = clamp_score(mean(dimensions.values()))

    tone = "energético" if shorts_ratio >= 0.5 else "informativo" if avg_duration and avg_duration > 180 else "misto"
    audience = (
        "público amplo de shorts"
        if shorts_ratio >= 0.5
        else "audiência de vídeos longos"
        if avg_duration and avg_duration > 300
        else "audiência mista"
    )

    report = {
        "channel_name": title,
        "bio": description[:500] if description else None,
        "branding": {
            "thumbnail_url": totals.get("thumbnail_url"),
            "custom_url": totals.get("custom_url"),
            "keywords": keywords or None,
        },
        "playlists": playlists,
        "content_style": {
            "avg_duration_seconds": avg_duration,
            "shorts_ratio": round(shorts_ratio, 2),
            "shorts_count": shorts_count,
            "videos_count": videos_count,
            "tone": tone,
        },
        "frequency": {
            "avg_days_between_posts": posting_gap_days,
            "playlist_count": len(playlists) if isinstance(playlists, list) else 0,
        },
        "hashtags": hashtags,
        "cta_patterns": cta_patterns,
        "audience": {"likely_profile": audience, "subscriber_count": subscriber_count},
        "dimensions": dimensions,
        "data_source": {
            "snapshot_id": overview.get("id"),
            "fetched_at": overview.get("fetched_at"),
            "media_sample_size": len(media_items),
            "platform": "youtube",
        },
    }

    profile = {
        "niche": keywords or None,
        "audience": audience,
        "tone": tone,
        "posting_gap_days": posting_gap_days,
        "shorts_ratio": round(shorts_ratio, 2),
        "subscriber_count": subscriber_count,
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
        format_hint="Shorts" if shorts_ratio < 0.2 else None,
    )

    summary = (
        f"Canal {title} analisado com score {growth_score:.0f}/100. "
        f"{subscriber_count:,} inscritos, {total_media} mídias amostradas, "
        f"tom {tone}, {len(recommendations)} recomendação(ões)."
    ).replace(",", ".")

    return ChannelAnalysisResult(
        channel_id=channel_id,
        project_id=project_id,
        platform="youtube",
        channel_name=channel_name,
        score=growth_score,
        summary=summary,
        report=report,
        profile=profile,
        recommendations=recommendations,
        analyzed_at=datetime.utcnow().isoformat() + "Z",
    )
