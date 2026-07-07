"""Semantic search over indexed assets via media embeddings (V5.0.6)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from contentos_database.models import Asset, AssetMediaProfile
from contentos_storage.domain.media_analysis import analysis_summary_text
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contentos_intelligence.application.similarity import cosine_similarity, text_overlap_score
from contentos_intelligence.domain.interfaces import IEmbeddingClient
from contentos_intelligence.infrastructure.embedding_client import get_gateway_embedding_client


@dataclass(frozen=True)
class AssetSemanticHit:
    asset: Asset
    similarity: float
    match_type: str
    analysis: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "similarity": round(self.similarity, 4),
            "match_type": self.match_type,
            "analysis": self.analysis,
        }


class AssetSemanticSearch:
    """Rank assets by embedding cosine similarity with text fallback."""

    def __init__(
        self,
        db: AsyncSession,
        embedding_client: IEmbeddingClient | None = None,
    ) -> None:
        self._db = db
        self._embed = embedding_client or get_gateway_embedding_client()

    @property
    def enabled(self) -> bool:
        return os.getenv("ENABLE_ASSET_SEMANTIC_SEARCH", "true").lower() in ("1", "true", "yes")

    async def search(
        self,
        query: str,
        *,
        category: str | None = None,
        limit: int = 50,
        min_similarity: float | None = None,
        candidate_limit: int | None = None,
    ) -> list[AssetSemanticHit]:
        stripped = (query or "").strip()
        if not stripped:
            return []

        min_sim = (
            float(min_similarity)
            if min_similarity is not None
            else float(os.getenv("ASSET_SEMANTIC_MIN_SIMILARITY", "0.12"))
        )
        max_candidates = candidate_limit or int(os.getenv("ASSET_SEMANTIC_CANDIDATE_LIMIT", "500"))

        stmt = (
            select(Asset, AssetMediaProfile)
            .outerjoin(AssetMediaProfile, AssetMediaProfile.asset_id == Asset.id)
            .order_by(Asset.created_at.desc())
            .limit(max_candidates)
        )
        if category:
            stmt = stmt.where(Asset.category == category)

        rows = await self._db.execute(stmt)
        candidates = list(rows.all())
        if not candidates:
            return []

        query_vector: list[float] = []
        if self.enabled:
            vectors = await self._embed.embed([stripped])
            query_vector = vectors[0] if vectors else []

        scored: list[AssetSemanticHit] = []
        for asset, profile in candidates:
            embedding = list(profile.embedding) if profile and profile.embedding else None
            analysis = dict(profile.analysis) if profile and profile.analysis else None
            haystack = _asset_search_text(asset, analysis)

            if query_vector and embedding:
                score = cosine_similarity(query_vector, embedding)
                match_type = "embedding"
            else:
                score = text_overlap_score(stripped, haystack)
                match_type = "text"

            if score < min_sim:
                continue
            scored.append(
                AssetSemanticHit(
                    asset=asset,
                    similarity=score,
                    match_type=match_type,
                    analysis=analysis,
                )
            )

        scored.sort(key=lambda hit: hit.similarity, reverse=True)
        return scored[:limit]


def _asset_search_text(asset: Asset, analysis: dict[str, Any] | None) -> str:
    meta = asset.metadata_ or {}
    media = analysis or (
        meta.get("media_analysis") if isinstance(meta.get("media_analysis"), dict) else {}
    )
    topic = str(meta.get("theme") or meta.get("game") or "")
    parts = [
        asset.object_key or "",
        asset.content_type or "",
        " ".join(str(t) for t in (asset.tags or [])),
        analysis_summary_text(media, topic=topic),
        " ".join(str(v) for v in meta.values() if isinstance(v, (str, int, float))),
    ]
    return " ".join(p for p in parts if p).lower()
