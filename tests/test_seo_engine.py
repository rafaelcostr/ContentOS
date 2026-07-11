"""V5.2.3 — SEO Engine tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from contentos_events.domain.event_types import SEO_OPTIMIZED, STEP_TO_DOMAIN_EVENT
from contentos_intelligence.application.content_score.dimensions import extract_seo
from contentos_intelligence.application.seo import SeoOptimizer
from contentos_shared.enums import PipelineStep


def test_seo_optimizer_generates_metadata():
    payload = {
        "topic": "GTA 6",
        "script": {
            "title": "GTA 6 — tudo que você precisa saber",
            "hook": "Você sabia que GTA 6 vai mudar os jogos?",
            "development": "Mapas, personagens e datas de lançamento.",
            "call_to_action": "Comenta qual cidade você quer explorar!",
        },
        "project_dna": {"brand_keywords": ["gta6", "rockstar", "games"]},
    }
    package = SeoOptimizer().optimize(payload)
    assert package.title
    assert 5 <= len(package.hashtags) <= 12
    assert package.description
    assert package.seo_score > 0
    data = package.to_dict()
    assert "tiktok" in data["platforms"]
    assert "youtube_shorts" in data["platforms"]
    assert data["title_variants"]


def test_extract_seo_prefers_seo_package():
    score, source = extract_seo(
        {
            "seo_package": {"title": "Test", "seo_score": 88.0, "hashtags": ["a", "b", "c", "d", "e"]},
            "multi_content": {"by_format": {"seo_article": {"content": "x"}}},
        }
    )
    assert score == 93.0
    assert source == "seo_package.seo_score"


def test_v5_autopilot_includes_seo_step():
    steps = PipelineStep.v5_media_autopilot_ordered()
    assert len(steps) == 16
    assert steps.index(PipelineStep.SEO) + 1 == steps.index(PipelineStep.CREATIVE_MEMORY)
    assert steps.index(PipelineStep.CREATIVE_MEMORY) + 1 == steps.index(PipelineStep.PUBLISHER)


def test_factory_full_includes_seo_before_publisher():
    steps = PipelineStep.factory_full_ordered()
    assert len(steps) == 29
    assert steps.index(PipelineStep.SEO) + 1 == steps.index(PipelineStep.PUBLISHER)
    assert steps.index(PipelineStep.SEO) > steps.index(PipelineStep.ANALYTICS)


def test_v1_pipeline_unchanged():
    assert len(PipelineStep.ordered()) == 9
    assert PipelineStep.SEO not in PipelineStep.ordered()


def test_seo_domain_event():
    assert STEP_TO_DOMAIN_EVENT["seo"] == SEO_OPTIMIZED


@pytest.mark.asyncio
async def test_seo_agent_handler(monkeypatch):
    from contentos_agents.handlers.seo import SeoAgentHandler
    from contentos_shared.schemas.agent import AgentTaskInput

    handler = SeoAgentHandler()

    async def fake_store(_self, category, data, meta):
        return type("R", (), {"key": "scripts/seo.json", "bucket": "contentos", "id": uuid4()})()

    async def fail_llm(*_a, **_k):
        raise RuntimeError("skip llm")

    handler.get_asset_manager = lambda: type("M", (), {"store": fake_store})()
    monkeypatch.setattr(handler, "render_prompt", lambda *a, **k: type("P", (), {"version": "1.0"})())
    monkeypatch.setattr(handler, "chat_json_with_cache", fail_llm)

    output = await handler.execute(
        AgentTaskInput(
            job_id=uuid4(),
            project_id=uuid4(),
            pipeline_id=uuid4(),
            step="seo",
            payload={
                "topic": "GTA 6",
                "script": {"title": "GTA 6", "hook": "Novidades insanas"},
            },
        )
    )
    assert output.data["seo_score"] > 0
    assert output.data["seo_package"]["title"]
    assert output.data["publication_hashtags"]
