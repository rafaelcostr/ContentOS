"""Creative direction brief contracts for Autopilot.

The creative brief prepares production context for existing agents. It does not
write scripts, generate voice, create thumbnails, edit video or call workers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping


@dataclass(frozen=True)
class SceneBrief:
    intent: str
    visual_style: str
    movement: str
    transition: str
    pacing: str
    b_roll_hint: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "visual_style": self.visual_style,
            "movement": self.movement,
            "transition": self.transition,
            "pacing": self.pacing,
            "b_roll_hint": self.b_roll_hint,
        }


@dataclass(frozen=True)
class CreativeDirectionBrief:
    topic: str
    objective: str
    platform: str
    content_type: str
    creative_angle: str
    tone: str
    pacing: str
    retention_strategy: list[str] = field(default_factory=list)
    scene_brief: SceneBrief | None = None
    thumbnail_brief: dict[str, Any] = field(default_factory=dict)
    music_brief: dict[str, Any] = field(default_factory=dict)
    voice_brief: dict[str, Any] = field(default_factory=dict)
    transition_brief: dict[str, Any] = field(default_factory=dict)
    editor_brief: dict[str, Any] = field(default_factory=dict)
    guardrails: list[str] = field(default_factory=list)
    inputs: dict[str, Any] = field(default_factory=dict)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "objective": self.objective,
            "platform": self.platform,
            "content_type": self.content_type,
            "creative_angle": self.creative_angle,
            "tone": self.tone,
            "pacing": self.pacing,
            "retention_strategy": list(self.retention_strategy),
            "scene_brief": self.scene_brief.to_dict() if self.scene_brief else None,
            "thumbnail_brief": dict(self.thumbnail_brief),
            "music_brief": dict(self.music_brief),
            "voice_brief": dict(self.voice_brief),
            "transition_brief": dict(self.transition_brief),
            "editor_brief": dict(self.editor_brief),
            "guardrails": list(self.guardrails),
            "inputs": dict(self.inputs),
            "generated_at": self.generated_at,
        }


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        return dict(value.to_dict())
    return {}


def _first_text(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _unique(items: list[Any], *, limit: int = 8) -> list[str]:
    out: list[str] = []
    for item in items:
        text = str(item or "").strip()
        if text and text not in out:
            out.append(text)
        if len(out) >= limit:
            break
    return out


def _creative_angle(topic: str, objective: str, market: dict[str, Any], trend: dict[str, Any]) -> str:
    text = f"{topic} {objective}".lower()
    if "segredo" in text or "escondido" in text or "ninguém" in text:
        return "mystery_reveal"
    if "luxo" in text or "premium" in text:
        return "aspirational_detail"
    if "tutorial" in text or "como" in text:
        return "practical_explainer"
    if (market.get("priority") or trend.get("priority")) == "high":
        return "timely_opportunity"
    return "curiosity_story"


def build_creative_direction_brief(
    *,
    topic: str,
    objective: str = "",
    platform: str = "youtube",
    content_type: str = "video",
    brand_dna: Mapping[str, Any] | Any | None = None,
    audience: Mapping[str, Any] | Any | None = None,
    media_strategy: Mapping[str, Any] | Any | None = None,
    visual_patterns: Mapping[str, Any] | Any | None = None,
    market_opportunity: Mapping[str, Any] | Any | None = None,
) -> CreativeDirectionBrief:
    brand = _as_dict(brand_dna or {})
    audience_data = _as_dict(audience or {})
    media = _as_dict(media_strategy or {})
    visual = _as_dict(visual_patterns or media.get("editor_hints", {}).get("visual_patterns") or {})
    market = _as_dict(market_opportunity or {})
    trend = _as_dict(market.get("trend_brief"))
    editor_hints = _as_dict(media.get("editor_hints"))
    source_mix = list(media.get("source_mix") or [])

    pacing = _first_text(visual.get("pacing"), editor_hints.get("pacing"), trend.get("pacing_hint"), "dinâmico")
    tone = _first_text(
        _as_dict(brand.get("brand_identity")).get("tone"),
        brand.get("tone"),
        audience_data.get("tone"),
        "direto e curioso",
    )
    angle = _creative_angle(topic, objective, market, trend)
    movements = list(visual.get("movements") or editor_hints.get("preferred_movements") or [])
    transitions = list(visual.get("transitions") or editor_hints.get("preferred_transitions") or ["cut", "fade"])
    colors = list(visual.get("colors") or editor_hints.get("color_palette") or [])
    source_names = [str(item.get("source") or "") for item in source_mix if isinstance(item, dict)]
    retention_strategy = _unique(
        [
            "Abrir com promessa visual clara nos primeiros 3 segundos.",
            "Alternar informação e imagem a cada bloco curto.",
            "Evitar legendas cobrindo a tela inteira.",
            "Fechar a ideia com conclusão, não com assunto novo.",
            *list(trend.get("patterns") or [])[:2],
        ],
        limit=8,
    )

    scene = SceneBrief(
        intent=f"Transformar '{topic}' em sequência visual clara e retentiva.",
        visual_style=str(media.get("style") or angle),
        movement=str((movements or ["ken-burns"])[0]),
        transition=str((transitions or ["fade"])[0]),
        pacing=pacing,
        b_roll_hint=", ".join(_unique([topic, *list(media.get("media_collector_hints") or media.get("clip_research_hints") or [])], limit=5)),
    )

    return CreativeDirectionBrief(
        topic=topic,
        objective=objective or topic,
        platform=platform,
        content_type=content_type,
        creative_angle=angle,
        tone=tone,
        pacing=pacing,
        retention_strategy=retention_strategy,
        scene_brief=scene,
        thumbnail_brief={
            "headline_style": "curto, forte e legível",
            "visual_hint": ", ".join(colors[:4]) or angle,
            "overlay_text_max_chars": 25,
            "avoid": ["texto pequeno", "poluição visual"],
        },
        music_brief={
            "mood": "tensão leve" if angle == "mystery_reveal" else "energia moderna",
            "duck_under_voice": True,
        },
        voice_brief={
            "tone": tone,
            "pace": pacing,
            "emotion": "curiosidade" if angle in {"mystery_reveal", "curiosity_story"} else "confiança",
        },
        transition_brief={
            "preferred": transitions[:4] or ["cut", "fade"],
            "movement": movements[:4] or ["ken-burns"],
        },
        editor_brief={
            "style": media.get("style") or angle,
            "source_mix": source_names,
            "pacing": pacing,
            "use_progress_bar": bool(editor_hints.get("use_progress_bar", True)),
            "subtitle_style": visual.get("subtitle_style") or {"avoid_full_screen_blocks": True},
        },
        guardrails=[
            "Agentes existentes executam produção; este brief é apenas contexto.",
            "Manter final conclusivo e compreensível.",
            "Respeitar licenças e fontes definidas no media_strategy.",
        ],
        inputs={
            "has_brand_dna": bool(brand),
            "has_audience": bool(audience_data),
            "has_media_strategy": bool(media),
            "has_visual_patterns": bool(visual),
            "has_market_opportunity": bool(market),
        },
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
