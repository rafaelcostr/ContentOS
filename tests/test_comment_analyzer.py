"""V5.4.3 — Comment Analyzer tests."""

from __future__ import annotations

from contentos_intelligence.application.comment_analyzer.sentiment import (
    analyze_comments,
    classify_sentiment,
    extract_themes,
)
from contentos_intelligence.domain.comment_analysis import CommentItem


def test_classify_sentiment_positive():
    assert classify_sentiment("Amei esse vídeo, top demais!") == "positive"


def test_classify_sentiment_negative():
    assert classify_sentiment("Muito ruim e chato") == "negative"


def test_classify_sentiment_neutral():
    assert classify_sentiment("ok") == "neutral"


def test_extract_themes():
    comments = [
        CommentItem(text="GTA 6 mapa incrível"),
        CommentItem(text="mapa do GTA sensacional"),
        CommentItem(text="quando lança GTA?"),
    ]
    themes = extract_themes(comments, limit=3)
    assert "mapa" in themes or "gta" in themes


def test_analyze_comments_counts():
    comments = [
        CommentItem(text="Amei!"),
        CommentItem(text="Ruim"),
        CommentItem(text="Quando sai?"),
    ]
    report = analyze_comments("youtube", "vid1", "GTA 6", comments)
    assert report.comment_count == 3
    assert report.positive_pct > 0
    assert report.negative_pct > 0
    assert report.question_count == 1


def test_comment_analyzer_enabled():
    from contentos_intelligence.application.comment_analyzer import comment_analyzer_enabled

    assert isinstance(comment_analyzer_enabled(), bool)
