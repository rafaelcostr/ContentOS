"""Gameplay recordings source (filter local library by prefix)."""

from __future__ import annotations

import os

from contentos_sources.adapters.local_library import LocalLibrarySource
from contentos_sources.domain.source_candidate import SourceCandidate, SourceHealth
from contentos_sources.domain.source_query import SourceQuery


class GameplaySource(LocalLibrarySource):
    source_id = "gameplay"

    async def search(self, query: SourceQuery) -> list[SourceCandidate]:
        results = await super().search(query)
        prefix = os.getenv("CONTENT_SOURCE_GAMEPLAY_PREFIX", "takes/gameplay/")
        filtered = [c for c in results if prefix in c.candidate_id or "gameplay" in c.candidate_id.lower()]
        return filtered or results[:3]

    async def health(self) -> SourceHealth:
        h = await super().health()
        return SourceHealth(self.source_id, h.healthy, h.message or "Gameplay library")
