"""clip_research → asset_collector handler chain with mocked Pexels/Pixabay."""

from __future__ import annotations

from uuid import uuid4

import pytest
from contentos_agents.handlers.asset_collector import AssetCollectorAgentHandler
from contentos_agents.handlers.clip_research import ClipResearchAgentHandler
from contentos_shared.schemas.agent import AgentTaskInput


@pytest.mark.asyncio
async def test_clip_research_refined_search_merges_candidates(monkeypatch):
    class FakeCandidate:
        def __init__(self, candidate_id: str) -> None:
            self.candidate_id = candidate_id

        def to_dict(self) -> dict:
            return {"source_id": "pexels", "candidate_id": self.candidate_id, "score": 0.95}

    class FakeMgr:
        def list_sources(self) -> list[str]:
            return ["pexels"]

        async def search_all_scenes(self, scenes, project_id, topic) -> list[dict]:
            return [
                {
                    "scene_index": 0,
                    "scene_label": "hook",
                    "candidates": [FakeCandidate("1001").to_dict()],
                }
            ]

        async def search(self, query) -> list[FakeCandidate]:
            return [FakeCandidate("2002")]

    monkeypatch.setattr("contentos_agents.handlers.clip_research.get_source_manager", lambda: FakeMgr())
    monkeypatch.setattr("contentos_agents.handlers.clip_research.get_collection_store", lambda: None)

    clip = ClipResearchAgentHandler()

    async def fake_chat_json_with_cache(_self, _prompt, **kwargs):
        return (
            {"queries": [{"query": "GTA 6 city skyline night", "visual_hint": "vertical"}]},
            False,
            "cache-key",
        )

    clip.chat_json_with_cache = fake_chat_json_with_cache.__get__(clip, ClipResearchAgentHandler)
    clip.render_prompt = lambda *args, **kwargs: type("P", (), {"version": "test"})()

    scenes = [{"label": "hook", "description": "GTA logo", "duration_seconds": 5}]
    output = await clip.execute(
        AgentTaskInput(
            job_id=uuid4(),
            project_id=uuid4(),
            pipeline_id=uuid4(),
            step="clip_research",
            payload={"topic": "GTA 6", "scenes": scenes},
        )
    )
    assert output.status == "completed"
    candidate_ids = {c["candidate_id"] for c in output.data["scene_candidates"][0]["candidates"]}
    assert candidate_ids == {"1001", "2002"}


@pytest.mark.asyncio
async def test_asset_collector_fetches_pexels_clip(monkeypatch):
    monkeypatch.setenv("MEDIA_COLLECT_TOP_N", "1")
    monkeypatch.setenv("MEDIA_REQUIRE_ASSETS", "false")

    class FakeAsset:
        content_type = "video/mp4"
        filename = "pexels_1001.mp4"
        sha256 = "abc"
        data = b"video-bytes"
        metadata = {"license_type": "royalty_free", "provider": "pexels"}

    class FakeMgr:
        async def fetch(self, source_id: str, candidate_id: str) -> FakeAsset:
            assert source_id == "pexels"
            assert candidate_id == "1001"
            return FakeAsset()

    stored: list[dict] = []

    class FakePersisted:
        def __init__(self) -> None:
            self.ref = type("R", (), {"key": "takes/clip.mp4", "bucket": "contentos", "id": uuid4()})()
            self.asset_id = uuid4()
            self.deduplicated = False

    class FakePipeline:
        async def store_and_persist(self, category, data, meta, **kwargs):
            stored.append({"category": str(category), "size": len(data)})
            return FakePersisted()

    import contentos_agents.handlers.asset_collector as mod

    monkeypatch.setattr(mod, "get_source_manager", lambda: FakeMgr())
    monkeypatch.setattr(mod, "get_asset_manager", lambda _settings: object())
    monkeypatch.setattr(mod, "AssetPipelineService", lambda _am: FakePipeline())
    monkeypatch.setattr(mod, "get_collection_store", lambda: None)

    collector = AssetCollectorAgentHandler()

    output = await collector.execute(
        AgentTaskInput(
            job_id=uuid4(),
            project_id=uuid4(),
            pipeline_id=uuid4(),
            step="asset_collector",
            payload={
                "topic": "GTA 6",
                "scenes": [{"label": "hook", "duration_seconds": 5}],
                "scene_candidates": [
                    {
                        "scene_label": "hook",
                        "candidates": [
                            {
                                "source_id": "pexels",
                                "candidate_id": "1001",
                                "score": 0.9,
                                "metadata": {"license_type": "royalty_free"},
                            }
                        ],
                    }
                ],
            },
        )
    )
    assert output.status == "completed"
    assert output.data["count"] >= 1
    assert stored
