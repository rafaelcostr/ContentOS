"""Community reply drafter — rules-based, no auto-post (V5.4.4)."""

from __future__ import annotations

from contentos_intelligence.application.comment_analyzer.sentiment import classify_sentiment
from contentos_intelligence.domain.comment_analysis import CommentItem
from contentos_intelligence.domain.community_draft import CommentReplyDraft


def comment_priority(comment: CommentItem) -> int:
    text = comment.text or ""
    sentiment = classify_sentiment(text)
    if "?" in text:
        return 3
    if sentiment == "negative":
        return 2
    if sentiment == "positive":
        return 1
    return 0


def draft_reply_for_comment(
    comment: CommentItem,
    *,
    platform: str,
    external_media_id: str | None,
    media_title: str | None,
    topic: str,
) -> CommentReplyDraft:
    sentiment = classify_sentiment(comment.text)
    subject = (topic or media_title or "o conteúdo").strip() or "o conteúdo"
    text = (comment.text or "").strip()

    if "?" in text:
        category = "question"
        draft = (
            f"Ótima pergunta! Sobre {subject}: estamos preparando mais detalhes em breve. "
            "Se quiser, comenta qual parte você quer ver no próximo vídeo."
        )
    elif sentiment == "negative":
        category = "support"
        draft = (
            "Obrigado pelo feedback — levamos a sério. "
            f"Vamos usar isso para melhorar o próximo conteúdo sobre {subject}."
        )
    elif sentiment == "positive":
        category = "thanks"
        draft = (
            f"Valeu demais pelo comentário! Fico feliz que curtiu. "
            f"Em breve tem mais sobre {subject} — ativa o sininho para não perder."
        )
    else:
        category = "general"
        draft = f"Obrigado por comentar! Fica de olho para mais sobre {subject}."

    return CommentReplyDraft(
        platform=platform,
        external_media_id=external_media_id,
        media_title=media_title,
        original_comment=text[:1000],
        comment_author=comment.author,
        draft_reply=draft[:2000],
        category=category,
        sentiment=sentiment,
        priority=comment_priority(comment),
        status="draft",
    )


def select_comments_for_drafts(
    comments: list[CommentItem],
    *,
    max_drafts: int,
) -> list[CommentItem]:
    if not comments:
        return []
    ranked = sorted(comments, key=lambda c: (-comment_priority(c), c.text or ""))
    return ranked[:max_drafts]
