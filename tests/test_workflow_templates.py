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
    assert cfg["enable_clip_pipeline"] is True
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
    }


def test_v2_dynamic_has_fourteen_steps():
    tpl = get_builtin("v2-dynamic")
    assert tpl is not None
    assert len(tpl["steps"]) == 14
    assert tpl["steps"][3] == "clip_research"
    assert tpl["steps"][-1] == "analytics"


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
    assert created == 7
    assert len(db.added) == 7

    created_again = await ensure_workflow_templates(db)
    assert created_again == 0
    assert len(db.added) == 7
