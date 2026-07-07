"""Community Agent domain — V5.4.4 (drafts only, no auto-post)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CommentReplyDraft:
    platform: str
    external_media_id: str | None
    media_title: str | None
    original_comment: str
    comment_author: str | None
    draft_reply: str
    category: str
    sentiment: str
    priority: int = 0
    status: str = "draft"
    draft_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "draft_id": self.draft_id,
            "platform": self.platform,
            "external_media_id": self.external_media_id,
            "media_title": self.media_title,
            "original_comment": self.original_comment,
            "comment_author": self.comment_author,
            "draft_reply": self.draft_reply,
            "category": self.category,
            "sentiment": self.sentiment,
            "priority": self.priority,
            "status": self.status,
        }


@dataclass
class CommunityDraftReport:
    project_id: str
    drafts: list[CommentReplyDraft] = field(default_factory=list)
    drafts_created: int = 0
    auto_post: bool = False
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "drafts": [d.to_dict() for d in self.drafts],
            "drafts_created": self.drafts_created,
            "auto_post": self.auto_post,
            "summary": self.summary,
        }
