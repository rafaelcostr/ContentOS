"""Relevance scoring for source search queries."""

from __future__ import annotations

import re

from contentos_sources.domain.source_query import SourceQuery

_STOP = frozenset({"the", "and", "for", "com", "uma", "para", "com", "que", "dos", "das"})


def query_terms(query: SourceQuery) -> list[str]:
    parts = [
        query.scene_description,
        query.visual_hint,
        query.topic,
        query.scene_label,
        *query.tags,
    ]
    text = " ".join(str(p) for p in parts if p)
    tokens = [t.lower() for t in re.findall(r"[\wÀ-ÿ]{2,}", text)]
    return [t for t in tokens if t not in _STOP]


def relevance_score(haystack: str, terms: list[str]) -> float:
    if not terms:
        return 0.5
    hay = haystack.lower()
    hits = sum(1 for term in terms if term in hay)
    return min(1.0, hits / len(terms))
