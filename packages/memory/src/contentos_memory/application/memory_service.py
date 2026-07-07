"""Memory Manager application service."""

from __future__ import annotations

import time
from functools import lru_cache
from uuid import UUID

from contentos_memory.domain.project_memory import ProjectMemoryData
from contentos_memory.infrastructure.db_repository import MemoryRepository, load_sync
from sqlalchemy.ext.asyncio import AsyncSession


class MemoryService:
    """Loads and formats per-project creative memory for prompt injection."""

    def __init__(self, cache_ttl_seconds: float = 30.0) -> None:
        self._repo = MemoryRepository()
        self._cache: dict[str, ProjectMemoryData] = {}
        self._cache_loaded_at: dict[str, float] = {}
        self._cache_ttl = cache_ttl_seconds

    def get_memory(self, project_id: UUID) -> ProjectMemoryData:
        key = str(project_id)
        now = time.monotonic()
        if key in self._cache and (now - self._cache_loaded_at.get(key, 0)) < self._cache_ttl:
            return self._cache[key]
        data = load_sync(project_id)
        self._cache[key] = data
        self._cache_loaded_at[key] = now
        return data

    def format_context(self, project_id: UUID) -> str:
        return self.get_memory(project_id).format_context()

    def prompt_variables(self, project_id: UUID) -> dict[str, str]:
        memory = self.get_memory(project_id)
        return {
            "memory_context": memory.format_context(),
            "dna_context": memory.format_dna_context(),
            "niche": memory.niche,
            "narrator_persona": memory.narrator_persona,
            "pace": memory.pace,
            "cta_style": memory.cta_style,
            "content_angle": memory.content_angle,
            "cinematic_preset": memory.cinematic_preset,
        }

    async def update_dna(
        self, db: AsyncSession, project_id: UUID, patch: dict
    ) -> ProjectMemoryData:
        current = await self._repo.get(db, project_id)
        current.apply_dna_patch(patch)
        return await self.update(db, current)

    def invalidate(self, project_id: UUID | None = None) -> None:
        if project_id is None:
            self._cache.clear()
            self._cache_loaded_at.clear()
            return
        key = str(project_id)
        self._cache.pop(key, None)
        self._cache_loaded_at.pop(key, None)

    async def get_async(self, db: AsyncSession, project_id: UUID) -> ProjectMemoryData:
        return await self._repo.get(db, project_id)

    async def update(self, db: AsyncSession, data: ProjectMemoryData) -> ProjectMemoryData:
        updated = await self._repo.upsert(db, data)
        self.invalidate(data.project_id)
        return updated

    async def ensure_empty(self, db: AsyncSession, project_id: UUID) -> ProjectMemoryData:
        from contentos_database.models import ProjectMemory
        from sqlalchemy import select

        result = await db.execute(select(ProjectMemory).where(ProjectMemory.project_id == project_id))
        if result.scalar_one_or_none():
            return await self._repo.get(db, project_id)
        return await self._repo.create_empty(db, project_id)


@lru_cache(maxsize=1)
def get_memory_service() -> MemoryService:
    return MemoryService()


def reset_memory_service_cache() -> None:
    get_memory_service.cache_clear()
