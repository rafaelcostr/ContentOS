"""Licensed trailers source stub."""

from __future__ import annotations

from contentos_sources.domain.source_candidate import SourceAsset, SourceCandidate, SourceHealth
from contentos_sources.domain.source_query import SourceQuery


class LicensedTrailerSource:
    source_id = "licensed_trailers"

    async def search(self, query: SourceQuery) -> list[SourceCandidate]:
        # Stub — integrate licensed catalog in production
        if not query.tags and not query.visual_hint:
            return []
        return [
            SourceCandidate(
                source_id=self.source_id,
                candidate_id=f"trailer_{query.scene_label or 'scene'}",
                title=f"Licensed trailer match: {query.visual_hint or query.topic}",
                score=0.55,
                reason="Licensed catalog stub",
                metadata={"license": "preview_only"},
            )
        ]

    async def fetch(self, candidate_id: str) -> SourceAsset:
        raise NotImplementedError("Licensed trailer fetch requires catalog integration")

    async def health(self) -> SourceHealth:
        return SourceHealth(self.source_id, True, "Stub adapter — configure catalog for production")
