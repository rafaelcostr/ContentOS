"""Tests for Workflow Templates (V2.12)."""

import os

import pytest
from contentos_shared.enums import PipelineStep
from contentos_shared.workflow_templates import (
    BUILTIN_TEMPLATES,
    get_builtin,
    get_default_workflow_name,
    list_builtin_names,
)


def test_builtin_templates_exist():
    assert "v1-default" in BUILTIN_TEMPLATES
    assert "v2-full" in BUILTIN_TEMPLATES


def test_v1_default_has_nine_steps():
    tpl = get_builtin("v1-default")
    assert tpl is not None
    assert len(tpl["steps"]) == 9
    assert tpl["steps"] == [s.value for s in PipelineStep.ordered()]
    assert tpl["is_default"] is True


def test_v2_full_enables_async_features():
    tpl = get_builtin("v2-full")
    assert tpl is not None
    cfg = tpl["config"]
    assert "enable_clip_pipeline" not in cfg
    assert cfg["enable_thumbnail"] is True
    assert cfg["enable_analytics_ai"] is True


def test_get_builtin_unknown():
    assert get_builtin("nonexistent") is None


def test_list_builtin_names():
    names = list_builtin_names()
    assert set(names) == {
        "v1-default",
        "v2-full",
        "v2-dynamic",
        "v3-quality",
        "v4-intelligence",
        "v4-multi-text",
        "v4-multi-full",
        "factory-full",
        "v5-media-autopilot",
    }


def test_v2_dynamic_has_asset_search_step():
    tpl = get_builtin("v2-dynamic")
    assert tpl is not None
    assert len(tpl["steps"]) == 14
    assert tpl["steps"][3] == "asset_index"
    assert "clip_research" not in tpl["steps"]
    assert "asset_collector" not in tpl["steps"]
    assert "asset_search" in tpl["steps"]
    assert tpl["steps"][-1] == "analytics"


def test_factory_full_has_executable_assembly_line():
    tpl = get_builtin("factory-full")
    assert tpl is not None
    assert len(tpl["steps"]) == 29
    assert tpl["steps"][:5] == ["research", "trend_intelligence", "hook", "script", "script_review"]
    assert tpl["steps"][-10:] == [
        "auto_retry",
        "content_score",
        "ai_director",
        "content_intelligence",
        "learning",
        "knowledge_base",
        "creative_memory",
        "analytics",
        "seo",
        "publisher",
    ]
    assert "clip_research" not in tpl["steps"]
    assert "asset_collector" not in tpl["steps"]
    assert tpl["steps"].index("asset_search") + 1 == tpl["steps"].index("takes")
    assert tpl["steps"].index("video_review") + 1 == tpl["steps"].index("auto_retry")
    assert tpl["steps"].index("auto_retry") + 1 == tpl["steps"].index("content_score")
    assert tpl["config"]["enable_auto_retry"] is True
    assert tpl["config"]["enable_content_score"] is True
    assert tpl["config"]["enable_learning"] is True
    assert tpl["config"]["enable_knowledge_base"] is True
    assert "enable_clip_pipeline" not in tpl["config"]


def test_v5_media_autopilot_is_lean_media_pipeline():
    tpl = get_builtin("v5-media-autopilot")
    assert tpl is not None
    assert len(tpl["steps"]) == 16
    assert tpl["steps"] == [s.value for s in PipelineStep.v5_media_autopilot_ordered()]
    assert tpl["steps"][3] == "asset_index"
    assert "clip_research" not in tpl["steps"]
    assert "asset_collector" not in tpl["steps"]
    assert tpl["steps"].index("media_analyze") == tpl["steps"].index("asset_index") + 1
    assert tpl["steps"].index("asset_search") + 1 == tpl["steps"].index("takes")
    assert tpl["steps"][-1] == "publisher"
    assert "thumbnail" not in tpl["steps"]
    assert "analytics" not in tpl["steps"]
    cfg = tpl["config"]
    assert "enable_clip_pipeline" not in cfg
    assert cfg["enable_media_analyze"] is True
    assert cfg["enable_take_recommendation"] is True
    assert cfg["enable_v5_media_autopilot"] is True
    assert cfg["content_sources"] == ["own_library", "local_library"]


def test_default_workflow_from_env(monkeypatch):
    monkeypatch.setenv("DEFAULT_WORKFLOW", "v2-full")
    assert get_default_workflow_name() == "v2-full"


def test_default_workflow_fallback(monkeypatch):
    monkeypatch.delenv("DEFAULT_WORKFLOW", raising=False)
    assert get_default_workflow_name() == "v1-default"


@pytest.mark.asyncio
async def test_ensure_workflow_templates_idempotent():
    from contentos_database.models import WorkflowDefinition
    from contentos_database.workflow_seed import ensure_workflow_templates

    class FakeResult:
        def __init__(self, row):
            self._row = row

        def scalar_one_or_none(self):
            return self._row

    class FakeSession:
        def __init__(self):
            self.added: list = []
            self._existing: dict[str, WorkflowDefinition] = {}

        async def execute(self, stmt):
            name = stmt.whereclause.right.value  # type: ignore[attr-defined]
            return FakeResult(self._existing.get(name))

        def add(self, obj):
            self.added.append(obj)
            self._existing[obj.name] = obj

    db = FakeSession()
    created = await ensure_workflow_templates(db)
    assert created == 9
    assert len(db.added) == 9

    created_again = await ensure_workflow_templates(db)
    assert created_again == 0
    assert len(db.added) == 9
