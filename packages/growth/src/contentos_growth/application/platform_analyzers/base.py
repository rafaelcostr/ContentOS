"""Shared helpers for platform channel analyzers."""

from __future__ import annotations

import re
from datetime import datetime
from statistics import mean
from typing import Any

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
    "compartilhe",
    "share",
    "bio",
    "dm",
)


def extract_hashtags(*texts: str | None) -> list[str]:
    found: list[str] = []
    for text in texts:
        if not text:
            continue
        for tag in _HASHTAG_RE.findall(text):
            normalized = tag.lower()
            if normalized not in found:
                found.append(normalized)
    return found


def detect_cta_patterns(*texts: str | None) -> list[str]:
    patterns: list[str] = []
    blob = " ".join(t.lower() for t in texts if t)
    for keyword in _CTA_KEYWORDS:
        if keyword in blob and keyword not in patterns:
            patterns.append(keyword)
    return patterns


def parse_published_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def posting_frequency_days(media_items: list[dict[str, Any]]) -> float | None:
    dates: list[datetime] = []
    for item in media_items:
        metrics = item.get("metrics") or {}
        published = parse_published_at(metrics.get("published_at") or item.get("published_at"))
        if published:
            dates.append(published)
    if len(dates) < 2:
        return None
    dates.sort(reverse=True)
    gaps = [(dates[i] - dates[i + 1]).days for i in range(len(dates) - 1)]
    return round(mean(gaps), 1) if gaps else None


def avg_metric(media_items: list[dict[str, Any]], key: str) -> float | None:
    values = []
    for item in media_items:
        metrics = item.get("metrics") or {}
        raw = metrics.get(key)
        if raw is not None:
            values.append(float(raw))
    return round(mean(values), 4) if values else None


def clamp_score(value: float) -> float:
    return max(0.0, min(100.0, round(value, 1)))


def build_recommendations(
    *,
    project_id: str,
    channel_id: str,
    dimensions: dict[str, float],
    hashtags: list[str],
    cta_patterns: list[str],
    posting_gap_days: float | None,
    format_hint: str | None = None,
) -> list[GrowthRecommendation]:
    recs: list[GrowthRecommendation] = []

    def add(kind: str, title: str, detail: str, priority: str) -> None:
        recs.append(
            GrowthRecommendation(
                id=None,
                project_id=project_id,
                channel_id=channel_id,
                kind=kind,
                title=title,
                detail=detail,
                priority=priority,
                source="channel_analyzer",
            )
        )

    if dimensions["branding"] < 70:
        add("branding", "Reforçar branding do canal", "Atualize bio, avatar e identidade visual para reforçar reconhecimento.", "high")
    if dimensions["consistency"] < 65:
        gap = f"{posting_gap_days:.0f} dias" if posting_gap_days else "irregular"
        add("frequency", "Melhorar cadência de publicação", f"Frequência atual ~{gap} entre posts. Defina calendário consistente.", "high")
    if dimensions["format_mix"] < 60 and format_hint:
        add("format", f"Testar {format_hint}", f"Pouco uso de {format_hint}. Teste formatos nativos da plataforma.", "medium")
    if not hashtags:
        add("hashtags", "Adicionar hashtags estratégicas", "Nenhuma hashtag consistente encontrada. Padronize tags por tema.", "medium")
    if not cta_patterns:
        add("cta", "Incluir CTAs claros", "Legendas sem chamadas para ação. Adicione follow, comentário ou link.", "medium")
    if dimensions["engagement"] < 55:
        add("engagement", "Melhorar engajamento", "Engajamento abaixo do esperado. Teste hooks mais fortes nos primeiros segundos.", "high")

    return recs[:6]
