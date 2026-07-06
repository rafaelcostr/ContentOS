"""Smart Reuse Engine — suggests reusable content from Knowledge Base."""

from __future__ import annotations

import hashlib
import json
import os
import time
from uuid import UUID

from contentos_intelligence.domain.context import IntelligenceContext
from contentos_intelligence.domain.interfaces import IKnowledgeQuery
from contentos_intelligence.domain.knowledge import KnowledgeQueryRequest
from contentos_intelligence.domain.reuse_suggestion import ReuseSuggestion

REUSE_RESOURCE_TYPES = ("hook", "script", "cta", "asset")

_REASON_HIGH = "Alta similaridade — considere reutilizar em vez de gerar novo conteúdo"
_REASON_MATCH = "Conteúdo similar na Knowledge Base"


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


class ReuseAdvisor:
    """Epic 4 — queries KB before generation to avoid duplicate content."""

    def __init__(
        self,
        knowledge_query: IKnowledgeQuery,
        *,
        min_similarity: float | None = None,
        max_per_type: int | None = None,
        max_total: int | None = None,
        cache_ttl_seconds: float | None = None,
    ) -> None:
        self._kb = knowledge_query
        self._min_similarity = min_similarity if min_similarity is not None else _env_float("REUSE_MIN_SIMILARITY", 0.35)
        self._max_per_type = max_per_type if max_per_type is not None else _env_int("REUSE_MAX_PER_TYPE", 3)
        self._max_total = max_total if max_total is not None else _env_int("REUSE_MAX_TOTAL", 10)
        self._cache_ttl = cache_ttl_seconds if cache_ttl_seconds is not None else _env_float("REUSE_CACHE_TTL", 30.0)
        self._cache: dict[str, tuple[float, list[ReuseSuggestion]]] = {}

    async def suggest(self, context: IntelligenceContext) -> list[ReuseSuggestion]:
        query = _build_query(context)
        if not query.strip():
            return []

        cache_key = _cache_key(context, query)
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        suggestions: list[ReuseSuggestion] = []
        per_type: dict[str, int] = {}

        for resource_type in REUSE_RESOURCE_TYPES:
            hits = await self._kb.search(
                KnowledgeQueryRequest(
                    project_id=context.project_id,
                    query=query,
                    resource_types=[resource_type],
                    limit=self._max_per_type,
                    min_similarity=self._min_similarity,
                    org_id=context.org_id,
                )
            )
            for hit in hits:
                if per_type.get(resource_type, 0) >= self._max_per_type:
                    break
                suggestions.append(_hit_to_suggestion(hit))
                per_type[resource_type] = per_type.get(resource_type, 0) + 1
                if len(suggestions) >= self._max_total:
                    break
            if len(suggestions) >= self._max_total:
                break

        suggestions.sort(key=lambda s: s.similarity, reverse=True)
        result = suggestions[: self._max_total]
        self._cache_set(cache_key, result)
        return result

    def invalidate_cache(self, project_id: UUID | None = None) -> None:
        if project_id is None:
            self._cache.clear()
            return
        prefix = f"{project_id}:"
        for key in list(self._cache):
            if key.startswith(prefix):
                del self._cache[key]

    def _cache_get(self, key: str) -> list[ReuseSuggestion] | None:
        entry = self._cache.get(key)
        if not entry:
            return None
        loaded_at, suggestions = entry
        if time.monotonic() - loaded_at > self._cache_ttl:
            del self._cache[key]
            return None
        return suggestions

    def _cache_set(self, key: str, suggestions: list[ReuseSuggestion]) -> None:
        self._cache[key] = (time.monotonic(), suggestions)


def _build_query(context: IntelligenceContext) -> str:
    parts: list[str] = []
    if context.topic:
        parts.append(context.topic.strip())
    payload = context.payload or {}
    for key in ("topic", "research_topic", "title"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            parts.append(val.strip())
    hook = payload.get("hook")
    if isinstance(hook, dict):
        for k in ("selected_hook", "hook", "text"):
            v = hook.get(k)
            if isinstance(v, str) and v.strip():
                parts.append(v.strip())
    elif isinstance(hook, str) and hook.strip():
        parts.append(hook.strip())
    script = payload.get("script")
    if isinstance(script, dict):
        for k in ("full_text", "hook", "title"):
            v = script.get(k)
            if isinstance(v, str) and v.strip():
                parts.append(v.strip()[:500])
    research = payload.get("research")
    if isinstance(research, dict):
        summary = research.get("summary") or research.get("brief")
        if isinstance(summary, str) and summary.strip():
            parts.append(summary.strip()[:400])
    return " ".join(dict.fromkeys(parts))


def _cache_key(context: IntelligenceContext, query: str) -> str:
    payload_hash = hashlib.sha256(
        json.dumps(context.payload or {}, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    return f"{context.project_id}:{query}:{payload_hash}"


def _hit_to_suggestion(hit) -> ReuseSuggestion:
    reason = _REASON_HIGH if hit.similarity >= 0.8 else _REASON_MATCH
    return ReuseSuggestion(
        resource_type=hit.resource_type,
        resource_id=hit.resource_id,
        title=hit.title,
        similarity=hit.similarity,
        reason=reason,
        metadata={
            **hit.metadata,
            "snippet": hit.snippet,
        },
    )
