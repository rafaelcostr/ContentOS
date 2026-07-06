"""Embedding index — vectorize and store knowledge entries."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from contentos_intelligence.domain.interfaces import IEmbeddingClient
from contentos_intelligence.domain.knowledge_entry import KnowledgeEntryData
from contentos_intelligence.infrastructure.kb_repository import KnowledgeRepository


class EmbeddingIndex:
    def __init__(
        self,
        db: AsyncSession,
        embedding_client: IEmbeddingClient,
        repository: KnowledgeRepository | None = None,
    ) -> None:
        self._db = db
        self._embed = embedding_client
        self._repo = repository or KnowledgeRepository()

    async def index_entry(self, data: KnowledgeEntryData) -> KnowledgeEntryData:
        if data.content_text.strip():
            vectors = await self._embed.embed([data.content_text])
            if vectors and vectors[0]:
                data.embedding = vectors[0]
        if not data.snippet:
            data.snippet = data.content_text[:500]
        if data.resource_id:
            latest = await self._repo.get_latest(
                self._db,
                resource_type=data.resource_type,
                resource_id=data.resource_id,
            )
            if latest:
                data.version = latest.version + 1
                data.parent_entry_id = latest.id
        return await self._repo.insert(self._db, data)
