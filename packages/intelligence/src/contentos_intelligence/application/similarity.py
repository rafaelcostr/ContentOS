"""Cosine similarity for semantic search."""

from __future__ import annotations


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def text_overlap_score(query: str, content: str) -> float:
    """Fallback when embeddings are unavailable."""
    q = {w for w in query.lower().split() if len(w) > 2}
    if not q:
        return 0.0
    c = content.lower()
    hits = sum(1 for w in q if w in c)
    return hits / len(q)
