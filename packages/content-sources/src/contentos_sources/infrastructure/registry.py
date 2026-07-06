"""Adapter registry."""

from __future__ import annotations

from contentos_sources.domain.content_source import ContentSource


class SourceRegistry:
    def __init__(self) -> None:
        self._sources: dict[str, ContentSource] = {}

    def register(self, source: ContentSource) -> None:
        self._sources[source.source_id] = source

    def get(self, source_id: str) -> ContentSource | None:
        return self._sources.get(source_id)

    def list_ids(self) -> list[str]:
        return list(self._sources.keys())

    def all(self) -> list[ContentSource]:
        return list(self._sources.values())
