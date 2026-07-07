"""Tests for V5.0.3 media_analyze — domain + handler."""

from __future__ import annotations

from uuid import uuid4

import pytest
from contentos_shared.enums import JobStatus, PipelineStep
from contentos_shared.schemas.agent import AgentTaskInput
from contentos_storage.domain.media_analysis import (
    analysis_summary_text,
    analysis_to_metadata,
    merge_vision_results,
    normalize_media_analysis,
)


def test_pipeline_step_media_analyze_in_v2_order():
    steps = [s.value for s in PipelineStep.v2_ordered()]
    idx = steps.index("asset_index")
    assert steps[idx + 1] == "media_analyze"
    assert steps[idx + 2] == "asset_search"


def test_normalize_media_analysis():
    raw = {
        "objects": ["car", "city"],
        "scenario": "night street",
        "emotion": "tension",
        "time_of_day": "night",
    }
    out = normalize_media_analysis(raw)
    assert "car" in out["objects"]
    assert out["scenario"] == "night street"


def test_merge_vision_results_dedupes_objects():
    merged = merge_vision_results(
        [
            {"objects": ["car"], "scenario": "street"},
            {"objects": ["car", "neon"], "emotion": "tension"},
        ]
    )
    assert merged["objects"] == ["car", "neon"]
    assert merged["scenario"] == "street"
    assert merged["emotion"] == "tension"


def test_analysis_to_metadata_facets():
    meta = analysis_to_metadata(
        {
            "objects": ["car"],
            "colors": ["blue", "red"],
            "motion": "fast",
            "scenario": "chase",
        }
    )
    assert meta["motion"] == "fast"
    assert meta["objects"] == ["car"]
    assert "media_analysis" in meta


def test_analysis_summary_text():
    text = analysis_summary_text(
        {"scenario": "city chase", "objects": ["car", "motorcycle"]},
        topic="GTA 6",
    )
    assert "GTA 6" in text
    assert "city chase" in text


@pytest.mark.asyncio
async def test_media_analyze_handler_no_assets(monkeypatch):
    monkeypatch.setenv("ENABLE_MEDIA_ANALYZE", "true")
    from contentos_agents.handlers.media_analyze import MediaAnalyzeAgentHandler

    handler = MediaAnalyzeAgentHandler()
    task = AgentTaskInput(
        job_id=uuid4(),
        pipeline_id=uuid4(),
        project_id=uuid4(),
        step="media_analyze",
        payload={"topic": "GTA 6"},
    )
    output = await handler.execute(task)
    assert output.status == JobStatus.COMPLETED.value
    assert output.data["analyzed_count"] == 0


@pytest.mark.asyncio
async def test_media_analyze_handler_disabled(monkeypatch):
    monkeypatch.setenv("ENABLE_MEDIA_ANALYZE", "false")
    from contentos_agents.handlers.media_analyze import MediaAnalyzeAgentHandler

    handler = MediaAnalyzeAgentHandler()
    task = AgentTaskInput(
        job_id=uuid4(),
        pipeline_id=uuid4(),
        project_id=uuid4(),
        step="media_analyze",
        payload={"asset_ids": [str(uuid4())]},
    )
    output = await handler.execute(task)
    assert output.status == JobStatus.COMPLETED.value
    assert output.data.get("skipped") is True
