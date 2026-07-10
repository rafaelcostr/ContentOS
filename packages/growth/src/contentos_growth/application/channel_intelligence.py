"""Channel intelligence snapshot for Growth Autopilot.

The snapshot consolidates brand, channel memory, analytics, competitors and
strategy into one read model. It does not mutate state and does not call AI
providers directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from contentos_growth.domain import ChannelProfile, CompetitorProfile, GrowthRecommendation, GrowthStrategy

ConfidenceLevel = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class ChannelIntelligenceSnapshot:
    channel_id: str
    project_id: str
    platform: str
    name: str
    confidence: ConfidenceLevel
    score: int
    summary: str
    niche: str = ""
    audience: str = ""
    brand_identity: dict[str, Any] = field(default_factory=dict)
    visual_identity: dict[str, Any] = field(default_factory=dict)
    content_patterns: dict[str, Any] = field(default_factory=dict)
    historical_videos: dict[str, Any] = field(default_factory=dict)
    posting_intelligence: dict[str, Any] = field(default_factory=dict)
    competitor_intelligence: dict[str, Any] = field(default_factory=dict)
    strategy_context: dict[str, Any] = field(default_factory=dict)
    risks: list[str] = field(default_factory=list)
    opportunities: list[str] = field(default_factory=list)
    next_questions: list[str] = field(default_factory=list)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "project_id": self.project_id,
            "platform": self.platform,
            "name": self.name,
            "confidence": self.confidence,
            "score": self.score,
            "summary": self.summary,
            "niche": self.niche,
            "audience": self.audience,
            "brand_identity": dict(self.brand_identity),
            "visual_identity": dict(self.visual_identity),
            "content_patterns": dict(self.content_patterns),
            "historical_videos": dict(self.historical_videos),
            "posting_intelligence": dict(self.posting_intelligence),
            "competitor_intelligence": dict(self.competitor_intelligence),
            "strategy_context": dict(self.strategy_context),
            "risks": list(self.risks),
            "opportunities": list(self.opportunities),
            "next_questions": list(self.next_questions),
            "generated_at": self.generated_at,
        }


def _first_text(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _unique(items: list[Any], *, limit: int = 12) -> list[str]:
    out: list[str] = []
    for item in items:
        text = str(item or "").strip()
        if text and text not in out:
            out.append(text)
        if len(out) >= limit:
            break
    return out


def _competitor_patterns(competitors: list[CompetitorProfile]) -> dict[str, Any]:
    handles: list[str] = []
    hooks: list[str] = []
    hashtags: list[str] = []
    posting_hours: list[int] = []
    avg_gaps: list[float] = []
    for competitor in competitors:
        handles.append(competitor.display_name or competitor.handle)
        metrics = competitor.metrics or {}
        analysis = metrics.get("analysis") if isinstance(metrics.get("analysis"), dict) else {}
        patterns = analysis.get("patterns") if isinstance(analysis.get("patterns"), dict) else metrics
        hooks.extend(patterns.get("top_hooks") or [])
        hashtags.extend(patterns.get("hashtags") or [])
        posting_hours.extend(int(h) for h in patterns.get("best_posting_hours") or [] if str(h).isdigit())
        gap = patterns.get("posting_gap_days")
        if gap is not None:
            try:
                avg_gaps.append(float(gap))
            except (TypeError, ValueError):
                pass
    return {
        "competitors": _unique(handles, limit=10),
        "top_hooks": _unique(hooks, limit=8),
        "hashtags": _unique(hashtags, limit=12),
        "best_posting_hours": sorted(set(h for h in posting_hours if 0 <= h <= 23))[:8],
        "avg_posting_gap_days": round(sum(avg_gaps) / len(avg_gaps), 1) if avg_gaps else None,
    }


def _performance_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    high = [row for row in rows if row.get("performance_tier") == "high"]
    low = [row for row in rows if row.get("performance_tier") == "low"]
    top_titles = _unique([row.get("title") or row.get("topic") for row in high], limit=6)
    weak_titles = _unique([row.get("title") or row.get("topic") for row in low], limit=4)
    hooks = _unique([row.get("hook_text") for row in high if row.get("hook_text")], limit=6)
    return {
        "total_media": len(rows),
        "high_performers": len(high),
        "low_performers": len(low),
        "winning_titles": top_titles,
        "underperforming_titles": weak_titles,
        "winning_hooks": hooks,
    }


def _confidence_score(
    *,
    channel: ChannelProfile,
    brand: dict[str, Any],
    memory: dict[str, Any],
    performance_rows: list[dict[str, Any]],
    competitors: list[CompetitorProfile],
    strategy: GrowthStrategy | None,
) -> tuple[int, ConfidenceLevel]:
    score = 0
    if channel.has_credentials:
        score += 20
    if channel.score > 0 or channel.profile:
        score += 20
    if brand.get("niche") or brand.get("target_audience") or brand.get("brand_context_preview"):
        score += 15
    if memory.get("top_hooks") or memory.get("winning_videos"):
        score += 15
    if performance_rows:
        score += 10
    if competitors:
        score += 10
    if strategy:
        score += 10
    level: ConfidenceLevel = "high" if score >= 75 else "medium" if score >= 45 else "low"
    return min(score, 100), level


def build_channel_intelligence_snapshot(
    *,
    channel: ChannelProfile,
    brand: dict[str, Any] | None = None,
    channel_memory: dict[str, Any] | None = None,
    performance_rows: list[dict[str, Any]] | None = None,
    competitors: list[CompetitorProfile] | None = None,
    strategy: GrowthStrategy | None = None,
    recommendations: list[GrowthRecommendation] | None = None,
) -> ChannelIntelligenceSnapshot:
    brand_data = dict(brand or {})
    memory = dict(channel_memory or {})
    performance = list(performance_rows or [])
    competitor_rows = list(competitors or [])
    recs = list(recommendations or [])
    profile = channel.profile or {}
    report = channel.report or {}

    niche = _first_text(brand_data.get("niche"), profile.get("niche"), memory.get("top_themes", [""])[0] if memory.get("top_themes") else "")
    audience = _first_text(
        brand_data.get("target_audience"),
        profile.get("audience"),
        (report.get("audience") or {}).get("likely_profile") if isinstance(report.get("audience"), dict) else "",
    )

    competitor_patterns = _competitor_patterns(competitor_rows)
    performance_data = _performance_summary(performance)
    content_patterns = {
        "top_hooks": _unique([*(memory.get("top_hooks") or []), *performance_data["winning_hooks"]], limit=10),
        "top_ctas": _unique(memory.get("top_ctas") or [], limit=8),
        "top_themes": _unique([*(memory.get("top_themes") or []), niche], limit=10),
        "top_hashtags": _unique(memory.get("top_hashtags") or competitor_patterns["hashtags"], limit=16),
    }
    posting_hours = sorted(
        set(
            [
                *[int(h) for h in memory.get("best_posting_hours") or [] if str(h).isdigit()],
                *[int(h) for h in competitor_patterns["best_posting_hours"] if str(h).isdigit()],
                *[int(h) for h in (strategy.cadence.get("posting_hours") if strategy else []) or [] if str(h).isdigit()],
            ]
        )
    )
    posting_intelligence = {
        "best_posting_hours": [h for h in posting_hours if 0 <= h <= 23][:8],
        "posting_gap_days": profile.get("posting_gap_days"),
        "strategy_weekly_posts": (strategy.cadence.get("weekly_posts") if strategy else None),
        "competitor_avg_posting_gap_days": competitor_patterns["avg_posting_gap_days"],
    }

    risks: list[str] = []
    opportunities: list[str] = []
    next_questions: list[str] = []
    if not channel.has_credentials:
        risks.append("Canal sem OAuth: histórico, analytics e publicação real ficam limitados.")
        next_questions.append("Qual perfil real deve ser conectado primeiro?")
    if not niche:
        risks.append("Nicho ainda não definido com confiança.")
        next_questions.append("Qual nicho principal este canal deve dominar?")
    if not audience:
        risks.append("Público-alvo ainda vazio ou inferido de forma fraca.")
        next_questions.append("Quem é o público principal do canal?")
    if not content_patterns["top_hooks"]:
        next_questions.append("Quais hooks já funcionaram melhor nos vídeos antigos?")
    if performance_data["high_performers"]:
        opportunities.append(f"Replicar {performance_data['high_performers']} formato(s) de alto desempenho.")
    if competitor_patterns["competitors"]:
        opportunities.append(f"Usar benchmark de {len(competitor_patterns['competitors'])} concorrente(s).")
    for rec in recs[:3]:
        opportunities.append(rec.title)

    score, confidence = _confidence_score(
        channel=channel,
        brand=brand_data,
        memory=memory,
        performance_rows=performance,
        competitors=competitor_rows,
        strategy=strategy,
    )

    summary_bits = [f"{channel.name} em {channel.platform}", f"confiança {confidence}", f"score {score}/100"]
    if niche:
        summary_bits.append(f"nicho: {niche[:80]}")
    if audience:
        summary_bits.append(f"público: {audience[:80]}")

    return ChannelIntelligenceSnapshot(
        channel_id=channel.channel_id,
        project_id=channel.project_id,
        platform=channel.platform,
        name=channel.name,
        confidence=confidence,
        score=score,
        summary=" · ".join(summary_bits),
        niche=niche,
        audience=audience,
        brand_identity={
            "mission": brand_data.get("mission") or "",
            "values": brand_data.get("values") or [],
            "tone": brand_data.get("tone") or "",
            "vocabulary": brand_data.get("vocabulary") or [],
            "editorial_rules": brand_data.get("editorial_rules") or [],
            "brand_context_preview": brand_data.get("brand_context_preview") or "",
        },
        visual_identity={
            "color_palette": brand_data.get("color_palette") or {},
            "visual_style": brand_data.get("visual_style") or {},
            "style": brand_data.get("style") or {},
            "narrator_persona": brand_data.get("narrator_persona") or "",
        },
        content_patterns=content_patterns,
        historical_videos={
            "winning_videos": memory.get("winning_videos") or [],
            "losing_videos": memory.get("losing_videos") or [],
            **performance_data,
        },
        posting_intelligence=posting_intelligence,
        competitor_intelligence=competitor_patterns,
        strategy_context=strategy.to_dict() if strategy else {},
        risks=_unique(risks, limit=8),
        opportunities=_unique(opportunities, limit=10),
        next_questions=_unique(next_questions, limit=8),
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
