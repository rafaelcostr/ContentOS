"""Take recommendation domain models (V5.0.4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SceneTakeQuery:
    topic: str
    scene_label: str
    scene: dict[str, Any] = field(default_factory=dict)
    duration_needed: float | None = None

    @property
    def search_text(self) -> str:
        parts = [
            self.topic,
            self.scene_label,
            str(self.scene.get("visual_hint") or ""),
            str(self.scene.get("description") or ""),
            str(self.scene.get("text") or ""),
            str(self.scene.get("theme") or ""),
            str(self.scene.get("game") or ""),
            str(self.scene.get("character") or ""),
            str(self.scene.get("motion") or ""),
            str(self.scene.get("emotion") or ""),
        ]
        return " ".join(p.strip() for p in parts if p and str(p).strip())


@dataclass(frozen=True)
class TakeRankResult:
    asset_id: str | None
    asset_key: str
    bucket: str
    content_type: str
    score: float
    reasons: tuple[str, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "asset_key": self.asset_key,
            "bucket": self.bucket,
            "content_type": self.content_type,
            "score": round(self.score, 2),
            "reasons": list(self.reasons),
            "metadata": self.metadata,
        }
