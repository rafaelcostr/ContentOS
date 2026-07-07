"""Comment Analyzer — V5.4.3."""

from contentos_intelligence.application.comment_analyzer.sentiment import analyze_comments, classify_sentiment
from contentos_intelligence.application.comment_analyzer.service import (
    analyze_project_comments,
    comment_analyzer_enabled,
    comment_max_per_media,
    list_comment_insights,
)

__all__ = [
    "analyze_comments",
    "analyze_project_comments",
    "classify_sentiment",
    "comment_analyzer_enabled",
    "comment_max_per_media",
    "list_comment_insights",
]
