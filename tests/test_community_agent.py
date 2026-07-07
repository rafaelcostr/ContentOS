"""V5.4.4 — Community Agent tests."""

from __future__ import annotations

from contentos_intelligence.application.community_agent.drafter import (
    comment_priority,
    draft_reply_for_comment,
    select_comments_for_drafts,
)
from contentos_intelligence.application.community_agent.service import community_auto_post
from contentos_intelligence.domain.comment_analysis import CommentItem


def test_community_auto_post_disabled():
    assert community_auto_post() is False


def test_comment_priority_question_highest():
    q = CommentItem(text="Quando lança?")
    neg = CommentItem(text="Muito ruim")
    assert comment_priority(q) > comment_priority(neg)


def test_draft_reply_question():
    draft = draft_reply_for_comment(
        CommentItem(text="Quando sai GTA 6?", author="fan1"),
        platform="youtube",
        external_media_id="vid1",
        media_title="GTA 6 hype",
        topic="GTA 6",
    )
    assert draft.category == "question"
    assert "GTA 6" in draft.draft_reply
    assert draft.status == "draft"


def test_draft_reply_negative():
    draft = draft_reply_for_comment(
        CommentItem(text="Vídeo ruim e chato"),
        platform="tiktok",
        external_media_id="v2",
        media_title=None,
        topic="Test",
    )
    assert draft.category == "support"
    assert draft.sentiment == "negative"


def test_select_comments_for_drafts_limits():
    comments = [
        CommentItem(text="ok"),
        CommentItem(text="Quando?"),
        CommentItem(text="ruim"),
    ]
    selected = select_comments_for_drafts(comments, max_drafts=2)
    assert len(selected) == 2
    assert any("?" in c.text for c in selected)


def test_community_agent_enabled():
    from contentos_intelligence.application.community_agent import community_agent_enabled

    assert isinstance(community_agent_enabled(), bool)
