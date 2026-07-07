"""V5.1.4 — Project DNA 2.0 tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from contentos_gateway.api.routes.project_dna import ProjectDnaPatchBody
from contentos_memory.domain.dna_v2 import normalize_cinematic_preset, normalize_content_angle
from contentos_memory.domain.project_memory import ProjectMemoryData
from contentos_shared.director_plan import build_director_plan
from contentos_shared.dna.pipeline_hints import build_cinematic_from_memory, project_dna_payload_hints


def test_normalize_cinematic_preset():
    assert normalize_cinematic_preset("dynamic") == "dynamic"
    assert normalize_cinematic_preset("INVALID") == ""


def test_normalize_content_angle():
    assert normalize_content_angle("hype") == "hype"
    assert normalize_content_angle("story_telling") == ""


def test_build_cinematic_from_memory():
    memory = ProjectMemoryData(project_id=uuid4(), cinematic_preset="punchy")
    cinematic = build_cinematic_from_memory(memory)
    assert cinematic is not None
    assert cinematic["preset"] == "punchy"
    assert cinematic["ducking_ratio"] == 12.0


def test_build_cinematic_with_editing_overrides():
    memory = ProjectMemoryData(
        project_id=uuid4(),
        cinematic_preset="calm",
        editing_preferences={"music_volume": 0.08, "enable_speed_ramp": False},
    )
    cinematic = build_cinematic_from_memory(memory)
    assert cinematic["music_volume"] == 0.08
    assert cinematic["enable_speed_ramp"] is False


def test_project_dna_payload_hints():
    memory = ProjectMemoryData(
        project_id=uuid4(),
        cinematic_preset="dynamic",
        content_angle="hype",
        brand_keywords=["GTA", "open world"],
    )
    hints = project_dna_payload_hints(memory)
    assert hints["cinematic"]["preset"] == "dynamic"
    assert hints["project_dna"]["content_angle"] == "hype"
    assert hints["brand_keywords"] == ["GTA", "open world"]


def test_format_dna_context_v2_fields():
    memory = ProjectMemoryData(
        project_id=uuid4(),
        content_angle="documentary",
        cinematic_preset="calm",
        brand_keywords=["nature", "wildlife"],
    )
    ctx = memory.format_dna_context()
    assert "documentário" in ctx
    assert "calm" in ctx
    assert "nature" in ctx


def test_apply_dna_patch_v2():
    memory = ProjectMemoryData(project_id=uuid4())
    memory.apply_dna_patch(
        {
            "cinematic_preset": "dynamic",
            "content_angle": "tutorial",
            "brand_keywords": ["how-to", "tips"],
            "editing_preferences": {"enable_zoom": False},
        }
    )
    assert memory.cinematic_preset == "dynamic"
    assert memory.content_angle == "tutorial"
    assert memory.brand_keywords == ["how-to", "tips"]
    assert memory.editing_preferences["enable_zoom"] is False


def test_build_director_plan_content_angle_hype():
    scenes = [{"label": "intro", "start_seconds": 0, "end_seconds": 5}]
    plan = build_director_plan(
        storyboard={"frames": [{"scene_index": 0}]},
        scenes=scenes,
        emotion={"overall": 5},
        content_angle="hype",
    )
    assert plan["pacing"] == "fast"
    assert plan["segments"][0]["movement"] == "speed-ramp-up"


def test_dna_patch_body_validates_cinematic_preset():
    with pytest.raises(ValueError):
        ProjectDnaPatchBody(cinematic_preset="neon")


def test_dna_patch_body_validates_content_angle():
    with pytest.raises(ValueError):
        ProjectDnaPatchBody(content_angle="viral")


def test_dna_patch_body_accepts_v2_fields():
    body = ProjectDnaPatchBody(
        cinematic_preset="punchy",
        content_angle="news",
        brand_keywords=["breaking"],
        editing_preferences={"music_volume": 0.2},
    )
    assert body.cinematic_preset == "punchy"
    assert body.content_angle == "news"
