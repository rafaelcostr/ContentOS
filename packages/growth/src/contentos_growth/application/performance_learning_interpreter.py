"""Growth interpretation of Performance Learning signals — Fase 14."""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import Any

from contentos_growth.domain import GrowthRecommendation
from contentos_growth.platform_registry import get_platform_profile, normalize_platform_id


@dataclass
class PerformanceInterpretation:
    project_id: str
    summary: str = ""
    total_media: int = 0
    high_performers: int = 0
    low_performers: int = 0
    avg_ctr: float | None = None
    avg_retention: float | None = None
    platform_breakdown: list[dict[str, Any]] = field(default_factory=list)
    top_hooks: list[str] = field(default_factory=list)
    top_assets: list[dict[str, Any]] = field(default_factory=list)
    underperformers: list[dict[str, Any]] = field(default_factory=list)
    opportunities: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    recommendations: list[GrowthRecommendation] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "summary": self.summary,
            "total_media": self.total_media,
            "high_performers": self.high_performers,
            "low_performers": self.low_performers,
            "avg_ctr": self.avg_ctr,
            "avg_retention": self.avg_retention,
            "platform_breakdown": list(self.platform_breakdown),
            "top_hooks": list(self.top_hooks),
            "top_assets": list(self.top_assets),
            "underperformers": list(self.underperformers),
            "opportunities": list(self.opportunities),
            "risks": list(self.risks),
            "recommendations": [rec.to_dict() for rec in self.recommendations],
        }


def _platform_label(platform: str) -> str:
    profile = get_platform_profile(platform)
    return profile.label if profile else platform


