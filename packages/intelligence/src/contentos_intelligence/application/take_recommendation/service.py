"""Recommend best video takes per scene using multi-signal scoring (V5.0.4)."""

from __future__ import annotations

import os
from typing import Any

from contentos_intelligence.application.similarity import cosine_similarity
from contentos_intelligence.application.take_recommendation.scoring import (
    asset_text,
    query_tokens,
    score_duration_fit,
    score_media_fields,
    score_motion_fit,
    score_quality,
    score_semantic,
    score_tokens,
)
from contentos_intelligence.domain.take_recommendation import SceneTakeQuery, TakeRankResult
from contentos_intelligence.infrastructure.asset_media_profile_repository import load_embeddings_by_asset_ids
from contentos_intelligence.infrastructure.embedding_client import get_gateway_embedding_client


class TakeRecommendationService:
    """Rank assets for a scene using tokens, media tags, quality, duration and embeddings."""

    def __init__(self, *, database_url: str | None = None, embedding_client=None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL", "")
        self._embed = embedding_client or get_gateway_embedding_client()

    @property
    def enabled(self) -> bool:
        return os.getenv("ENABLE_TAKE_RECOMMENDATION", "true").lower() in ("1", "true", "yes")

    async def rank_scene(
        self,
        query: SceneTakeQuery,
        assets: list[Any],
        *,
        collected_match: dict | None = None,
        used_asset_keys: set[str] | None = None,
        embeddings: dict[str, list[float]] | None = None,
    ) -> list[TakeRankResult]:
        if not assets:
            return []

        tokens = query_tokens(
            query.topic,
            query.scene_label,
            query.scene.get("visual_hint"),
            query.scene.get("description"),
            query.scene.get("text"),
            query.scene.get("theme"),
            query.scene.get("game"),
            query.scene.get("character"),
            query.scene.get("motion"),
            query.scene.get("emotion"),
        )
        collected_key = collected_match.get("asset_key") if collected_match else None
        used = used_asset_keys or set()

        asset_ids = [a.id for a in assets if getattr(a, "id", None)]
        embedding_map = embeddings if embeddings is not None else load_embeddings_by_asset_ids(
            asset_ids, database_url=self.database_url
        )
        scene_vector: list[float] = []
        if self.enabled and embedding_map:
            vectors = await self._embed.embed([query.search_text])
            scene_vector = vectors[0] if vectors else []

        ranked: list[TakeRankResult] = []
        for asset in assets:
            meta = getattr(asset, "metadata_", None) or {}
            tags = list(getattr(asset, "tags", None) or [])
            tag_set = {str(t).lower() for t in tags}
            content_type = str(getattr(asset, "content_type", "") or "")
            object_key = str(getattr(asset, "object_key", "") or "")
            bucket = str(getattr(asset, "bucket", "contentos") or "contentos")
            size_bytes = int(getattr(asset, "size_bytes", 0) or 0)
            asset_id = str(asset.id) if getattr(asset, "id", None) else None

            score = 0.0
            reasons: list[str] = []

            if content_type.startswith("video/"):
                score += 10
                reasons.append("video")

            if collected_key and object_key == collected_key:
                score += 50
                reasons.append("collected")

            asset_label = str(meta.get("scene_label") or meta.get("label") or "").lower()
            if asset_label and asset_label == query.scene_label.lower():
                score += 80
                reasons.append("scene label")
            if query.scene_label.lower() in tag_set:
                score += 25
                reasons.append("tag label")

            text = asset_text(meta, tags, object_key, content_type)
            token_points, token_reason = score_tokens(tokens, text)
            if token_points:
                score += token_points
                if token_reason:
                    reasons.append(token_reason)

            if "media_analyzed" in tag_set:
                score += 8
                reasons.append("media analyzed")

            media_points, media_reasons = score_media_fields(tokens, meta)
            score += media_points
            reasons.extend(media_reasons)

            quality_points, quality_reason = score_quality(size_bytes, meta)
            if quality_points:
                score += quality_points
                if quality_reason:
                    reasons.append(quality_reason)

            duration_points, duration_reason = score_duration_fit(query.duration_needed, meta)
            if duration_points:
                score += duration_points
                if duration_reason:
                    reasons.append(duration_reason)

            motion_points, motion_reason = score_motion_fit(
                str(query.scene.get("motion") or ""),
                meta,
            )
            if motion_points:
                score += motion_points
                if motion_reason:
                    reasons.append(motion_reason)

            if asset_id and scene_vector and asset_id in embedding_map:
                sem_points, sem_reason = score_semantic(
                    cosine_similarity(scene_vector, embedding_map[asset_id])
                )
                if sem_points:
                    score += sem_points
                    if sem_reason:
                        reasons.append(sem_reason)

            if object_key and object_key in used:
                score -= float(os.getenv("TAKE_REUSE_PENALTY", "25"))
                reasons.append("reuse penalty")

            if score > 0:
                ranked.append(
                    TakeRankResult(
                        asset_id=asset_id,
                        asset_key=object_key,
                        bucket=bucket,
                        content_type=content_type,
                        score=score,
                        reasons=tuple(reasons),
                        metadata=meta,
                    )
                )

        return sorted(ranked, key=lambda item: item.score, reverse=True)

    async def recommend_scenes(
        self,
        *,
        topic: str,
        scenes: list[dict[str, Any]],
        assets: list[Any],
        collected: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        if not scenes:
            scenes = [{"label": "main", "visual_hint": topic}]

        collected_by_label = {str(item.get("scene_label") or ""): item for item in (collected or [])}
        used_keys: set[str] = set()
        matches: list[dict[str, Any]] = []

        asset_ids = [a.id for a in assets if getattr(a, "id", None)]
        embedding_map = load_embeddings_by_asset_ids(asset_ids, database_url=self.database_url)

        for index, scene in enumerate(scenes):
            label = str(scene.get("label") or scene.get("scene_label") or f"scene_{index}")
            query = SceneTakeQuery(
                topic=topic,
                scene_label=label,
                scene=scene,
                duration_needed=_duration(scene),
            )
            ranked = await self.rank_scene(
                query,
                assets,
                collected_match=collected_by_label.get(label),
                used_asset_keys=used_keys,
                embeddings=embedding_map,
            )
            if not ranked and collected and index < len(collected):
                item = collected[index]
                ranked = [
                    TakeRankResult(
                        asset_id=str(item.get("asset_id")) if item.get("asset_id") else None,
                        asset_key=str(item.get("asset_key") or ""),
                        bucket=str(item.get("bucket") or "contentos"),
                        content_type=str(item.get("content_type") or "video/mp4"),
                        score=40.0,
                        reasons=("manifest order",),
                        metadata={"scene_label": label},
                    )
                ]

            candidates = [r.to_dict() for r in ranked[:3]]
            if candidates and candidates[0].get("asset_key"):
                used_keys.add(str(candidates[0]["asset_key"]))

            matches.append(
                {
                    "scene_label": label,
                    "scene_index": index,
                    "selected": candidates[0] if candidates else None,
                    "candidates": candidates,
                }
            )
        return matches


def _duration(scene: dict[str, Any]) -> float | None:
    for key in ("duration_seconds", "duration"):
        raw = scene.get(key)
        if raw is None:
            continue
        try:
            return float(raw)
        except (TypeError, ValueError):
            continue
    return None
