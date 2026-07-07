"""Comment sentiment + theme extraction — rules-based (V5.4.3)."""

from __future__ import annotations

import re
from collections import Counter

from contentos_intelligence.domain.comment_analysis import CommentItem, CommentMediaAnalysis

POSITIVE = frozenset({
    "amo", "amei", "top", "demais", "incrível", "incrivel", "sensacional", "parabéns", "parabens",
    "bom", "ótimo", "otimo", "excelente", "perfeito", "massa", "brabo", "foda", "love", "great",
    "amazing", "awesome", "good", "nice", "best", "fire", "lit",
})
NEGATIVE = frozenset({
    "ruim", "péssimo", "pessimo", "chato", "boring", "bad", "hate", "odio", "ódio", "horrível",
    "horrivel", "lixo", "trash", "worst", "terrible", "awful", "fake", "clickbait",
})
STOPWORDS = frozenset({
    "para", "com", "que", "uma", "por", "mais", "muito", "esse", "essa", "isso", "aqui", "você",
    "voce", "the", "and", "for", "this", "that", "with", "from", "have", "your",
})


def classify_sentiment(text: str) -> str:
    tokens = _tokens(text)
    if not tokens:
        return "neutral"
    pos = sum(1 for t in tokens if t in POSITIVE)
    neg = sum(1 for t in tokens if t in NEGATIVE)
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-zà-ú0-9]+", (text or "").lower())


def extract_themes(comments: list[CommentItem], *, limit: int = 5) -> list[str]:
    counter: Counter[str] = Counter()
    for item in comments:
        for token in _tokens(item.text):
            if len(token) < 4 or token in STOPWORDS:
                continue
            counter[token] += 1
    return [word for word, _ in counter.most_common(limit)]


def analyze_comments(
    platform: str,
    external_media_id: str | None,
    title: str | None,
    comments: list[CommentItem],
) -> CommentMediaAnalysis:
    analysis = CommentMediaAnalysis(
        platform=platform,
        external_media_id=external_media_id,
        title=title,
        comment_count=len(comments),
    )
    if not comments:
        return analysis

    sentiments = [classify_sentiment(c.text) for c in comments]
    total = len(sentiments)
    pos = sentiments.count("positive")
    neg = sentiments.count("negative")
    neu = sentiments.count("neutral")
    analysis.positive_pct = round(100 * pos / total, 1)
    analysis.negative_pct = round(100 * neg / total, 1)
    analysis.neutral_pct = round(100 * neu / total, 1)
    analysis.question_count = sum(1 for c in comments if "?" in c.text)
    analysis.themes = extract_themes(comments)
    analysis.sample_comments = [c.text[:200] for c in comments[:5]]
    return analysis
