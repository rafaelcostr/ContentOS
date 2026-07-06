"""Semantic search over knowledge entries."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from contentos_intelligence.application.similarity import cosine_similarity, text_overlap_score
from contentos_intelligence.domain.interfaces import IEmbeddingClient
from contentos_intelligence.domain.knowledge import KnowledgeHit, KnowledgeQueryRequest
from contentos_intelligence.domain.knowledge_entry import KnowledgeEntryData
from contentos_intelligence.infrastructure.kb_repository import KnowledgeRepository


class SemanticSearch:
    def __init__(
        self,
        db: AsyncSession,
        embedding_client: IEmbeddingClient,
        repository: KnowledgeRepository | None = None,
    ) -> None:
        self._db = db
        self._embed = embedding_client
        self._repo = repository or KnowledgeRepository()

    async def search(self, request: KnowledgeQueryRequest) -> list[KnowledgeHit]:
        candidates = await self._repo.fetch_candidates(
            self._db,
            request.project_id,
            resource_types=request.resource_types or None,
            limit=max(request.limit * 20, 50),
        )
        if not candidates:
            return []

        query_vector: list[float] = []
        vectors = await self._embed.embed([request.query])
        if vectors:
            query_vector = vectors[0]

        scored: list[tuple[float, KnowledgeEntryData]] = []
        for entry in candidates:
            if query_vector and entry.embedding:
                score = cosine_similarity(query_vector, entry.embedding)
            else:
                score = text_overlap_score(request.query, entry.content_text)
            if score >= request.min_similarity:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        hits: list[KnowledgeHit] = []
        for score, entry in scored[: request.limit]:
            hits.append(
                KnowledgeHit(
                    resource_type=entry.resource_type,
                    resource_id=entry.resource_id,
                    title=entry.title,
                    snippet=entry.snippet or entry.content_text[:300],
                    similarity=score,
                    metadata={
                        **entry.metadata,
                        "knowledge_entry_id": str(entry.id) if entry.id else None,
                        "pipeline_id": str(entry.pipeline_id) if entry.pipeline_id else None,
                        "version": entry.version,
                    },
                )
            )
        return hits
