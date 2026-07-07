"""V5.0.6 — semantic asset search via media embeddings."""

from __future__ import annotations

from uuid import uuid4

import pytest
from contentos_database.models import Asset, AssetMediaProfile
from contentos_intelligence.application.asset_semantic_search import AssetSemanticSearch, _asset_search_text
from contentos_intelligence.application.noop import NoOpEmbeddingClient
from contentos_shared.enums import AssetCategory


class FakeSession:
    def __init__(self, rows):
        self._rows = rows

    async def execute(self, _stmt):
        class Result:
            def __init__(self, data):
                self._data = data

            def all(self):
                return self._data

        return Result(self._rows)


class FakeEmbed:
    async def embed(self, texts):
        if "beach" in texts[0].lower():
            return [[1.0, 0.0, 0.0]]
        return [[0.0, 1.0, 0.0]]


def _asset(*, key: str, theme: str = "GTA 6", tags: list[str] | None = None) -> Asset:
    return Asset(
        id=uuid4(),
        category=AssetCategory.TAKES.value,
        bucket="contentos",
        object_key=key,
        content_type="video/mp4",
        size_bytes=1_000_000,
        sha256="c" * 64,
        tags=tags or [theme],
        metadata_={"theme": theme, "game": theme},
    )


def test_asset_search_text_includes_analysis():
    asset = _asset(key="takes/beach.mp4")
    text = _asset_search_text(
        asset,
        {"scenario": "beach sunset", "objects": ["car", "palm"]},
    )
    assert "beach" in text
    assert "sunset" in text


@pytest.mark.asyncio
async def test_semantic_search_embedding_ranking():
    beach = _asset(key="takes/beach.mp4", tags=["beach"])
    city = _asset(key="takes/city.mp4", tags=["city"])
    beach_profile = AssetMediaProfile(
        id=uuid4(),
        asset_id=beach.id,
        embedding=[1.0, 0.0, 0.0],
        analysis={"scenario": "beach sunset"},
    )
    city_profile = AssetMediaProfile(
        id=uuid4(),
        asset_id=city.id,
        embedding=[0.0, 1.0, 0.0],
        analysis={"scenario": "city night"},
    )
    session = FakeSession([(beach, beach_profile), (city, city_profile)])
    searcher = AssetSemanticSearch(session, embedding_client=FakeEmbed())
    hits = await searcher.search("GTA 6 beach sunset", min_similarity=0.0)
    assert hits[0].asset.object_key == "takes/beach.mp4"
    assert hits[0].match_type == "embedding"
    assert hits[0].similarity > hits[1].similarity


@pytest.mark.asyncio
async def test_semantic_search_text_fallback():
    asset = _asset(key="takes/chase.mp4", theme="GTA 6")
    asset.metadata_ = {
        **(asset.metadata_ or {}),
        "objects": ["car chase city night"],
        "motion": "fast",
    }
    session = FakeSession([(asset, None)])
    searcher = AssetSemanticSearch(session, embedding_client=NoOpEmbeddingClient())
    hits = await searcher.search("car chase night", min_similarity=0.1)
    assert len(hits) == 1
    assert hits[0].match_type == "text"
    assert hits[0].similarity > 0


@pytest.mark.asyncio
async def test_semantic_search_empty_query():
    session = FakeSession([])
    searcher = AssetSemanticSearch(session)
    assert await searcher.search("   ") == []


@pytest.mark.asyncio
async def test_semantic_search_respects_limit():
    rows = []
    for i in range(5):
        asset = _asset(key=f"takes/a{i}.mp4")
        profile = AssetMediaProfile(
            id=uuid4(),
            asset_id=asset.id,
            embedding=[1.0, float(i) * 0.1, 0.0],
            analysis={"scenario": f"scene {i}"},
        )
        rows.append((asset, profile))
    session = FakeSession(rows)
    searcher = AssetSemanticSearch(session, embedding_client=FakeEmbed())
    hits = await searcher.search("beach", limit=2, min_similarity=0.0)
    assert len(hits) == 2
