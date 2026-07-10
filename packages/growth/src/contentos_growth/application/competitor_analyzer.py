"""Competitor Intelligence — pattern analysis (Growth OS Fase 7)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from statistics import mean
from typing import Any

from contentos_growth.channel_memory_model import extract_patterns_from_media
from contentos_growth.domain import GrowthRecommendation

_HASHTAG_RE = re.compile(r"#\w+", re.UNICODE)
_CTA_KEYWORDS = (
    "inscreva",
    "subscribe",
    "like",
    "comente",
    "comment",
    "link",
    "clique",
    "click",
    "siga",
    "follow",
)


@dataclass(frozen=True)
class CompetitorAnalysisResult:
    competitor_id: str
    project_id: str
    platform: str
    handle: str
    display_name: str
    score: float
    summary: str
    patterns: dict[str, Any]
    recommendations: list[GrowthRecommendation] = field(default_factory=list)
    analyzed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "competitor_id": self.competitor_id,
            "project_id": self.project_id,
            "platform": self.platform,
            "handle": self.handle,
            "display_name": self.display_name,
            "score": self.score,
            "summary": self.summary,
            "patterns": dict(self.patterns),
            "recommendations": [rec.to_dict() for rec in self.recommendations],
            "analyzed_at": self.analyzed_at,
        }


def _extract_hashtags(*texts: str | None) -> list[str]:
    found: list[str] = []
    for text in texts:
        if not text:
            continue
        for tag in _HASHTAG_RE.findall(text):
            normalized = tag.lower()
            if normalized not in found:
                found.append(normalized)
    return found


def _detect_cta_patterns(*texts: str | None) -> list[str]:
    patterns: list[str] = []
    blob = " ".join(t.lower() for t in texts if t)
    for keyword in _CTA_KEYWORDS:
        if keyword in blob and keyword not in patterns:
            patterns.append(keyword)
    return patterns


def _parse_published_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _posting_frequency_days(media_items: list[dict[str, Any]]) -> float | None:
    dates: list[datetime] = []
    for item in media_items:
        metrics = item.get("metrics") or item
        published = _parse_published_at(metrics.get("published_at") or item.get("published_at"))
        if published:
            dates.append(published)
    if len(dates) < 2:
        return None
    dates.sort(reverse=True)
    gaps = [(dates[i] - dates[i + 1]).days for i in range(len(dates) - 1)]
    return round(mean(gaps), 1) if gaps else None


def _avg_metric(media_items: list[dict[str, Any]], key: str) -> float | None:
    values = []
    for item in media_items:
        metrics = item.get("metrics") or item
        raw = metrics.get(key)
        if raw is not None:
            values.append(float(raw))
    return round(mean(values), 4) if values else None


def _clamp_score(value: float) -> float:
    return max(0.0, min(100.0, round(value, 1)))


def _build_recommendations(
    *,
    project_id: str,
    competitor_id: str,
    display_name: str,
    shorts_ratio: float,
    posting_gap_days: float | None,
    avg_engagement: float | None,
    hashtags: list[str],
) -> list[GrowthRecommendation]:
    recs: list[GrowthRecommendation] = []
    if shorts_ratio >= 0.5:
        recs.append(
            GrowthRecommendation(
                id=None,
                project_id=project_id,
                channel_id=None,
                kind="competitor",
                title=f"{display_name} prioriza Shorts",
                detail="O concorrente tem forte presença em Shorts. Avalie aumentar a proporção de vídeos curtos no seu canal.",
                priority="high",
                source="competitor_analyzer",
            )
        )
    if posting_gap_days is not None and posting_gap_days <= 4:
        recs.append(
            GrowthRecommendation(
                id=None,
                project_id=project_id,
                channel_id=None,
                kind="competitor",
                title=f"{display_name} publica com alta frequência",
                detail=f"Intervalo médio de ~{posting_gap_days:.0f} dias entre posts. Considere ajustar sua cadência para competir.",
                priority="medium",
                source="competitor_analyzer",
            )
        )
    if avg_engagement is not None and avg_engagement >= 0.05:
        recs.append(
            GrowthRecommendation(
                id=None,
                project_id=project_id,
                channel_id=None,
                kind="competitor",
                title=f"Engajamento elevado em {display_name}",
                detail="Estude os títulos e hooks dos vídeos com maior engagement_rate na amostra sincronizada.",
                priority="medium",
                source="competitor_analyzer",
            )
        )
    if hashtags:
        recs.append(
            GrowthRecommendation(
                id=None,
                project_id=project_id,
                channel_id=None,
                kind="competitor",
                title="Hashtags recorrentes do concorrente",
                detail=f"Tags observadas: {', '.join(hashtags[:8])}. Teste variações no seu nicho.",
                priority="low",
                source="competitor_analyzer",
            )
        )
    return recs


def analyze_competitor_snapshot(
    *,
    competitor_id: str,
    project_id: str,
    platform: str,
    handle: str,
    display_name: str,
    metrics: dict[str, Any],
) -> CompetitorAnalysisResult:
    if metrics.get("sync_error"):
        raise ValueError(f"Sincronização pendente: {metrics['sync_error']}")

    channel_totals = metrics.get("channel_totals") or {}
    media_items = metrics.get("media_items") or []
    if not channel_totals and not media_items:
        raise ValueError("Nenhum dado sincronizado. Execute a sincronização do concorrente antes da análise.")

    description = str(channel_totals.get("description") or "")
    title = str(channel_totals.get("title") or display_name)
    keywords = str(channel_totals.get("keywords") or "")
    subscriber_count = int(channel_totals.get("subscriber_count") or 0)
    shorts_count = int(channel_totals.get("shorts_count") or 0)
    videos_count = int(channel_totals.get("videos_count") or 0)
    total_media = shorts_count + videos_count

    normalized_media = [
        {
            "external_media_id": item.get("external_media_id"),
            "title": item.get("title"),
            "metrics": item if item.get("engagement_rate") is not None else item.get("metrics", item),
        }
        for item in media_items
    ]

    titles = [
        str((item.get("metrics") or item).get("title") or item.get("title") or "")
        for item in normalized_media
    ]
    hashtags = _extract_hashtags(description, keywords, *titles)
    cta_patterns = _detect_cta_patterns(description, *titles)
    avg_engagement = _avg_metric(normalized_media, "engagement_rate")
    avg_duration = _avg_metric(normalized_media, "duration_seconds")
    posting_gap_days = _posting_frequency_days(normalized_media)
    shorts_ratio = (shorts_count / total_media) if total_media else 0.0
    extracted = extract_patterns_from_media(normalized_media)

    content_score = 35.0
    if total_media >= 3:
        content_score += 20
    if shorts_ratio >= 0.3:
        content_score += 20
    if avg_engagement and avg_engagement >= 0.03:
        content_score += 15
    if subscriber_count >= 10_000:
        content_score += 10
    score = _clamp_score(content_score)

    patterns = {
        "subscriber_count": subscriber_count,
        "view_count": channel_totals.get("view_count"),
        "video_count": channel_totals.get("video_count"),
        "shorts_ratio": round(shorts_ratio, 2),
        "avg_duration_seconds": avg_duration,
        "avg_engagement_rate": avg_engagement,
        "posting_gap_days": posting_gap_days,
        "hashtags": hashtags[:15],
        "cta_patterns": cta_patterns,
        "top_hooks": extracted.get("top_hooks", []),
        "top_themes": extracted.get("top_themes", []),
        "winning_videos": extracted.get("winning_videos", []),
        "best_posting_hours": extracted.get("best_posting_hours", []),
    }

    recommendations = _build_recommendations(
        project_id=project_id,
        competitor_id=competitor_id,
        display_name=title,
        shorts_ratio=shorts_ratio,
        posting_gap_days=posting_gap_days,
        avg_engagement=avg_engagement,
        hashtags=hashtags,
    )

    summary = (
        f"Concorrente {title} (@{handle.lstrip('@')}) — score competitivo {score:.0f}/100, "
        f"{subscriber_count:,} inscritos, {len(normalized_media)} mídias na amostra."
    ).replace(",", ".")

    return CompetitorAnalysisResult(
        competitor_id=competitor_id,
        project_id=project_id,
        platform=platform,
        handle=handle,
        display_name=title,
        score=score,
        summary=summary,
        patterns=patterns,
        recommendations=recommendations,
        analyzed_at=datetime.now(timezone.utc).isoformat(),
    )
