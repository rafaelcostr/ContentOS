"""Comment analysis domain — V5.4.3."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CommentItem:
    text: str
    author: str | None = None
    platform: str = ""
    external_media_id: str | None = None
    published_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "author": self.author,
            "platform": self.platform,
            "external_media_id": self.external_media_id,
            "published_at": self.published_at,
        }


@dataclass
class CommentMediaAnalysis:
    platform: str
    external_media_id: str | None
    title: str | None
    comment_count: int = 0
    positive_pct: float = 0.0
    negative_pct: float = 0.0
    neutral_pct: float = 0.0
    question_count: int = 0
    themes: list[str] = field(default_factory=list)
    sample_comments: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "external_media_id": self.external_media_id,
            "title": self.title,
            "comment_count": self.comment_count,
            "positive_pct": self.positive_pct,
            "negative_pct": self.negative_pct,
            "neutral_pct": self.neutral_pct,
            "question_count": self.question_count,
            "themes": list(self.themes),
            "sample_comments": list(self.sample_comments),
            "error": self.error,
        }


@dataclass
class CommentAnalysisReport:
    project_id: str
    media_analyses: list[CommentMediaAnalysis] = field(default_factory=list)
    total_comments: int = 0
    kb_indexed_count: int = 0
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "media_analyses": [m.to_dict() for m in self.media_analyses],
            "total_comments": self.total_comments,
            "kb_indexed_count": self.kb_indexed_count,
            "summary": self.summary,
        }
