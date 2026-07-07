"""AI Director decision — V5.2.4."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DirectorWeakSignal:
    name: str
    score: float
    weight: float
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "score": round(self.score, 2),
            "weight": round(self.weight, 3),
            "source": self.source,
        }


@dataclass
class DirectorDecision:
    passed: bool
    overall_score: float
    min_score: float
    target: str
    retry_from: str
    reason: str
    weak_signals: list[DirectorWeakSignal] = field(default_factory=list)
    action: str = "advance"

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "overall_score": round(self.overall_score, 2),
            "min_score": round(self.min_score, 2),
            "target": self.target,
            "retry_from": self.retry_from,
            "reason": self.reason,
            "action": self.action,
            "weak_signals": [s.to_dict() for s in self.weak_signals],
        }
