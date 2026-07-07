"""Project memory domain model."""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from contentos_memory.domain.dna_v2 import (
    CONTENT_ANGLE_LABELS,
    normalize_brand_keywords,
    normalize_cinematic_preset,
    normalize_content_angle,
)
from contentos_memory.domain.project_dna import PACE_LABELS, clamp_humor_level, normalize_pace


@dataclass
class ProjectMemoryData:
    project_id: UUID
    tone: str = ""
    vocabulary: list[str] = field(default_factory=list)
    cta: str = ""
    avg_duration: float | None = None
    hook_style: str = ""
    niche: str = ""
    goal: str = ""
    style: dict = field(default_factory=dict)
    history: list[dict] = field(default_factory=list)
    # V4 Project DNA (Epic 8) — extends same row, no parallel table
    humor_level: float | None = None
    pace: str = ""
    visual_style: dict = field(default_factory=dict)
    narrator_persona: str = ""
    preferred_formats: list[str] = field(default_factory=list)
    hook_patterns: list[str] = field(default_factory=list)
    cta_style: str = ""
    default_voice_builtin: str = ""
    # V5.1.4 Project DNA 2.0
    cinematic_preset: str = ""
    content_angle: str = ""
    brand_keywords: list[str] = field(default_factory=list)
    editing_preferences: dict = field(default_factory=dict)

    def format_dna_context(self) -> str:
        """DNA-only block for {{dna_context}} in prompts."""
        parts: list[str] = []
        if self.humor_level is not None:
            parts.append(f"Humor: {self.humor_level:.0%}")
        if self.pace:
            label = PACE_LABELS.get(self.pace, self.pace)
            parts.append(f"Ritmo: {label}")
        if self.narrator_persona:
            parts.append(f"Narrador: {self.narrator_persona}")
        if self.cta_style:
            parts.append(f"Estilo de CTA: {self.cta_style}")
        if self.preferred_formats:
            parts.append(f"Formatos favoritos: {', '.join(self.preferred_formats[:8])}")
        if self.hook_patterns:
            parts.append(f"Padrões de hook: {', '.join(self.hook_patterns[:6])}")
        if self.visual_style:
            visual_bits = [f"{k}: {v}" for k, v in list(self.visual_style.items())[:8]]
            if visual_bits:
                parts.append(f"Estilo visual: {'; '.join(visual_bits)}")
        if self.content_angle:
            label = CONTENT_ANGLE_LABELS.get(self.content_angle, self.content_angle)
            parts.append(f"Ângulo de conteúdo: {label}")
        if self.cinematic_preset:
            parts.append(f"Preset cinematográfico: {self.cinematic_preset}")
        if self.brand_keywords:
            parts.append(f"Palavras-chave da marca: {', '.join(self.brand_keywords[:10])}")
        return ". ".join(parts) + ("." if parts else "")

    def format_context(self) -> str:
        """Render memory + DNA as a compact string for {{memory_context}} in prompts."""
        parts: list[str] = []
        if self.niche:
            parts.append(f"Nicho: {self.niche}")
        if self.tone:
            parts.append(f"Tom: {self.tone}")
        if self.hook_style:
            parts.append(f"Estilo de gancho: {self.hook_style}")
        if self.goal:
            parts.append(f"Objetivo: {self.goal}")
        if self.cta:
            parts.append(f"CTA padrão: {self.cta}")
        if self.avg_duration:
            parts.append(f"Duração alvo: {int(self.avg_duration)}s")
        if self.vocabulary:
            parts.append(f"Vocabulário preferido: {', '.join(self.vocabulary[:12])}")
        if self.style:
            style_bits = [f"{k}: {v}" for k, v in list(self.style.items())[:6]]
            if style_bits:
                parts.append(f"Estilo: {'; '.join(style_bits)}")
        dna = self.format_dna_context()
        if dna:
            parts.append(dna.rstrip("."))
        if self.history:
            recent = self.history[:3]
            summaries = [h.get("summary", "") for h in recent if h.get("summary")]
            if summaries:
                parts.append(f"Histórico recente: {' | '.join(summaries)}")
        return ". ".join(parts) + ("." if parts else "")

    def to_dna_dict(self) -> dict[str, Any]:
        return {
            "humor_level": self.humor_level,
            "pace": self.pace,
            "visual_style": dict(self.visual_style),
            "narrator_persona": self.narrator_persona,
            "preferred_formats": list(self.preferred_formats),
            "hook_patterns": list(self.hook_patterns),
            "cta_style": self.cta_style,
            "cinematic_preset": self.cinematic_preset,
            "content_angle": self.content_angle,
            "brand_keywords": list(self.brand_keywords),
            "editing_preferences": dict(self.editing_preferences),
            "default_voice_builtin": self.default_voice_builtin,
            "dna_context_preview": self.format_dna_context(),
        }

    def apply_dna_patch(self, patch: dict[str, Any]) -> None:
        """Merge partial DNA update (PATCH semantics)."""
        if "humor_level" in patch:
            self.humor_level = clamp_humor_level(patch.get("humor_level"))
        if "pace" in patch:
            self.pace = normalize_pace(patch.get("pace"))
        if "visual_style" in patch and patch["visual_style"] is not None:
            self.visual_style = dict(patch["visual_style"])
        if "narrator_persona" in patch and patch["narrator_persona"] is not None:
            self.narrator_persona = str(patch["narrator_persona"])
        if "preferred_formats" in patch and patch["preferred_formats"] is not None:
            self.preferred_formats = list(patch["preferred_formats"])
        if "hook_patterns" in patch and patch["hook_patterns"] is not None:
            self.hook_patterns = list(patch["hook_patterns"])
        if "cta_style" in patch and patch["cta_style"] is not None:
            self.cta_style = str(patch["cta_style"])
        if "cinematic_preset" in patch:
            self.cinematic_preset = normalize_cinematic_preset(patch.get("cinematic_preset"))
        if "content_angle" in patch:
            self.content_angle = normalize_content_angle(patch.get("content_angle"))
        if "brand_keywords" in patch and patch["brand_keywords"] is not None:
            self.brand_keywords = normalize_brand_keywords(patch["brand_keywords"])
        if "editing_preferences" in patch and patch["editing_preferences"] is not None:
            self.editing_preferences = dict(patch["editing_preferences"])
        if "default_voice_builtin" in patch and patch["default_voice_builtin"] is not None:
            self.default_voice_builtin = str(patch["default_voice_builtin"])

    def to_dict(self) -> dict:
        return {
            "project_id": str(self.project_id),
            "tone": self.tone,
            "vocabulary": self.vocabulary,
            "cta": self.cta,
            "avg_duration": self.avg_duration,
            "hook_style": self.hook_style,
            "niche": self.niche,
            "goal": self.goal,
            "style": self.style,
            "history": self.history,
            "default_voice_builtin": self.default_voice_builtin,
            **self.to_dna_dict(),
        }

    @classmethod
    def from_dict(cls, project_id: UUID, data: dict) -> "ProjectMemoryData":
        return cls(
            project_id=project_id,
            tone=str(data.get("tone") or ""),
            vocabulary=list(data.get("vocabulary") or []),
            cta=str(data.get("cta") or ""),
            avg_duration=data.get("avg_duration"),
            hook_style=str(data.get("hook_style") or ""),
            niche=str(data.get("niche") or ""),
            goal=str(data.get("goal") or ""),
            style=dict(data.get("style") or {}),
            history=list(data.get("history") or []),
            humor_level=clamp_humor_level(data.get("humor_level")),
            pace=normalize_pace(data.get("pace")),
            visual_style=dict(data.get("visual_style") or {}),
            narrator_persona=str(data.get("narrator_persona") or ""),
            preferred_formats=list(data.get("preferred_formats") or []),
            hook_patterns=list(data.get("hook_patterns") or []),
            cta_style=str(data.get("cta_style") or ""),
            default_voice_builtin=str(data.get("default_voice_builtin") or ""),
            cinematic_preset=normalize_cinematic_preset(data.get("cinematic_preset")),
            content_angle=normalize_content_angle(data.get("content_angle")),
            brand_keywords=normalize_brand_keywords(data.get("brand_keywords")),
            editing_preferences=dict(data.get("editing_preferences") or {}),
        )

    @classmethod
    def empty(cls, project_id: UUID) -> "ProjectMemoryData":
        return cls(project_id=project_id)
