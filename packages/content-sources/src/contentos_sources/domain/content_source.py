"""ContentSource protocol."""

from typing import Protocol

from contentos_sources.domain.source_candidate import SourceAsset, SourceCandidate, SourceHealth
from contentos_sources.domain.source_query import SourceQuery


class ContentSource(Protocol):
    source_id: str

    async def search(self, query: SourceQuery) -> list[SourceCandidate]: ...

    async def fetch(self, candidate_id: str) -> SourceAsset: ...

    async def health(self) -> SourceHealth: ...
