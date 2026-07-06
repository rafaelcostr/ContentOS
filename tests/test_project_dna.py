"""Tests for Project DNA (V4.0.2 / Epic 8)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from contentos_gateway.api.routes.project_dna import ProjectDnaPatchBody
from contentos_memory.domain.project_dna import clamp_humor_level, normalize_pace
from contentos_memory.domain.project_memory import ProjectMemoryData


def test_format_dna_context_full():
    memory = ProjectMemoryData(
        project_id=uuid4(),
        humor_level=0.75,
        pace="fast",
        narrator_persona="hype gamer",
        cta_style="urgente",
        preferred_formats=["tiktok", "youtube_shorts"],
        hook_patterns=["pergunta chocante"],
        visual_style={"primary_color": "#FF0050", "mood": "neon"},
    )
    ctx = memory.format_dna_context()
    assert "75%" in ctx
    assert "rápido" in ctx
    assert "hype gamer" in ctx
    assert "tiktok" in ctx
    assert "#FF0050" in ctx


def test_format_context_includes_dna():
    memory = ProjectMemoryData(
        project_id=uuid4(),
        niche="games",
        tone="casual",
        pace="fast",
        narrator_persona="streamer",
    )
    ctx = memory.format_context()
    assert "games" in ctx
    assert "Narrador: streamer" in ctx


def test_apply_dna_patch_partial():
    memory = ProjectMemoryData(project_id=uuid4(), pace="slow", humor_level=0.2)
    memory.apply_dna_patch({"pace": "fast", "narrator_persona": "tech expert"})
    assert memory.pace == "fast"
    assert memory.humor_level == 0.2
    assert memory.narrator_persona == "tech expert"


def test_from_dict_dna_roundtrip():
    pid = uuid4()
    data = ProjectMemoryData(
        project_id=pid,
        humor_level=0.5,
        pace="medium",
        preferred_formats=["linkedin"],
    )
    restored = ProjectMemoryData.from_dict(pid, data.to_dict())
    assert restored.humor_level == 0.5
    assert restored.pace == "medium"
    assert restored.preferred_formats == ["linkedin"]


def test_clamp_humor_level():
    assert clamp_humor_level(1.5) == 1.0
    assert clamp_humor_level(-0.1) == 0.0
    assert clamp_humor_level(None) is None


def test_normalize_pace_invalid():
    assert normalize_pace("invalid") == ""
    assert normalize_pace("FAST") == "fast"


def test_dna_patch_body_validates_pace():
    with pytest.raises(ValueError):
        ProjectDnaPatchBody(pace="ultra-fast")


def test_dna_patch_body_validates_formats():
    with pytest.raises(ValueError):
        ProjectDnaPatchBody(preferred_formats=["unknown_format"])


def test_dna_patch_body_accepts_valid():
    body = ProjectDnaPatchBody(
        humor_level=0.8,
        pace="fast",
        preferred_formats=["tiktok", "thread_x"],
    )
    assert body.pace == "fast"
    assert body.humor_level == 0.8


def test_to_dna_dict_preview():
    memory = ProjectMemoryData(project_id=uuid4(), pace="slow")
    dna = memory.to_dna_dict()
    assert "dna_context_preview" in dna
    assert "lento" in dna["dna_context_preview"]
