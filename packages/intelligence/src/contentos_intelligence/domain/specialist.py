"""Specialist agent types — Epic 5."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SpecialistProfile:
    specialist_id: str
    name: str
    niche: str
    tone: str = ""
    vocabulary: list[str] = field(default_factory=list)
    cta_style: str = ""
    structure: str = ""
    prompt_pack: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "specialist_id": self.specialist_id,
            "name": self.name,
            "niche": self.niche,
            "tone": self.tone,
            "vocabulary": list(self.vocabulary),
            "cta_style": self.cta_style,
            "structure": self.structure,
            "prompt_pack": self.prompt_pack,
            "metadata": dict(self.metadata),
        }


@dataclass
class SpecialistSelection:
    specialist: SpecialistProfile
    confidence: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "specialist": self.specialist.to_dict(),
            "confidence": round(self.confidence, 4),
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SpecialistSelection:
        spec_data = data.get("specialist") or {}
        profile = SpecialistProfile(
            specialist_id=str(spec_data.get("specialist_id", "general")),
            name=str(spec_data.get("name", "General")),
            niche=str(spec_data.get("niche", "general")),
            tone=str(spec_data.get("tone", "")),
            vocabulary=list(spec_data.get("vocabulary") or []),
            cta_style=str(spec_data.get("cta_style", "")),
            structure=str(spec_data.get("structure", "")),
            prompt_pack=str(spec_data.get("prompt_pack", "")),
            metadata=dict(spec_data.get("metadata") or {}),
        )
        return cls(
            specialist=profile,
            confidence=float(data.get("confidence", 0)),
            reason=str(data.get("reason", "")),
        )
