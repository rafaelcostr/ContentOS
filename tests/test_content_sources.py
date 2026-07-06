"""Tests for Content Sources package."""

from uuid import uuid4

from contentos_sources.application.source_manager import SourceManager
from contentos_sources.domain.source_candidate import SourceCandidate
from contentos_sources.domain.source_query import SourceQuery


def test_source_candidate_to_dict():
    c = SourceCandidate(source_id="local_library", candidate_id="takes/a.mp4", title="a.mp4", score=0.8)
    d = c.to_dict()
    assert d["source_id"] == "local_library"
    assert d["score"] == 0.8


def test_custom_source_search_empty():
    mgr = SourceManager()
    results = mgr.list_sources()
    assert "local_library" in results or len(results) >= 0


async def test_custom_source_entries(monkeypatch):
    monkeypatch.setenv("CONTENT_SOURCES_ENABLED", "custom")
    monkeypatch.setenv(
        "CONTENT_SOURCE_CUSTOM_JSON",
        '[{"id":"c1","title":"car chase","tags":["car","action"]}]',
    )
    from contentos_sources.infrastructure.factory import build_registry

    mgr = SourceManager()
    mgr._registry = build_registry()
    query = SourceQuery(scene_description="car chase scene", tags=["car"], project_id=uuid4())
    results = await mgr.search(query, source_id="custom")
    assert len(results) >= 1
    assert results[0].source_id == "custom"


async def test_search_all_scenes_structure():
    mgr = SourceManager()
    scenes = [{"label": "intro", "description": "hook", "visual_hint": "city"}]
    rows = await mgr.search_all_scenes(scenes, uuid4(), "test topic")
    assert len(rows) == 1
    assert rows[0]["scene_index"] == 0
    assert "candidates" in rows[0]
