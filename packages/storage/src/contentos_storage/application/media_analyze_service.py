"""Media analyze service — vision tags + embeddings for video assets (V5.0.3)."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from uuid import UUID

import httpx
from contentos_database.models import Asset
from contentos_shared.enums import AssetCategory
from contentos_shared.schemas.asset import AssetRef
from contentos_storage.domain.asset_metadata import facet_tags
from contentos_storage.domain.media_analysis import (
    analysis_summary_text,
    analysis_to_metadata,
    merge_vision_results,
    normalize_media_analysis,
)
from contentos_storage.infrastructure.frame_extractor import extract_frame_jpegs
from contentos_storage.infrastructure.pg_asset_repository import PgAssetRepository
from contentos_storage.infrastructure.pg_media_profile_repository import PgAssetMediaProfileRepository


@dataclass
class MediaAnalyzeResult:
    asset_id: str
    analyzed: bool
    skipped: bool = False
    reason: str = ""


class MediaAnalyzeService:
    def __init__(
        self,
        asset_manager,
        *,
        database_url: str | None = None,
        gateway_url: str | None = None,
    ) -> None:
        self.asset_manager = asset_manager
        self.database_url = database_url or os.getenv("DATABASE_URL", "")
        self.gateway_url = (gateway_url or os.getenv("AI_GATEWAY_URL", "http://ai-gateway:8020")).rstrip("/")
        self.asset_repo = PgAssetRepository(database_url=self.database_url)
        self.profile_repo = PgAssetMediaProfileRepository(database_url=self.database_url)
        self.vision_provider = os.getenv("MEDIA_VISION_PROVIDER", os.getenv("VISION_PROVIDER", "ollama"))
        self.vision_model = os.getenv("MEDIA_VISION_MODEL", os.getenv("OLLAMA_VISION_MODEL", ""))
        self.embed_provider = os.getenv("MEDIA_EMBED_PROVIDER", os.getenv("KNOWLEDGE_EMBED_PROVIDER", "ollama"))
        self.embed_model = os.getenv("MEDIA_EMBED_MODEL", os.getenv("KNOWLEDGE_EMBED_MODEL", ""))
        self.max_frames = max(1, min(5, int(os.getenv("MEDIA_ANALYZE_MAX_FRAMES", "2"))))

    async def analyze_asset_ids(
        self,
        asset_ids: list[str],
        *,
        pipeline_id: UUID | None,
        project_id: UUID | None,
        topic: str = "",
        vision_prompt: str | None = None,
    ) -> list[MediaAnalyzeResult]:
        results: list[MediaAnalyzeResult] = []
        reanalyze = os.getenv("MEDIA_REANALYZE", "").lower() in ("1", "true", "yes")
        prompt = vision_prompt or _default_vision_prompt()

        for raw_id in asset_ids:
            try:
                asset_id = UUID(raw_id)
            except ValueError:
                results.append(MediaAnalyzeResult(asset_id=raw_id, analyzed=False, reason="invalid id"))
                continue

            asset = self.asset_repo.get_sync(asset_id)
            if not asset:
                results.append(MediaAnalyzeResult(asset_id=raw_id, analyzed=False, reason="not found"))
                continue
            if asset.category != AssetCategory.TAKES.value and not str(asset.content_type or "").startswith("video"):
                results.append(MediaAnalyzeResult(asset_id=raw_id, analyzed=False, skipped=True, reason="not video"))
                continue
            if not reanalyze and self.profile_repo.get_by_asset_id(asset_id):
                results.append(MediaAnalyzeResult(asset_id=raw_id, analyzed=False, skipped=True, reason="cached"))
                continue

            try:
                video_bytes = await self.asset_manager.get(self._ref_from_asset(asset))
                frames = await extract_frame_jpegs(video_bytes, max_frames=self.max_frames)
                if not frames:
                    results.append(MediaAnalyzeResult(asset_id=raw_id, analyzed=False, reason="no frames"))
                    continue

                vision_chunks: list[dict] = []
                for frame in frames:
                    parsed = await self._vision_analyze(frame, prompt)
                    if parsed:
                        vision_chunks.append(parsed)
                analysis = merge_vision_results(vision_chunks) if vision_chunks else {}
                if not analysis:
                    results.append(MediaAnalyzeResult(asset_id=raw_id, analyzed=False, reason="vision empty"))
                    continue

                summary = analysis_summary_text(analysis, topic=topic)
                embedding = await self._embed(summary)
                self._persist(asset, pipeline_id, project_id, analysis, embedding)
                results.append(MediaAnalyzeResult(asset_id=raw_id, analyzed=True))
            except Exception as exc:
                results.append(MediaAnalyzeResult(asset_id=raw_id, analyzed=False, reason=str(exc)[:200]))
        return results

    async def _vision_analyze(self, jpeg_bytes: bytes, prompt: str) -> dict:
        async with httpx.AsyncClient(timeout=120.0) as client:
            data = {
                "prompt": prompt,
                "provider": self.vision_provider,
                "agent": "media_analyze",
            }
            if self.vision_model:
                data["model"] = self.vision_model
            response = await client.post(
                f"{self.gateway_url}/v1/vision/analyze",
                data=data,
                files={"file": ("frame.jpg", jpeg_bytes, "image/jpeg")},
            )
            response.raise_for_status()
            payload = response.json()
        return _parse_vision_payload(payload)

    async def _embed(self, text: str) -> list[float]:
        if not text.strip():
            return []
        async with httpx.AsyncClient(timeout=120.0) as client:
            body: dict = {"provider": self.embed_provider, "text": text, "agent": "media_analyze"}
            if self.embed_model:
                body["model"] = self.embed_model
            response = await client.post(f"{self.gateway_url}/v1/embeddings", json=body)
            response.raise_for_status()
            return list(response.json().get("embedding") or [])

    def _persist(
        self,
        asset: Asset,
        pipeline_id: UUID | None,
        project_id: UUID | None,
        analysis: dict,
        embedding: list[float],
    ) -> None:
        facet_meta = analysis_to_metadata(analysis)
        merged = dict(asset.metadata_ or {})
        merged.update(facet_meta)
        merged["has_embedding"] = bool(embedding)
        tags = list(asset.tags or [])
        for tag in facet_tags(facet_meta):
            if tag not in tags:
                tags.append(tag)
        if "media_analyzed" not in tags:
            tags.append("media_analyzed")
        asset.metadata_ = merged
        asset.tags = tags
        self.asset_repo.save_sync(asset)
        self.profile_repo.upsert(
            asset_id=asset.id,
            pipeline_id=pipeline_id,
            project_id=project_id,
            analysis=analysis,
            embedding=embedding,
            embedding_model=self.embed_model or self.embed_provider,
            vision_model=self.vision_model or self.vision_provider,
        )

    @staticmethod
    def _ref_from_asset(asset: Asset) -> AssetRef:
        return AssetRef(
            id=asset.id,
            category=AssetCategory(asset.category),
            key=asset.object_key,
            bucket=asset.bucket,
            content_type=asset.content_type,
            size_bytes=asset.size_bytes,
        )


def _default_vision_prompt() -> str:
    return (
        "Analyze this video frame for short-form B-roll editing. "
        "Return ONLY valid JSON with keys: objects[], characters[], vehicles[], colors[], "
        "scenario, motion, speed, time_of_day, angle, emotion, camera_type."
    )


def _parse_vision_payload(payload: dict) -> dict:
    if isinstance(payload.get("analysis"), dict):
        return normalize_media_analysis(payload["analysis"])
    for key in ("result", "content", "text", "response"):
        value = payload.get(key)
        if isinstance(value, dict):
            return normalize_media_analysis(value)
        if isinstance(value, str):
            parsed = _extract_json(value)
            if parsed:
                return normalize_media_analysis(parsed)
    if isinstance(payload.get("objects"), list) or payload.get("scenario"):
        return normalize_media_analysis(payload)
    return {}


def _extract_json(text: str) -> dict | None:
    text = text.strip()
    if text.startswith("{"):
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            pass
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None
