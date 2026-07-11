"""Custom JSON-configured source — metadata catalog only.

Remote HTTP download was removed. Use Media Collector to acquire media and
upload via POST /api/v1/assets/takes/upload (or MinIO takes/).
"""

from __future__ import annotations

import json
import os

from contentos_sources.domain.source_candidate import SourceAsset, SourceCandidate, SourceHealth
from contentos_sources.domain.source_query import SourceQuery


class CustomSource:
    source_id = "custom"

    def _entries(self) -> list[dict]:
        raw = os.getenv("CONTENT_SOURCE_CUSTOM_JSON", "[]")
        try:
            data = json.loads(raw)
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []

    async def search(self, query: SourceQuery) -> list[SourceCandidate]:
        terms = [t.lower() for t in query.tags + [query.visual_hint, query.topic, query.scene_label] if t]
        candidates: list[SourceCandidate] = []
        for entry in self._entries():
            title = str(entry.get("title", ""))
            cid = str(entry.get("id", title))
            hay = f"{title} {entry.get('tags', [])}".lower()
            score = 0.5
            if terms:
                hits = sum(1 for t in terms if t in hay)
                score = min(1.0, hits / len(terms))
            candidates.append(
                SourceCandidate(
                    source_id=self.source_id,
                    candidate_id=cid,
                    title=title,
                    score=score,
                    reason="Custom source entry (catalog only — download via Media Collector)",
                    metadata=entry,
                )
            )
        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates[:10]

    async def fetch(self, candidate_id: str) -> SourceAsset:
        raise NotImplementedError(
            "External media download was moved to Media Collector. "
            f"Upload asset '{candidate_id}' via POST /api/v1/assets/takes/upload."
        )

    async def health(self) -> SourceHealth:
        entries = self._entries()
        return SourceHealth(self.source_id, True, f"{len(entries)} custom catalog entries (no remote download)")
