"""V5.0.4 — TakeRecommendationService multi-signal ranking."""

from __future__ import annotations

from uuid import uuid4

import pytest
from contentos_database.models import Asset
from contentos_intelligence.application.noop import NoOpEmbeddingClient
from contentos_intelligence.application.take_recommendation.scoring import (
    score_duration_fit,
    score_media_fields,
    score_motion_fit,
    score_quality,
    score_semantic,
    score_tokens,
)
from contentos_intelligence.application.take_recommendation.service import TakeRecommendationService
from contentos_intelligence.domain.take_recommendation import SceneTakeQuery
from contentos_shared.enums import AssetCategory


def _asset(
    *,
    object_key: str,
    scene_label: str | None = None,
    tags: list[str] | None = None,
    metadata: dict | None = None,
    size_bytes: int = 2_000_000,
) -> Asset:
    meta = dict(metadata or {})
    if scene_label:
        meta.setdefault("scene_label", scene_label)
    return Asset(
        id=uuid4(),
        category=AssetCategory.TAKES.value,
        bucket="contentos",
        object_key=object_key,
        content_type="video/mp4",
        size_bytes=size_bytes,
        sha256="a" * 64,
        tags=tags or [],
        metadata_=meta,
    )


def test_score_tokens_matches_query():
    points, reason = score_tokens({"beach", "gta"}, "gta 6 beach sunset cars")
    assert points > 0
    assert reason and "beach" in reason


def test_score_media_fields_scenario():
    points, reasons = score_media_fields({"night", "city"}, {"scenario": "city night skyline"})
    assert points >= 12
    assert "media:scenario" in reasons


def test_score_quality_and_duration():
    quality_points, _ = score_quality(6_000_000, {"width": 1920})
    assert quality_points >= 15
    duration_points, reason = score_duration_fit(10.0, {"duration_seconds": 12.0})
    assert duration_points > 0
    assert reason and "duration" in reason


def test_score_motion_fit():
    points, reason = score_motion_fit("pan-left", {"motion": "slow pan-left"})
    assert points == 8.0
    assert reason == "motion-fit"


def test_score_semantic_weight():
    points, reason = score_semantic(0.75)
    assert points > 0
    assert reason and "semantic" in reason


@pytest.mark.asyncio
async def test_rank_scene_prefers_scene_label():
    service = TakeRecommendationService(embedding_client=NoOpEmbeddingClient())
    beach = _asset(object_key="takes/beach.mp4", scene_label="beach", tags=["beach"])
    city = _asset(object_key="takes/city.mp4", scene_label="city", tags=["city"])
    query = SceneTakeQuery(topic="GTA 6", scene_label="beach", scene={"visual_hint": "GTA 6 beach"})
    ranked = await service.rank_scene(query, [city, beach])
    assert ranked[0].asset_key == "takes/beach.mp4"
    assert ranked[0].score > ranked[1].score


@pytest.mark.asyncio
async def test_rank_scene_collected_bonus():
    service = TakeRecommendationService(embedding_client=NoOpEmbeddingClient())
    asset = _asset(object_key="takes/collected.mp4", scene_label="chase")
    query = SceneTakeQuery(topic="GTA 6", scene_label="chase", scene={})
    ranked = await service.rank_scene(
        query,
        [asset],
        collected_match={"asset_key": "takes/collected.mp4"},
    )
    assert ranked[0].asset_key == "takes/collected.mp4"
    assert "collected" in ranked[0].reasons


@pytest.mark.asyncio
async def test_recommend_scenes_avoids_reuse():
    service = TakeRecommendationService(embedding_client=NoOpEmbeddingClient())
    shared = _asset(object_key="takes/shared.mp4", scene_label="intro")
    alt = _asset(object_key="takes/alt.mp4", scene_label="outro")
    matches = await service.recommend_scenes(
        topic="GTA 6",
        scenes=[
            {"label": "intro", "visual_hint": "intro"},
            {"label": "outro", "visual_hint": "outro"},
        ],
        assets=[shared, alt],
    )
    assert len(matches) == 2
    first_key = matches[0]["selected"]["asset_key"]
    second_key = matches[1]["selected"]["asset_key"]
    assert first_key != second_key or second_key == "takes/alt.mp4"


@pytest.mark.asyncio
async def test_recommend_scenes_fallback_to_collected(monkeypatch):
    service = TakeRecommendationService(embedding_client=NoOpEmbeddingClient())
    matches = await service.recommend_scenes(
        topic="GTA 6",
        scenes=[{"label": "beach"}],
        assets=[],
        collected=[
            {
                "scene_label": "beach",
                "asset_key": "manifest/beach.mp4",
                "bucket": "contentos",
                "content_type": "video/mp4",
            }
        ],
    )
    assert matches[0]["selected"]["asset_key"] == "manifest/beach.mp4"
    assert "manifest order" in matches[0]["selected"]["reasons"]


@pytest.mark.asyncio
async def test_semantic_scoring_with_embeddings(monkeypatch):
    class FakeEmbed:
        async def embed(self, texts):
            if "beach" in texts[0].lower():
                return [[1.0, 0.0]]
            return [[]]

    beach = _asset(object_key="takes/beach.mp4", scene_label="beach")
    city = _asset(object_key="takes/city.mp4", scene_label="city")
    asset_id = str(beach.id)
    service = TakeRecommendationService(embedding_client=FakeEmbed())
    query = SceneTakeQuery(topic="GTA 6", scene_label="beach", scene={"visual_hint": "beach"})
    ranked = await service.rank_scene(
        query,
        [city, beach],
        embeddings={asset_id: [0.95, 0.05]},
    )
    assert ranked[0].asset_key == "takes/beach.mp4"
    assert any("semantic" in reason for reason in ranked[0].reasons)
