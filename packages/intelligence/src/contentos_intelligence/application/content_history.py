"""Content history — chronological knowledge entries per project."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from contentos_intelligence.domain.knowledge_entry import KnowledgeEntryData
from contentos_intelligence.infrastructure.kb_repository import KnowledgeRepository


class ContentHistory:
    def __init__(self, db: AsyncSession, repository: KnowledgeRepository | None = None) -> None:
        self._db = db
        self._repo = repository or KnowledgeRepository()

    async def list_entries(
        self,
        project_id: UUID,
        *,
        resource_type: str | None = None,
        limit: int = 50,
    ) -> list[KnowledgeEntryData]:
        return await self._repo.list_by_project(
            self._db,
            project_id,
            resource_type=resource_type,
            limit=limit,
        )
