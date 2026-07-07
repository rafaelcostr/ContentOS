"""Performance scoring — CTR, retention delta, tiers (V5.4.2)."""

from __future__ import annotations

import os
from typing import Any

from contentos_intelligence.domain.performance_learning import PerformanceMediaInsight


def min_ctr() -> float:
    try:
        return max(0.0, min(1.0, float(os.getenv("PERFORMANCE_LEARNING_MIN_CTR", "0.04"))))
    except ValueError:
        return 0.04


def min_views() -> int:
    try:
        return max(1, int(os.getenv("PERFORMANCE_LEARNING_MIN_VIEWS", "50")))
    except ValueError:
        return 50


def compute_ctr(metrics: dict[str, Any]) -> float | None:
    if metrics.get("engagement_rate") is not None:
        try:
            return round(float(metrics["engagement_rate"]), 4)
        except (TypeError, ValueError):
            pass
    views = int(metrics.get("views") or 0)
    if views <= 0:
        return None
    interactions = int(metrics.get("likes") or 0) + int(metrics.get("comments") or 0) + int(metrics.get("shares") or 0)
    return round(interactions / views, 4)


def classify_tier(*, ctr: float | None, views: int, retention_pct: float | None) -> str:
    high_ctr = ctr is not None and ctr >= min_ctr()
    high_views = views >= min_views()
    strong_retention = retention_pct is not None and retention_pct >= 55.0
    if high_ctr and high_views and (strong_retention or retention_pct is None):
        return "high"
    if (ctr is not None and ctr >= min_ctr() * 0.5) or views >= min_views() // 2:
        return "medium"
    return "low"


def build_learnings(insight: PerformanceMediaInsight) -> list[str]:
    lines: list[str] = []
    if insight.performance_tier == "high":
        lines.append(f"Alto desempenho em {insight.platform}: CTR {insight.ctr or 0:.1%} com {insight.views} views.")
    if insight.retention_delta is not None:
        if insight.retention_delta >= 5:
            lines.append(f"Retenção real superou previsão em {insight.retention_delta:.1f} p.p.")
        elif insight.retention_delta <= -5:
            lines.append(f"Retenção real ficou {abs(insight.retention_delta):.1f} p.p. abaixo da previsão.")
    if insight.hook_text and insight.performance_tier == "high":
        lines.append(f"Hook vencedor: {insight.hook_text[:160]}")
    if insight.title and not lines:
        lines.append(f"Métricas registradas para «{insight.title[:80]}».")
    return lines


def topic_from_title(title: str | None) -> str:
    if not title:
        return ""
    base = title.split("—")[0].split("#")[0].strip()
    return base[:200]


def match_retention(
    title: str | None,
    retention_by_topic: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    if not title:
        return None
    key = topic_from_title(title).lower()
    if not key:
        return None
    if key in retention_by_topic:
        return retention_by_topic[key]
    for topic, data in retention_by_topic.items():
        if topic and (topic in key or key in topic):
            return data
    return None
