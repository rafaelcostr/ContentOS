"""Pexels video API — royalty-free stock footage (V5.0)."""

from __future__ import annotations

import os
import time

import httpx
from contentos_sources.application.download_pipeline import DownloadPipeline
from contentos_sources.application.query_scoring import query_terms, relevance_score
from contentos_sources.domain.media_license import ROYALTY_FREE, is_license_allowed
from contentos_sources.domain.source_candidate import SourceAsset, SourceCandidate, SourceHealth
from contentos_sources.domain.source_query import SourceQuery

_API = "https://api.pexels.com/videos"


class PexelsSource:
    source_id = "pexels"

    def _api_key(self) -> str:
        return os.getenv("PEXELS_API_KEY", "").strip()

    def _headers(self) -> dict[str, str]:
        return {"Authorization": self._api_key()}

    def _per_page(self) -> int:
        return max(1, min(30, int(os.getenv("MEDIA_SEARCH_PER_PAGE", "8"))))

    async def search(self, query: SourceQuery) -> list[SourceCandidate]:
        key = self._api_key()
        if not key:
            return []
        terms = query_terms(query)
        q = " ".join(terms[:8]) or query.topic or query.scene_description or "nature"
        params: dict[str, str | int] = {
            "query": q,
            "per_page": self._per_page(),
            "orientation": "portrait",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{_API}/search", headers=self._headers(), params=params)
            resp.raise_for_status()
            payload = resp.json()

        candidates: list[SourceCandidate] = []
        for video in payload.get("videos") or []:
            vid = video.get("id")
            if vid is None:
                continue
            user = video.get("user") or {}
            photographer = user.get("name", "Pexels")
            tags = " ".join(str(video.get(k, "")) for k in ("url",))
            hay = f"{q} {photographer} {tags}"
            score = relevance_score(hay, terms)
            duration = float(video.get("duration") or 0)
            if query.duration_needed and duration and duration < query.duration_needed * 0.5:
                score *= 0.7
            candidates.append(
                SourceCandidate(
                    source_id=self.source_id,
                    candidate_id=str(vid),
                    title=f"Pexels #{vid}",
                    score=score,
                    reason="Pexels portrait video",
                    duration_seconds=duration or None,
                    metadata={
                        "license_type": ROYALTY_FREE,
                        "attribution": photographer,
                        "source_url": video.get("url"),
                        "preview_url": video.get("image"),
                        "provider": "pexels",
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
            raise ValueError("PEXELS_API_KEY not configured")
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{_API}/videos/{candidate_id}", headers=self._headers())
            resp.raise_for_status()
            video = resp.json()

        url = _best_pexels_file(video.get("video_files") or [])
        if not url:
            raise ValueError(f"No downloadable file for Pexels video {candidate_id}")

        pipeline = DownloadPipeline()
        data, content_type = await pipeline.download(url)
        user = video.get("user") or {}
        return SourceAsset(
            source_id=self.source_id,
            candidate_id=candidate_id,
            data=data,
            filename=f"pexels_{candidate_id}.mp4",
            content_type=content_type if "video" in content_type else "video/mp4",
            metadata={
                "license_type": ROYALTY_FREE,
                "attribution": user.get("name", "Pexels"),
                "source_url": video.get("url"),
                "provider": "pexels",
                "download_url": url,
            },
            sha256=pipeline.sha256(data),
        )

    async def health(self) -> SourceHealth:
        key = self._api_key()
        if not key:
            return SourceHealth(self.source_id, False, "PEXELS_API_KEY not set")
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{_API}/search",
                    headers=self._headers(),
                    params={"query": "test", "per_page": 1},
                )
                ok = resp.status_code == 200
            latency = int((time.perf_counter() - started) * 1000)
            return SourceHealth(
                self.source_id,
                ok,
                "Pexels API reachable" if ok else f"HTTP {resp.status_code}",
                latency_ms=latency,
            )
        except Exception as exc:
            return SourceHealth(self.source_id, False, str(exc))


def _best_pexels_file(files: list[dict]) -> str | None:
    """Prefer vertical HD MP4."""
    mp4s = [f for f in files if str(f.get("file_type", "")).startswith("video/mp4")]
    if not mp4s:
        mp4s = files
    if not mp4s:
        return None

    def rank(f: dict) -> tuple[int, int]:
        w = int(f.get("width") or 0)
        h = int(f.get("height") or 0)
        vertical = 1 if h > w else 0
        return (vertical, h)

    best = max(mp4s, key=rank)
    return str(best.get("link") or "")
