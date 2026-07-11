"""V5.0.5 — v5-media-autopilot template + GTA 6 E2E simulation."""

from __future__ import annotations

from uuid import uuid4

import pytest
from contentos_database.models import Asset
from contentos_shared.enums import AssetCategory, PipelineStep
from contentos_shared.schemas.agent import AgentTaskInput
from contentos_shared.workflow_templates import get_builtin

GTA_TOPIC = "GTA 6"
GTA_SCENES = [
    {"label": "beach", "visual_hint": "GTA 6 beach sunset", "duration_seconds": 8},
    {"label": "chase", "visual_hint": "car chase city night", "duration_seconds": 10},
]


def _asset(
    *,
    object_key: str,
    scene_label: str,
    tags: list[str] | None = None,
    metadata: dict | None = None,
) -> Asset:
    meta = dict(metadata or {})
    meta.setdefault("scene_label", scene_label)
    return Asset(
        id=uuid4(),
        category=AssetCategory.TAKES.value,
        bucket="contentos",
        object_key=object_key,
        content_type="video/mp4",
        size_bytes=3_000_000,
        sha256="b" * 64,
        tags=tags or [scene_label, GTA_TOPIC],
        metadata_=meta,
    )


def test_v5_media_autopilot_template_exists():
    tpl = get_builtin("v5-media-autopilot")
    assert tpl is not None
    assert tpl["name"] == "v5-media-autopilot"
    assert len(tpl["steps"]) == 16


def test_v5_media_autopilot_step_order():
    expected = [s.value for s in PipelineStep.v5_media_autopilot_ordered()]
    tpl = get_builtin("v5-media-autopilot")
    assert tpl is not None
    assert tpl["steps"] == expected
    media_idx = expected.index("media_analyze")
    assert expected[media_idx - 1] == "asset_index"
    assert expected[media_idx + 1] == "asset_search"
    assert "clip_research" not in expected
    assert "asset_collector" not in expected


def test_engine_queue_map_covers_v5_steps():
    from contentos_workflow.engine import STEP_QUEUE_MAP

    for step in PipelineStep.v5_media_autopilot_ordered():
        assert step.value in STEP_QUEUE_MAP


def test_v5_config_enables_media_pipeline():
    cfg = get_builtin("v5-media-autopilot")["config"]
    assert "enable_clip_pipeline" not in cfg
    assert cfg["enable_media_analyze"] is True
    assert cfg["enable_take_recommendation"] is True
    assert cfg.get("default_topic_hint") == "GTA 6"


def test_gta6_media_chain_asset_search_to_takes():
    """Simulate GTA 6: 2 scenes → asset_search → takes with ≥2 clips."""
    from contentos_agents.handlers.asset_search import AssetSearchAgentHandler
    from contentos_agents.handlers.takes import TakesAgentHandler

    beach = _asset(
        object_key="takes/gta_beach.mp4",
        scene_label="beach",
        metadata={"objects": ["GTA 6 beach cars"], "scenario": "beach sunset"},
    )
    chase = _asset(
        object_key="takes/gta_chase.mp4",
        scene_label="chase",
        metadata={"objects": ["car chase city"], "scenario": "city night", "motion": "fast"},
    )

    search_handler = AssetSearchAgentHandler()
    matches = search_handler._match_scenes(GTA_SCENES, [beach, chase], [], GTA_TOPIC)
    assert len(matches) == 2
    assert matches[0]["selected"]["asset_key"] == "takes/gta_beach.mp4"
    assert matches[1]["selected"]["asset_key"] == "takes/gta_chase.mp4"
    assert matches[0]["selected"]["score"] > 0
    assert matches[1]["selected"]["score"] > 0

    takes_handler = TakesAgentHandler()
    labels = [s["label"] for s in GTA_SCENES]
    clips = takes_handler._clips_from_asset_search(matches, labels)
    assert len(clips) == 2
    assert clips[0].asset_key == "takes/gta_beach.mp4"
    assert clips[1].asset_key == "takes/gta_chase.mp4"


@pytest.mark.asyncio
async def test_gta6_asset_search_agent_output_shape():
    from contentos_agents.handlers.asset_search import AssetSearchAgentHandler

    beach = _asset(object_key="takes/gta_beach.mp4", scene_label="beach")
    chase = _asset(object_key="takes/gta_chase.mp4", scene_label="chase")
    task = AgentTaskInput(
        job_id=uuid4(),
        pipeline_id=uuid4(),
        project_id=uuid4(),
        step="asset_search",
        payload={
            "topic": GTA_TOPIC,
            "scenes": GTA_SCENES,
            "assets": [],
        },
    )

    handler = AssetSearchAgentHandler()
    handler._load_assets = lambda _task: [beach, chase]  # type: ignore[method-assign]
    output = await handler.execute(task)

    assert output.status == "completed"
    assert output.data["take_recommendation"] is True
    assert output.data["asset_search_count"] == 2
    assert len(output.data["assets_selected"]) == 2
    keys = {item["asset_key"] for item in output.data["assets_selected"]}
    assert keys == {"takes/gta_beach.mp4", "takes/gta_chase.mp4"}
