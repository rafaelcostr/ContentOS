"""Content Sources application service."""

from __future__ import annotations

import asyncio
from functools import lru_cache

from contentos_sources.domain.source_candidate import SourceAsset, SourceCandidate, SourceHealth
from contentos_sources.domain.source_query import SourceQuery
from contentos_sources.infrastructure.factory import build_registry, enabled_source_ids


class SourceManager:
    def __init__(self) -> None:
        self._registry = build_registry()

    def list_sources(self) -> list[str]:
        return [sid for sid in self._registry.list_ids() if sid in enabled_source_ids()]

    async def search(self, query: SourceQuery, source_id: str | None = None) -> list[SourceCandidate]:
        ids = [source_id] if source_id else self.list_sources()
        results: list[SourceCandidate] = []
        for sid in ids:
            src = self._registry.get(sid)
            if not src:
                continue
            try:
                found = await src.search(query)
                results.extend(found)
            except Exception:
                continue
        results.sort(key=lambda c: c.score, reverse=True)
        return results

    async def search_all_scenes(self, scenes: list[dict], project_id, topic: str) -> list[dict]:
        scene_results: list[dict] = []
        for i, scene in enumerate(scenes):
            query = SourceQuery(
                scene_description=scene.get("description", scene.get("text", "")),
                visual_hint=scene.get("visual", scene.get("visual_hint", "")),
                duration_needed=float(scene.get("duration_seconds", 5)),
                tags=scene.get("tags", []) if isinstance(scene.get("tags"), list) else [],
                project_id=project_id,
                scene_label=scene.get("label", f"scene_{i}"),
                topic=topic,
            )
            candidates = await self.search(query)
            scene_results.append(
                {
                    "scene_index": i,
                    "scene_label": query.scene_label,
                    "candidates": [c.to_dict() for c in candidates[:5]],
                }
            )
        return scene_results

    async def fetch(self, source_id: str, candidate_id: str) -> SourceAsset:
        src = self._registry.get(source_id)
        if not src:
            raise ValueError(f"Unknown source: {source_id}")
        return await src.fetch(candidate_id)

    async def health_all(self) -> list[dict]:
        async def _check(sid: str) -> dict:
            src = self._registry.get(sid)
            if not src:
                return {"source_id": sid, "healthy": False, "message": "not registered"}
            h: SourceHealth = await src.health()
            return {"source_id": h.source_id, "healthy": h.healthy, "message": h.message, "latency_ms": h.latency_ms}

        ids = self.list_sources()
        rows = await asyncio.gather(*[_check(sid) for sid in ids])
        return list(rows)


@lru_cache(maxsize=1)
def get_source_manager() -> SourceManager:
    return SourceManager()
