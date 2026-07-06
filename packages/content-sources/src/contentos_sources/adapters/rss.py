"""RSS feed content source (metadata search)."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET

import httpx
from contentos_sources.domain.source_candidate import SourceAsset, SourceCandidate, SourceHealth
from contentos_sources.domain.source_query import SourceQuery


class RSSSource:
    source_id = "rss"

    def _feed_url(self) -> str:
        return os.getenv("CONTENT_SOURCE_RSS_URL", "")

    async def search(self, query: SourceQuery) -> list[SourceCandidate]:
        url = self._feed_url()
        if not url:
            return []
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                root = ET.fromstring(resp.text)
        except Exception:
            return []

        terms = [t.lower() for t in query.tags + [query.visual_hint, query.topic] if t]
        candidates: list[SourceCandidate] = []
        for item in root.findall(".//item")[:20]:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            desc = (item.findtext("description") or "").strip()
            hay = f"{title} {desc}".lower()
            score = 0.4
            if terms:
                hits = sum(1 for t in terms if t in hay)
                score = min(1.0, 0.3 + hits / len(terms))
            candidates.append(
                SourceCandidate(
                    source_id=self.source_id,
                    candidate_id=link or title,
                    title=title,
                    score=score,
                    reason="RSS feed item",
                    metadata={"link": link, "description": desc[:200]},
                )
            )
        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates[:5]

    async def fetch(self, candidate_id: str) -> SourceAsset:
        # RSS items are references — store metadata JSON as placeholder asset
        import json

        payload = json.dumps({"rss_url": candidate_id, "note": "RSS reference — fetch media separately"}).encode()
        return SourceAsset(
            source_id=self.source_id,
            candidate_id=candidate_id,
            data=payload,
            content_type="application/json",
            filename="rss_ref.json",
            metadata={"link": candidate_id},
        )

    async def health(self) -> SourceHealth:
        url = self._feed_url()
        if not url:
            return SourceHealth(self.source_id, False, "CONTENT_SOURCE_RSS_URL not set")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.head(url)
                ok = resp.status_code < 400
                return SourceHealth(self.source_id, ok, f"HTTP {resp.status_code}")
        except Exception as exc:
            return SourceHealth(self.source_id, False, str(exc))
