"""Creative Memory — merge Learning + Knowledge Base (V5.2.5)."""

from __future__ import annotations

import os
from typing import Any
from uuid import UUID

from contentos_shared.payload_utils import coerce_dict

from contentos_intelligence.application.learning import LearningEngine, is_learning_enabled
from contentos_intelligence.domain.context import IntelligenceContext
from contentos_intelligence.domain.creative_memory import CreativeMemoryHit, CreativeMemoryReport

DEFAULT_KB_LIMIT = 5


def creative_memory_enabled() -> bool:
    return os.getenv("CREATIVE_MEMORY_ENABLED", "true").lower() in ("1", "true", "yes")


def _kb_search_limit() -> int:
    try:
        return max(1, min(20, int(os.getenv("CREATIVE_MEMORY_KB_SEARCH_LIMIT", str(DEFAULT_KB_LIMIT)))))
    except ValueError:
        return DEFAULT_KB_LIMIT


def _format_context(
    topic: str,
    learning: dict[str, Any],
    hits: list[CreativeMemoryHit],
) -> str:
    lines: list[str] = [f"Tema: {topic}"]
    if learning.get("hook_text"):
        lines.append(f"Hook aprendido: {learning['hook_text']}")
    if learning.get("cta_text"):
        lines.append(f"CTA aprendido: {learning['cta_text']}")
    if learning.get("content_score") is not None:
        lines.append(f"Content score: {learning['content_score']}")
    updates = learning.get("memory_updates") or []
    if updates:
        lines.append("Memória atualizada: " + ", ".join(str(u) for u in updates[:5]))
    signals = learning.get("signals") or []
    hook_signals = [s for s in signals if isinstance(s, dict) and s.get("signal_type") == "hook"]
    if hook_signals and not learning.get("hook_text"):
        lines.append(f"Sinal hook: {hook_signals[0].get('value', '')}")
    if hits:
        lines.append("Conhecimento relevante:")
        for hit in hits[:5]:
            lines.append(f"- [{hit.resource_type}] {hit.title}: {hit.snippet[:120]}")
    return "\n".join(lines).strip()


def _learning_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    raw = payload.get("learning_report")
    return coerce_dict(raw) if raw else {}


def _resolve_learning(context: IntelligenceContext) -> dict[str, Any]:
    payload = dict(context.payload or {})
    existing = _learning_from_payload(payload)
    if existing:
        return existing
    if not is_learning_enabled():
        return {}
    report = LearningEngine().process(context)
    return report.to_dict()


def merge_creative_memory(context: IntelligenceContext) -> CreativeMemoryReport:
    """Sync merge — learning + payload hints (KB search optional via async helper)."""
    payload = dict(context.payload or {})
    learning = _resolve_learning(context)
    kb_report = coerce_dict(payload.get("knowledge_base_report"))
    hits: list[CreativeMemoryHit] = []
    for raw in payload.get("creative_memory_hits") or []:
        if isinstance(raw, dict) and raw.get("title"):
            hits.append(
                CreativeMemoryHit(
                    resource_type=str(raw.get("resource_type") or "artifact"),
                    title=str(raw.get("title") or ""),
                    snippet=str(raw.get("snippet") or ""),
                    similarity=float(raw.get("similarity") or 0),
                    source=str(raw.get("source") or "payload"),
                )
            )

    topic = str(context.topic or payload.get("topic") or learning.get("topic") or "")
    context_str = _format_context(topic, learning, hits)
    hints = {
        "hook_hint": learning.get("hook_text") or "",
        "cta_hint": learning.get("cta_text") or "",
        "content_score_hint": learning.get("content_score"),
        "kb_hit_count": len(hits),
    }

    return CreativeMemoryReport(
        project_id=str(context.project_id),
        pipeline_id=str(context.pipeline_id) if context.pipeline_id else None,
        topic=topic,
        learning_report=learning,
        knowledge_hits=hits,
        memory_applied=bool(learning.get("memory_applied")),
        memory_updates=list(learning.get("memory_updates") or []),
        kb_indexed_count=int(learning.get("kb_indexed_count") or 0),
        knowledge_indexed_count=int(kb_report.get("knowledge_indexed_count") or 0),
        creative_memory_context=context_str,
        hints=hints,
    )


async def merge_creative_memory_async(
    context: IntelligenceContext,
    db: Any,
    *,
    embedding_client: Any | None = None,
) -> CreativeMemoryReport:
    """Async merge with optional KB index + semantic search."""
    from contentos_intelligence.application.knowledge_base import KnowledgeBaseService
    from contentos_intelligence.application.knowledge_indexer import KnowledgeIndexer
    from contentos_intelligence.domain.knowledge import KnowledgeQueryRequest
    from contentos_intelligence.infrastructure.embedding_client import get_gateway_embedding_client

    payload = dict(context.payload or {})
    report = merge_creative_memory(context)
    kb_report = coerce_dict(payload.get("knowledge_base_report"))
    knowledge_indexed = int(kb_report.get("knowledge_indexed_count") or 0)

    embed = embedding_client or get_gateway_embedding_client()
    kb = KnowledgeBaseService(db, embed)

    if context.pipeline_id and not kb_report.get("knowledge_base_indexed"):
        try:
            indexed = await KnowledgeIndexer(kb).index_pipeline(db, UUID(str(context.pipeline_id)))
            knowledge_indexed = len(indexed)
        except Exception:
            pass

    hits: list[CreativeMemoryHit] = list(report.knowledge_hits)
    query = str(report.topic or payload.get("topic") or "").strip()
    if query:
        try:
            for hit in await kb.search(
                KnowledgeQueryRequest(
                    project_id=UUID(str(context.project_id)),
                    query=query,
                    limit=_kb_search_limit(),
                )
            ):
                hits.append(
                    CreativeMemoryHit(
                        resource_type=hit.resource_type,
                        title=hit.title,
                        snippet=hit.snippet,
                        similarity=float(hit.similarity or 0),
                    )
                )
        except Exception:
            pass

    context_str = _format_context(report.topic, report.learning_report, hits)
    hints = dict(report.hints)
    hints["kb_hit_count"] = len(hits)

    return CreativeMemoryReport(
        project_id=report.project_id,
        pipeline_id=report.pipeline_id,
        topic=report.topic,
        learning_report=report.learning_report,
        knowledge_hits=hits,
        memory_applied=report.memory_applied,
        memory_updates=report.memory_updates,
        kb_indexed_count=report.kb_indexed_count,
        knowledge_indexed_count=knowledge_indexed,
        creative_memory_context=context_str,
        hints=hints,
    )
