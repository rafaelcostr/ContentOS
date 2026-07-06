"""Knowledge Base facade — search, history, indexing."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from contentos_intelligence.application.content_history import ContentHistory
from contentos_intelligence.application.embedding_index import EmbeddingIndex
from contentos_intelligence.application.semantic_search import SemanticSearch
from contentos_intelligence.application.version_history import VersionHistory
from contentos_intelligence.domain.interfaces import IEmbeddingClient
from contentos_intelligence.domain.knowledge import KnowledgeHit, KnowledgeQueryRequest
from contentos_intelligence.domain.knowledge_entry import KnowledgeEntryData
from contentos_intelligence.infrastructure.kb_repository import KnowledgeRepository


class KnowledgeBaseService:
    """Epic 3 — unified Knowledge Base API."""

    def __init__(
        self,
        db: AsyncSession,
        embedding_client: IEmbeddingClient,
        repository: KnowledgeRepository | None = None,
    ) -> None:
        self._db = db
        self._embed = embedding_client
        self._repo = repository or KnowledgeRepository()
        self._search = SemanticSearch(db, embedding_client, self._repo)
        self._index = EmbeddingIndex(db, embedding_client, self._repo)
        self._history = ContentHistory(db, self._repo)
        self._versions = VersionHistory(db, self._repo)

    async def search(self, request: KnowledgeQueryRequest) -> list[KnowledgeHit]:
        return await self._search.search(request)

    async def history(
        self,
        project_id: UUID,
        *,
        resource_type: str | None = None,
        limit: int = 50,
    ) -> list[KnowledgeEntryData]:
        return await self._history.list_entries(project_id, resource_type=resource_type, limit=limit)

    async def versions(self, resource_type: str, resource_id: UUID) -> list[KnowledgeEntryData]:
        return await self._versions.list_versions(resource_type, resource_id)

    async def index_entry(self, data: KnowledgeEntryData) -> KnowledgeEntryData:
        return await self._index.index_entry(data)
