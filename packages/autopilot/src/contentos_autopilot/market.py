"""Market intelligence and trend opportunity contracts.

This module ranks opportunities. External trend APIs are optional adapters; the
core stays deterministic and never schedules, publishes or executes work.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Mapping

from contentos_shared.trend_intelligence import build_trend_brief

SignalSource = Literal["strategy", "calendar", "competitor", "memory", "external", "default"]


@dataclass(frozen=True)
class MarketSignal:
    source: SignalSource
    title: str
    detail: str = ""
    score: float = 50.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "title": self.title,
            "detail": self.detail,
            "score": round(float(self.score), 1),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class SaturationSignal:
    topic: str
    level: Literal["low", "medium", "high"]
    score: float
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "level": self.level,
            "score": round(float(self.score), 1),
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class TrendOpportunity:
    topic: str
    title: str
    score: float
    priority: Literal["low", "medium", "high"]
    recommendation: str
    signals: list[MarketSignal] = field(default_factory=list)
    saturation: SaturationSignal | None = None
    trend_brief: dict[str, Any] = field(default_factory=dict)
    objective_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "title": self.title,
            "score": round(float(self.score), 1),
            "priority": self.priority,
            "recommendation": self.recommendation,
            "signals": [signal.to_dict() for signal in self.signals],
            "saturation": self.saturation.to_dict() if self.saturation else None,
            "trend_brief": dict(self.trend_brief),
            "objective_id": self.objective_id,
        }


@dataclass(frozen=True)
class MarketIntelligenceReport:
    project_id: str
    status: str
    summary: str
    opportunities: list[TrendOpportunity] = field(default_factory=list)
    saturation: list[SaturationSignal] = field(default_factory=list)
    signals: list[MarketSignal] = field(default_factory=list)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "status": self.status,
            "summary": self.summary,
            "opportunities": [opportunity.to_dict() for opportunity in self.opportunities],
            "saturation": [signal.to_dict() for signal in self.saturation],
            "signals": [signal.to_dict() for signal in self.signals],
            "generated_at": self.generated_at,
        }


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        return dict(value.to_dict())
    return {}


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _unique(items: list[Any], *, limit: int = 12) -> list[str]:
    out: list[str] = []
    for item in items:
        text = str(item or "").strip()
        if text and text not in out:
            out.append(text)
        if len(out) >= limit:
            break
    return out


def _topic_candidates(
    *,
    strategy: Mapping[str, Any],
    calendar: list[dict[str, Any]],
    competitors: list[Mapping[str, Any]],
    channel_twin: Mapping[str, Any],
    external_signals: list[Mapping[str, Any]],
) -> list[str]:
    competitor_topics: list[str] = []
    for competitor in competitors:
        metrics = _as_dict(competitor.get("metrics"))
        analysis = _as_dict(metrics.get("analysis"))
        patterns = _as_dict(analysis.get("patterns") or metrics.get("patterns"))
        competitor_topics.extend(patterns.get("top_hooks") or [])
        competitor_topics.extend(patterns.get("hashtags") or [])

    brand_dna = _as_dict(channel_twin.get("brand_dna"))
    content_patterns = _as_dict(brand_dna.get("content_patterns"))
    identity = _as_dict(channel_twin.get("identity"))

    return _unique(
        [
            *list(strategy.get("goals") or []),
            strategy.get("positioning"),
            *[item.get("title") or item.get("topic") for item in calendar],
            identity.get("niche"),
            *list(content_patterns.get("top_themes") or []),
            *competitor_topics,
            *[signal.get("title") or signal.get("topic") for signal in external_signals],
        ],
        limit=16,
    )


def _signals_for_topic(
    topic: str,
    *,
    strategy: Mapping[str, Any],
    calendar: list[dict[str, Any]],
    competitors: list[Mapping[str, Any]],
    external_signals: list[Mapping[str, Any]],
    trend_brief: dict[str, Any],
) -> list[MarketSignal]:
    signals: list[MarketSignal] = []
    lowered = topic.lower()
    if any(lowered in str(goal).lower() for goal in strategy.get("goals") or []):
        signals.append(MarketSignal(source="strategy", title="Alinhado a objetivo estratégico", score=72.0))
    if any(lowered in str(item.get("title") or item.get("topic") or "").lower() for item in calendar):
        signals.append(MarketSignal(source="calendar", title="Tema já aparece no calendário", score=55.0))
    competitor_hits = [
        comp.get("display_name") or comp.get("handle")
        for comp in competitors
        if lowered in str(comp.get("metrics") or comp).lower()
    ]
    if competitor_hits:
        signals.append(
            MarketSignal(
                source="competitor",
                title="Concorrentes sinalizam o tema",
                detail=", ".join(_unique(competitor_hits, limit=4)),
                score=68.0,
            )
        )
    for signal in external_signals:
        title = str(signal.get("title") or signal.get("topic") or "")
        if lowered in title.lower():
            signals.append(
                MarketSignal(
                    source="external",
                    title=title,
                    detail=str(signal.get("detail") or ""),
                    score=float(signal.get("score") or 65.0),
                    metadata=dict(signal),
                )
            )
    for source in trend_brief.get("sources") or []:
        if source in {"memory", "analytics", "default"}:
            signals.append(
                MarketSignal(
                    source="memory" if source != "default" else "default",
                    title=f"Trend Intelligence: {source}",
                    score=62.0 if source != "default" else 45.0,
                )
            )
    return signals


def _saturation_for_topic(topic: str, calendar: list[dict[str, Any]], signals: list[MarketSignal]) -> SaturationSignal:
    calendar_count = sum(
        1 for item in calendar if topic.lower() in str(item.get("title") or item.get("topic") or "").lower()
    )
    competitor_count = sum(1 for signal in signals if signal.source == "competitor")
    score = min(100.0, calendar_count * 22.0 + competitor_count * 18.0)
    reasons: list[str] = []
    if calendar_count:
        reasons.append(f"{calendar_count} item(ns) parecido(s) já planejado(s)")
    if competitor_count:
        reasons.append("Concorrência já sinaliza o tema")
    level: Literal["low", "medium", "high"] = "high" if score >= 65 else "medium" if score >= 35 else "low"
    return SaturationSignal(topic=topic, level=level, score=score, reasons=reasons)


def _opportunity_score(trend_brief: dict[str, Any], signals: list[MarketSignal], saturation: SaturationSignal) -> float:
    signal_score = sum(signal.score for signal in signals) / len(signals) if signals else 45.0
    keyword_boost = min(12.0, len(trend_brief.get("keywords") or []) * 2.0)
    pattern_boost = min(16.0, len(trend_brief.get("patterns") or []) * 1.5)
    saturation_penalty = saturation.score * 0.25
    return max(0.0, min(100.0, signal_score + keyword_boost + pattern_boost - saturation_penalty))


def build_market_intelligence_report(
    *,
    project_id: str,
    strategy: Mapping[str, Any] | Any | None = None,
    calendar: list[dict[str, Any]] | None = None,
    competitors: list[Mapping[str, Any]] | None = None,
    channel_twin: Mapping[str, Any] | Any | None = None,
    external_signals: list[Mapping[str, Any]] | None = None,
    max_opportunities: int = 8,
) -> MarketIntelligenceReport:
    strategy_data = _as_dict(strategy or {})
    calendar_items = [item for item in _as_list(calendar or []) if isinstance(item, dict)]
    competitor_rows = [_as_dict(item) for item in _as_list(competitors or [])]
    twin = _as_dict(channel_twin or {})
    ext_signals = [_as_dict(item) for item in _as_list(external_signals or [])]

    topics = _topic_candidates(
        strategy=strategy_data,
        calendar=calendar_items,
        competitors=competitor_rows,
        channel_twin=twin,
        external_signals=ext_signals,
    )
    if not topics:
        topics = ["Mapear tendências do nicho"]

    memory = {
        "niche": _as_dict(twin.get("identity")).get("niche") or "",
        "hook_patterns": _as_dict(_as_dict(twin.get("brand_dna")).get("content_patterns")).get("top_hooks") or [],
    }
    all_signals: list[MarketSignal] = []
    opportunities: list[TrendOpportunity] = []
    saturation_rows: list[SaturationSignal] = []

    for topic in topics:
        trend_brief = build_trend_brief(topic=topic, niche=str(memory.get("niche") or ""), memory=memory)
        signals = _signals_for_topic(
            topic,
            strategy=strategy_data,
            calendar=calendar_items,
            competitors=competitor_rows,
            external_signals=ext_signals,
            trend_brief=trend_brief,
        )
        saturation = _saturation_for_topic(topic, calendar_items, signals)
        score = _opportunity_score(trend_brief, signals, saturation)
        priority: Literal["low", "medium", "high"] = "high" if score >= 75 else "medium" if score >= 55 else "low"
        recommendation = (
            f"Explorar '{topic}' agora com ângulo próprio."
            if priority == "high"
            else f"Validar '{topic}' com pesquisa curta antes de produzir."
            if priority == "medium"
            else f"Monitorar '{topic}' antes de priorizar produção."
        )
        opportunities.append(
            TrendOpportunity(
                topic=topic,
                title=f"Oportunidade: {topic}",
                score=score,
                priority=priority,
                recommendation=recommendation,
                signals=signals,
                saturation=saturation,
                trend_brief=trend_brief,
            )
        )
        all_signals.extend(signals)
        saturation_rows.append(saturation)

    ranked = sorted(opportunities, key=lambda item: item.score, reverse=True)[:max_opportunities]
    status = "ready" if any(item.priority in {"high", "medium"} for item in ranked) else "learning"
    summary = f"{len(ranked)} oportunidade(s) ranqueada(s); melhor score {ranked[0].score:.0f}/100." if ranked else "Sem oportunidades suficientes."
    return MarketIntelligenceReport(
        project_id=project_id,
        status=status,
        summary=summary,
        opportunities=ranked,
        saturation=saturation_rows,
        signals=all_signals,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
