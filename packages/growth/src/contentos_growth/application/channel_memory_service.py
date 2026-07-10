"""Channel memory application service — Growth OS Fase 6."""

from __future__ import annotations

import time
from functools import lru_cache
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from contentos_growth.application.channel_analyzer import ChannelAnalysisResult
from contentos_growth.channel_memory_model import ChannelMemoryData, extract_patterns_from_media
from contentos_growth.infrastructure.channel_memory_repository import ChannelMemoryRepository, load_sync


class ChannelMemoryService:
    def __init__(self, cache_ttl_seconds: float = 30.0) -> None:
        self._repo = ChannelMemoryRepository()
        self._cache: dict[str, ChannelMemoryData] = {}
        self._cache_loaded_at: dict[str, float] = {}
        self._cache_ttl = cache_ttl_seconds

    def get_memory(self, channel_id: UUID) -> ChannelMemoryData | None:
        key = str(channel_id)
        now = time.monotonic()
        if key in self._cache and (now - self._cache_loaded_at.get(key, 0)) < self._cache_ttl:
            return self._cache[key]
        data = load_sync(channel_id)
        if data:
            self._cache[key] = data
            self._cache_loaded_at[key] = now
        return data

    def format_context(self, channel_id: UUID) -> str:
        data = self.get_memory(channel_id)
        return data.format_channel_context() if data else ""

    def prompt_variables(self, channel_id: UUID) -> dict[str, str]:
        data = self.get_memory(channel_id)
        if not data:
            return {"channel_context": ""}
        return {
            "channel_context": data.format_channel_context(),
            "channel_top_hooks": ", ".join(data.top_hooks[:6]),
            "channel_top_hashtags": ", ".join(data.top_hashtags[:10]),
        }

    def invalidate(self, channel_id: UUID | None = None) -> None:
        if channel_id is None:
            self._cache.clear()
            self._cache_loaded_at.clear()
            return
        key = str(channel_id)
        self._cache.pop(key, None)
        self._cache_loaded_at.pop(key, None)

    async def get_async(self, db: AsyncSession, channel_id: UUID) -> ChannelMemoryData | None:
        return await self._repo.get(db, channel_id)

    async def update(self, db: AsyncSession, data: ChannelMemoryData) -> ChannelMemoryData:
        updated = await self._repo.upsert(db, data)
        self.invalidate(data.channel_id)
        return updated

    async def patch(self, db: AsyncSession, channel_id: UUID, patch: dict[str, Any]) -> ChannelMemoryData:
        current = await self._repo.get(db, channel_id)
        if not current:
            raise ValueError("Channel not found")
        current.apply_patch(patch)
        return await self.update(db, current)

    async def seed_from_analysis(
        self,
        db: AsyncSession,
        *,
        channel_id: UUID,
        project_id: UUID,
        analysis: ChannelAnalysisResult,
        overview: dict[str, Any] | None,
    ) -> ChannelMemoryData:
        current = await self._repo.get(db, channel_id)
        if not current:
            current = ChannelMemoryData.empty(channel_id, project_id)

        media_items = (overview or {}).get("media_items") or []
        patterns = extract_patterns_from_media(media_items)
        report = analysis.report or {}
        profile = analysis.profile or {}

        hashtags = list(report.get("hashtags") or profile.get("hashtags") or [])
        ctas = list(report.get("cta_patterns") or profile.get("cta_patterns") or [])
        themes = list(patterns.get("top_themes") or [])
        niche = profile.get("niche")
        if niche and str(niche) not in themes:
            themes.insert(0, str(niche))

        insights = [analysis.summary]
        for rec in analysis.recommendations[:4]:
            insights.append(f"{rec.title}: {rec.detail}")

        current.merge_seed(
            winning_videos=patterns["winning_videos"],
            losing_videos=patterns["losing_videos"],
            top_hooks=patterns["top_hooks"],
            top_ctas=ctas,
            top_themes=themes,
            top_hashtags=hashtags,
            best_posting_hours=patterns["best_posting_hours"],
            insights=insights,
        )
        return await self.update(db, current)


@lru_cache(maxsize=1)
def get_channel_memory_service() -> ChannelMemoryService:
    return ChannelMemoryService()


def reset_channel_memory_service_cache() -> None:
    get_channel_memory_service.cache_clear()