def interpret_performance_insights(
    project_id: str,
    rows: list[dict[str, Any]],
) -> PerformanceInterpretation:
    if not rows:
        return PerformanceInterpretation(
            project_id=project_id,
            summary="Nenhum insight de performance. Execute sync OAuth e POST /growth/performance/sync.",
            risks=["Sem dados pós-publicação — decisões de conteúdo sem feedback real."],
            recommendations=[
                GrowthRecommendation(
                    id=None,
                    project_id=project_id,
                    channel_id=None,
                    kind="performance",
                    title="Ativar Performance Learning",
                    detail="Sincronize analytics OAuth e processe performance learning para obter CTR e retenção.",
                    priority="high",
                    source="performance_learning",
                )
            ],
        )

    high = [r for r in rows if r.get("performance_tier") == "high"]
    low = [r for r in rows if r.get("performance_tier") == "low"]
    ctrs = [float(r["ctr"]) for r in rows if r.get("ctr") is not None]
    retentions = [float(r["retention_pct"]) for r in rows if r.get("retention_pct") is not None]

    by_platform: dict[str, dict[str, Any]] = {}
    for row in rows:
        platform = normalize_platform_id(str(row.get("platform") or "unknown"))
        bucket = by_platform.setdefault(
            platform,
            {"platform": platform, "label": _platform_label(platform), "count": 0, "high": 0, "total_views": 0},
        )
        bucket["count"] += 1
        if row.get("performance_tier") == "high":
            bucket["high"] += 1
        bucket["total_views"] += int(row.get("views") or 0)

    top_assets = sorted(
        [r for r in rows if r.get("views") is not None],
        key=lambda r: (r.get("ctr") or 0, r.get("views") or 0),
        reverse=True,
    )[:5]
    underperformers = sorted(
        [r for r in low if r.get("views") is not None],
        key=lambda r: r.get("views") or 0,
    )[:3]

    hooks: list[str] = []
    for row in high:
        hook = row.get("hook_text")
        if hook and hook not in hooks:
            hooks.append(str(hook)[:200])
    for row in top_assets:
        for learning in row.get("learnings") or []:
            if "hook" in learning.lower() and learning not in hooks:
                hooks.append(learning[:200])

    opportunities: list[str] = []
    risks: list[str] = []
    recommendations: list[GrowthRecommendation] = []

    for asset in top_assets[:3]:
        title = asset.get("title") or asset.get("topic")
        if not title:
            continue
        platform = _platform_label(str(asset.get("platform") or ""))
        ctr = asset.get("ctr")
        ctr_txt = f"{ctr:.1%}" if ctr is not None else "—"
        opportunities.append(f"Replicar em {platform}: «{str(title)[:70]}» (CTR {ctr_txt})")

    if hooks:
        opportunities.append(f"Hooks vencedores detectados: {hooks[0][:80]}…")

    best_platform = max(by_platform.values(), key=lambda b: b["high"], default=None)
    if best_platform and best_platform["high"] >= 2:
        opportunities.append(
            f"Priorizar {best_platform['label']}: {best_platform['high']} mídias de alto desempenho."
        )

    if low:
        risks.append(f"{len(low)} mídia(s) com performance_tier baixo — revisar hook e formato.")
    negative_retention = [r for r in rows if (r.get("retention_delta") or 0) < -5]
    if negative_retention:
        risks.append(
            f"{len(negative_retention)} vídeo(s) com retenção abaixo do previsto (delta negativo)."
        )
    if ctrs and mean(ctrs) < 0.02:
        risks.append(f"CTR médio baixo ({mean(ctrs):.2%}) — testar novos hooks nos primeiros 3s.")

    for asset in underperformers:
        title = asset.get("title") or asset.get("topic") or "Conteúdo"
        recommendations.append(
            GrowthRecommendation(
                id=None,
                project_id=project_id,
                channel_id=None,
                kind="performance",
                title=f"Revisar: {str(title)[:60]}",
                detail="; ".join((asset.get("learnings") or [])[:2]) or "Performance abaixo da média do canal.",
                priority="medium",
                source="performance_learning",
            )
        )

    for hook in hooks[:2]:
        recommendations.append(
            GrowthRecommendation(
                id=None,
                project_id=project_id,
                channel_id=None,
                kind="hook",
                title="Reutilizar hook de alto desempenho",
                detail=hook,
                priority="high",
                source="performance_learning",
            )
        )

    if high and not recommendations:
        top = high[0]
        learnings = top.get("learnings") or []
        recommendations.append(
            GrowthRecommendation(
                id=None,
                project_id=project_id,
                channel_id=None,
                kind="format",
                title="Escalar formato vencedor",
                detail=learnings[0] if learnings else f"CTR {top.get('ctr', 0):.1%} em {top.get('platform', '')}",
                priority="high",
                source="performance_learning",
            )
        )

    summary = (
        f"{len(rows)} mídias analisadas · {len(high)} alto desempenho · "
        f"{len(low)} baixo desempenho"
    )
    if ctrs:
        summary += f" · CTR médio {mean(ctrs):.2%}"
    if retentions:
        summary += f" · retenção média {mean(retentions):.1f}%"

    return PerformanceInterpretation(
        project_id=project_id,
        summary=summary,
        total_media=len(rows),
        high_performers=len(high),
        low_performers=len(low),
        avg_ctr=round(mean(ctrs), 4) if ctrs else None,
        avg_retention=round(mean(retentions), 2) if retentions else None,
        platform_breakdown=sorted(by_platform.values(), key=lambda b: b["high"], reverse=True),
        top_hooks=hooks[:5],
        top_assets=[
            {
                "title": a.get("title") or a.get("topic"),
                "platform": a.get("platform"),
                "views": a.get("views"),
                "ctr": a.get("ctr"),
                "performance_tier": a.get("performance_tier"),
            }
            for a in top_assets
        ],
        underperformers=[
            {
                "title": a.get("title") or a.get("topic"),
                "platform": a.get("platform"),
                "views": a.get("views"),
                "performance_tier": a.get("performance_tier"),
            }
            for a in underperformers
        ],
        opportunities=opportunities[:6],
        risks=risks[:6],
        recommendations=recommendations[:8],
    )
