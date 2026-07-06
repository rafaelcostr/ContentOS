"""Source search candidate and fetched asset."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SourceCandidate:
    source_id: str
    candidate_id: str
    title: str
    score: float = 0.0
    reason: str = ""
    duration_seconds: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "candidate_id": self.candidate_id,
            "title": self.title,
            "score": self.score,
            "reason": self.reason,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata,
        }


@dataclass
class SourceAsset:
    source_id: str
    candidate_id: str
    data: bytes
    content_type: str = "video/mp4"
    filename: str = "clip.mp4"
    metadata: dict[str, Any] = field(default_factory=dict)
    sha256: str = ""


@dataclass
class SourceHealth:
    source_id: str
    healthy: bool
    message: str = ""
    latency_ms: int | None = None
