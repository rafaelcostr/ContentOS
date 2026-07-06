"""Version history — revisions per resource."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from contentos_intelligence.domain.knowledge_entry import KnowledgeEntryData
from contentos_intelligence.infrastructure.kb_repository import KnowledgeRepository


class VersionHistory:
    def __init__(self, db: AsyncSession, repository: KnowledgeRepository | None = None) -> None:
        self._db = db
        self._repo = repository or KnowledgeRepository()

    async def list_versions(self, resource_type: str, resource_id: UUID) -> list[KnowledgeEntryData]:
        return await self._repo.list_versions(self._db, resource_type=resource_type, resource_id=resource_id)
