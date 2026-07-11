"""Media strategy planning contracts for Autopilot.

The media strategy engine decides the recommended source mix and constraints for
production. It does not download, search, render or call worker queues.
External acquisition is owned by Media Collector; ContentOS consumes the library.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

MediaSourceKind = Literal[
    "own_library",
    "internal_assets",
    "gameplay",
    "media_collector",
    "ai_image",
    "ai_video",
    "motion_graphics",
    "documentary",
    "infographic",
]


@dataclass(frozen=True)
class MediaSourceMix:
    source: MediaSourceKind
    percentage: int
    reason: str
    license_risk: Literal["low", "medium", "high"] = "medium"
    cost_risk: Literal["low", "medium", "high"] = "medium"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "percentage": self.percentage,
            "reason": self.reason,
            "license_risk": self.license_risk,
            "cost_risk": self.cost_risk,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class MediaStrategyPlan:
    topic: str
    platform: str
    content_type: str
    style: str
    source_mix: list[MediaSourceMix] = field(default_factory=list)
    license_score: int = 70
    cost_score: int = 70
    risk_score: int = 30
    media_collector_hints: list[str] = field(default_factory=list)
    media_collector_policy: dict[str, Any] = field(default_factory=dict)
    asset_search_filters: dict[str, Any] = field(default_factory=dict)
    editor_hints: dict[str, Any] = field(default_factory=dict)
    guardrails: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "platform": self.platform,
            "content_type": self.content_type,
            "style": self.style,
            "source_mix": [item.to_dict() for item in self.source_mix],
            "license_score": self.license_score,
            "cost_score": self.cost_score,
            "risk_score": self.risk_score,
            "media_collector_hints": list(self.media_collector_hints),
            # Backward-compatible aliases for older consumers
            "clip_research_hints": list(self.media_collector_hints),
            "media_collector_policy": dict(self.media_collector_policy),
            "asset_collector_policy": dict(self.media_collector_policy),
            "asset_search_filters": dict(self.asset_search_filters),
            "editor_hints": dict(self.editor_hints),
            "guardrails": list(self.guardrails),
        }


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        return dict(value.to_dict())
    return {}


def _unique(items: list[Any], *, limit: int = 8) -> list[str]:
    out: list[str] = []
    for item in items:
        text = str(item or "").strip()
        if text and text not in out:
            out.append(text)
        if len(out) >= limit:
            break
    return out


def _topic_style(topic: str, platform: str, content_type: str, trend_brief: dict[str, Any]) -> str:
    text = f"{topic} {platform} {content_type}".lower()
    if any(word in text for word in ("gta", "game", "jogo", "gameplay")):
        return "gameplay_documentary"
    if any(word in text for word in ("tutorial", "como fazer", "passo a passo")):
        return "explainer"
    if any(word in text for word in ("noticia", "notícia", "breaking", "lançamento")):
        return "news_documentary"
    if trend_brief.get("pacing_hint") in {"rápido", "rapido", "fast"}:
        return "fast_social"
    return "social_documentary"


def _source_mix_for_style(style: str, assets_available: int) -> list[MediaSourceMix]:
    if assets_available >= 5:
        return [
            MediaSourceMix(
                source="own_library",
                percentage=70,
                reason="Biblioteca própria suficiente para reduzir custo e risco de licença.",
                license_risk="low",
                cost_risk="low",
            ),
            MediaSourceMix(
                source="motion_graphics",
                percentage=30,
                reason="Complementar cenas com reforço visual e retenção.",
                license_risk="low",
                cost_risk="low",
            ),
        ]
    if style == "gameplay_documentary":
        return [
            MediaSourceMix(
                source="gameplay",
                percentage=55,
                reason="Tema pede material contextual de jogo ou captura própria.",
                license_risk="medium",
                cost_risk="low",
            ),
            MediaSourceMix(
                source="own_library",
                percentage=25,
                reason="Reutilizar takes internos quando existirem.",
                license_risk="low",
                cost_risk="low",
            ),
            MediaSourceMix(
                source="motion_graphics",
                percentage=20,
                reason="Cobrir lacunas com mapas, textos e zooms.",
                license_risk="low",
                cost_risk="low",
            ),
        ]
    if style == "explainer":
        return [
            MediaSourceMix(
                source="infographic",
                percentage=45,
                reason="Explicações performam melhor com visual didático.",
                license_risk="low",
                cost_risk="low",
            ),
            MediaSourceMix(
                source="media_collector",
                percentage=35,
                reason="Media Collector deve abastecer B-roll autorizado na biblioteca.",
                license_risk="medium",
                cost_risk="low",
            ),
            MediaSourceMix(
                source="motion_graphics",
                percentage=20,
                reason="Retenção com destaques e progressão visual.",
                license_risk="low",
                cost_risk="low",
            ),
        ]
    return [
        MediaSourceMix(
            source="media_collector",
            percentage=40,
            reason="Media Collector abastece a biblioteca antes da produção.",
            license_risk="medium",
            cost_risk="low",
        ),
        MediaSourceMix(
            source="own_library",
            percentage=35,
            reason="Preferir material já coletado quando possível.",
            license_risk="low",
            cost_risk="low",
        ),
        MediaSourceMix(
            source="motion_graphics",
            percentage=25,
            reason="Adicionar ritmo, zooms e contexto.",
            license_risk="low",
            cost_risk="low",
        ),
    ]


def _risk_scores(source_mix: list[MediaSourceMix]) -> tuple[int, int, int]:
    license_penalty = {"low": 6, "medium": 18, "high": 35}
    cost_penalty = {"low": 5, "medium": 20, "high": 40}
    license_risk = sum(license_penalty[item.license_risk] * item.percentage for item in source_mix) / 100
    cost_risk = sum(cost_penalty[item.cost_risk] * item.percentage for item in source_mix) / 100
    risk_score = min(100, round((license_risk + cost_risk) / 2))
    return max(0, 100 - round(license_risk)), max(0, 100 - round(cost_risk)), risk_score


def build_media_strategy_plan(
    *,
    topic: str,
    platform: str = "youtube",
    content_type: str = "video",
    channel_twin: Mapping[str, Any] | Any | None = None,
    trend_opportunity: Mapping[str, Any] | Any | None = None,
    visual_patterns: Mapping[str, Any] | Any | None = None,
    assets_available: int = 0,
) -> MediaStrategyPlan:
    twin = _as_dict(channel_twin or {})
    opportunity = _as_dict(trend_opportunity or {})
    visual = _as_dict(visual_patterns or {})
    trend_brief = _as_dict(opportunity.get("trend_brief"))
    identity = _as_dict(twin.get("identity"))
    brand_dna = _as_dict(twin.get("brand_dna"))
    content_patterns = _as_dict(brand_dna.get("content_patterns"))
    style = _topic_style(topic, platform, content_type, trend_brief)
    source_mix = _source_mix_for_style(style, assets_available)
    license_score, cost_score, risk_score = _risk_scores(source_mix)
    keywords = _unique(
        [
            topic,
            identity.get("niche"),
            *list(trend_brief.get("keywords") or []),
            *list(content_patterns.get("top_themes") or []),
        ],
        limit=10,
    )
    guardrails = [
        "Usar apenas mídia já na biblioteca (Media Collector / uploads).",
        "Validar licença no Media Collector antes de enviar ao ContentOS.",
        "Preferir biblioteca própria quando houver material suficiente.",
    ]
    if any(item.source in {"ai_image", "ai_video"} for item in source_mix):
        guardrails.append("Geração por IA exige provider configurado e política de custo.")

    policy = {
        "allowed_sources": [item.source for item in source_mix],
        "min_duration_seconds": 30,
        "dedupe": True,
        "license_required": True,
        "ingest_endpoint": "POST /api/v1/assets/takes/upload",
    }

    return MediaStrategyPlan(
        topic=topic,
        platform=platform,
        content_type=content_type,
        style=style,
        source_mix=source_mix,
        license_score=license_score,
        cost_score=cost_score,
        risk_score=risk_score,
        media_collector_hints=keywords,
        media_collector_policy=policy,
        asset_search_filters={
            "query": topic,
            "theme": identity.get("niche") or topic,
            "platform": platform,
            "content_type": content_type,
        },
        editor_hints={
            "pacing": visual.get("pacing") or trend_brief.get("pacing_hint") or "dinâmico",
            "style": style,
            "use_progress_bar": content_type in {"short", "reel", "video"},
            "prefer_zoom_cuts": True,
            "visual_patterns": visual,
        },
        guardrails=guardrails,
    )
