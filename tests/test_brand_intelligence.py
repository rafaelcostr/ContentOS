"""Tests for Brand Intelligence — Growth OS Fase 5."""

from __future__ import annotations

from uuid import uuid4

import pytest
from contentos_gateway.api.routes.project_brand import BrandIdentityPatchBody
from contentos_memory.domain.brand_identity import normalize_color_palette, normalize_string_list
from contentos_memory.domain.project_memory import ProjectMemoryData


def test_format_brand_context_full():
    memory = ProjectMemoryData(
        project_id=uuid4(),
        mission="Educar sobre finanças pessoais",
        objectives=["crescimento orgânico", "autoridade"],
        values=["transparência", "clareza"],
        target_audience="Jovens 18-30 interessados em investimentos",
        tone="didático e acessível",
        color_palette={"primary": "#1E40AF", "accent": "#F59E0B"},
        editorial_rules=["Sem promessas irreais", "Sempre citar fontes"],
    )
    ctx = memory.format_brand_context()
    assert "Educar sobre finanças" in ctx
    assert "transparência" in ctx
    assert "18-30" in ctx
    assert "#1E40AF" in ctx
    assert "Sem promessas" in ctx


def test_format_context_includes_brand():
    memory = ProjectMemoryData(
        project_id=uuid4(),
        niche="finanças",
        mission="Democratizar investimentos",
        tone="casual",
    )
    ctx = memory.format_context()
    assert "finanças" in ctx
    assert "Democratizar investimentos" in ctx


def test_apply_brand_patch_partial():
    memory = ProjectMemoryData(project_id=uuid4(), mission="Antiga")
    memory.apply_brand_patch(
        {
            "mission": "Nova missão",
            "objectives": ["obj1", "obj2"],
            "color_palette": {"primary": "#FFF", "invalid": "x"},
        }
    )
    assert memory.mission == "Nova missão"
    assert memory.objectives == ["obj1", "obj2"]
    assert memory.color_palette == {"primary": "#FFF"}


def test_from_dict_brand_roundtrip():
    pid = uuid4()
    data = ProjectMemoryData(
        project_id=pid,
        mission="Test",
        values=["a", "b"],
        color_palette={"primary": "#000"},
    )
    restored = ProjectMemoryData.from_dict(pid, data.to_dict())
    assert restored.mission == "Test"
    assert restored.values == ["a", "b"]
    assert restored.color_palette == {"primary": "#000"}


def test_normalize_string_list_dedupes():
    assert normalize_string_list(["a", "a", " b ", ""]) == ["a", "b"]


def test_normalize_color_palette_allowed_keys_only():
    assert normalize_color_palette({"primary": "#111", "foo": "bar"}) == {"primary": "#111"}


def test_brand_patch_body_accepts_valid():
    body = BrandIdentityPatchBody(
        mission="Missão",
        objectives=["obj"],
        color_palette={"primary": "#ABC"},
    )
    assert body.mission == "Missão"


def test_to_brand_dict_preview():
    memory = ProjectMemoryData(project_id=uuid4(), mission="Grow")
    brand = memory.to_brand_dict()
    assert "brand_context_preview" in brand
    assert "Grow" in brand["brand_context_preview"]
