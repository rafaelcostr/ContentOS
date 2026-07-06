"""Custom JSON-configured source."""

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
                    reason="Custom source entry",
                    metadata=entry,
                )
            )
        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates[:10]

    async def fetch(self, candidate_id: str) -> SourceAsset:
        for entry in self._entries():
            if str(entry.get("id", entry.get("title"))) == candidate_id:
                url = entry.get("url", "")
                if url:
                    import httpx

                    async with httpx.AsyncClient(timeout=60.0) as client:
                        resp = await client.get(url)
                        resp.raise_for_status()
                        import hashlib

                        data = resp.content
                        return SourceAsset(
                            source_id=self.source_id,
                            candidate_id=candidate_id,
                            data=data,
                            filename=entry.get("filename", "custom_clip.mp4"),
                            content_type=resp.headers.get("content-type", "video/mp4"),
                            metadata=entry,
                            sha256=hashlib.sha256(data).hexdigest(),
                        )
        raise ValueError(f"Custom source entry '{candidate_id}' not found")

    async def health(self) -> SourceHealth:
        entries = self._entries()
        return SourceHealth(self.source_id, True, f"{len(entries)} custom entries configured")
