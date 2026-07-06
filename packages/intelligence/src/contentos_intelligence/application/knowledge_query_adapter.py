"""IKnowledgeQuery adapter using async DB sessions."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from contentos_intelligence.application.knowledge_base import KnowledgeBaseService
from contentos_intelligence.domain.interfaces import IEmbeddingClient, IKnowledgeQuery
from contentos_intelligence.domain.knowledge import KnowledgeHit, KnowledgeQueryRequest


class DbKnowledgeQuery(IKnowledgeQuery):
    """Resolves search via KnowledgeBaseService + session factory."""

    def __init__(
        self,
        session_factory: Callable[[], AsyncSession],
        embedding_client: IEmbeddingClient,
    ) -> None:
        self._session_factory = session_factory
        self._embedding_client = embedding_client

    async def search(self, request: KnowledgeQueryRequest) -> list[KnowledgeHit]:
        async with self._session_factory() as db:
            service = KnowledgeBaseService(db, self._embedding_client)
            hits = await service.search(request)
            await db.commit()
            return hits
