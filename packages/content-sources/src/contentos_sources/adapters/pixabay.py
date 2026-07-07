"""Pixabay video API — royalty-free stock footage (V5.0)."""

from __future__ import annotations

import os
import time

import httpx
from contentos_sources.application.download_pipeline import DownloadPipeline
from contentos_sources.application.query_scoring import query_terms, relevance_score
from contentos_sources.domain.media_license import ROYALTY_FREE, is_license_allowed
from contentos_sources.domain.source_candidate import SourceAsset, SourceCandidate, SourceHealth
from contentos_sources.domain.source_query import SourceQuery

_API = "https://pixabay.com/api/videos/"


class PixabaySource:
    source_id = "pixabay"

    def _api_key(self) -> str:
        return os.getenv("PIXABAY_API_KEY", "").strip()

    def _per_page(self) -> int:
        return max(1, min(30, int(os.getenv("MEDIA_SEARCH_PER_PAGE", "8"))))

    async def search(self, query: SourceQuery) -> list[SourceCandidate]:
        key = self._api_key()
        if not key:
            return []
        terms = query_terms(query)
        q = "+".join(terms[:8]) or (query.topic or "nature").replace(" ", "+")
        params = {
            "key": key,
            "q": q.replace("+", " "),
            "per_page": self._per_page(),
            "video_type": "film",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(_API, params=params)
            resp.raise_for_status()
            payload = resp.json()

        candidates: list[SourceCandidate] = []
        for hit in payload.get("hits") or []:
            vid = hit.get("id")
            if vid is None:
                continue
            tags = str(hit.get("tags") or "")
            score = relevance_score(f"{tags} {q}", terms)
            duration = float(hit.get("duration") or 0)
            if query.duration_needed and duration and duration < query.duration_needed * 0.5:
                score *= 0.7
            candidates.append(
                SourceCandidate(
                    source_id=self.source_id,
                    candidate_id=str(vid),
                    title=f"Pixabay #{vid}",
                    score=score,
                    reason="Pixabay stock video",
                    duration_seconds=duration or None,
                    metadata={
                        "license_type": ROYALTY_FREE,
                        "attribution": "Pixabay",
                        "tags": tags,
                        "source_url": hit.get("pageURL"),
                        "provider": "pixabay",
                    },
                )
            )
        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates[: self._per_page()]

    async def fetch(self, candidate_id: str) -> SourceAsset:
        if not is_license_allowed(ROYALTY_FREE):
            raise ValueError(f"License {ROYALTY_FREE} not in MEDIA_ALLOWED_LICENSES")
        key = self._api_key()
        if not key:
            raise ValueError("PIXABAY_API_KEY not configured")

        params = {"key": key, "id": candidate_id}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(_API, params=params)
            resp.raise_for_status()
            payload = resp.json()

        hits = payload.get("hits") or []
        if not hits:
            raise ValueError(f"Pixabay video {candidate_id} not found")
        hit = hits[0]
        url = _best_pixabay_url(hit.get("videos") or {})
        if not url:
            raise ValueError(f"No downloadable URL for Pixabay {candidate_id}")

        pipeline = DownloadPipeline()
        data, content_type = await pipeline.download(url)
        return SourceAsset(
            source_id=self.source_id,
            candidate_id=candidate_id,
            data=data,
            filename=f"pixabay_{candidate_id}.mp4",
            content_type=content_type if "video" in content_type else "video/mp4",
            metadata={
                "license_type": ROYALTY_FREE,
                "attribution": "Pixabay",
                "tags": hit.get("tags"),
                "source_url": hit.get("pageURL"),
                "provider": "pixabay",
                "download_url": url,
            },
            sha256=pipeline.sha256(data),
        )

    async def health(self) -> SourceHealth:
        key = self._api_key()
        if not key:
            return SourceHealth(self.source_id, False, "PIXABAY_API_KEY not set")
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(_API, params={"key": key, "q": "test", "per_page": 3})
                ok = resp.status_code == 200
            latency = int((time.perf_counter() - started) * 1000)
            return SourceHealth(
                self.source_id,
                ok,
                "Pixabay API reachable" if ok else f"HTTP {resp.status_code}",
                latency_ms=latency,
            )
        except Exception as exc:
            return SourceHealth(self.source_id, False, str(exc))


def _best_pixabay_url(videos: dict) -> str | None:
    for quality in ("large", "medium", "small", "tiny"):
        entry = videos.get(quality) or {}
        url = entry.get("url")
        if url:
            return str(url)
    return None
