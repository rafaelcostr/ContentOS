"""Factory map tests."""

from pathlib import Path

from contentos_shared.enums import PipelineStep
from contentos_shared.factory_map import (
    FACTORY_LINE,
    FACTORY_MODULES,
    executable_factory_steps,
    planned_or_partial_stages,
    stages_by_module,
    stages_by_status,
)


def test_factory_line_has_requested_assembly_order():
    keys = [stage.key for stage in FACTORY_LINE]

    assert keys[0] == "project"
    assert keys[1] == "theme"
    assert keys.index("research") < keys.index("script")
    assert keys.index("scene_director") < keys.index("clip_research")
    assert keys.index("media_analyze") < keys.index("asset_search")
    assert keys.index("editor") < keys.index("retention")
    assert keys.index("auto_retry") < keys.index("content_score")
    assert keys.index("creative_memory") < keys.index("analytics")
    assert keys.index("seo") < keys.index("publisher")
    assert keys[-1] == "dashboard"


def test_factory_map_matches_executable_factory_full_pipeline():
    assert executable_factory_steps() == PipelineStep.factory_full_ordered()
    assert len(executable_factory_steps()) == 31


def test_factory_map_doc_matches_quality_retention_order():
    root = Path(__file__).resolve().parents[1]
    doc = (root / "docs" / "FACTORY_MAP.md").read_text(encoding="utf-8")
    quality = "| 21 | Quality AI |"
    retention = "| 22 | Retention Engine |"
    assert quality in doc
    assert retention in doc
    assert doc.index(quality) < doc.index(retention)


def test_factory_modules_cover_all_stages():
    module_keys = {module.key for module in FACTORY_MODULES}

    assert module_keys
    assert all(stage.module in module_keys for stage in FACTORY_LINE)


def test_factory_map_tracks_incomplete_work():
    incomplete = planned_or_partial_stages()
    incomplete_keys = {stage.key for stage in incomplete}

    assert "asset_search" not in incomplete_keys
    assert "auto_retry" not in incomplete_keys
    assert "content_score" not in incomplete_keys
    assert "knowledge_base" not in incomplete_keys
    assert "creative_memory" not in incomplete_keys
    assert "seo" not in incomplete_keys


def test_asset_search_is_now_an_executable_factory_stage():
    asset_search = next(stage for stage in FACTORY_LINE if stage.key == "asset_search")
    assert asset_search.executable is True
    assert asset_search.pipeline_step is not None


def test_factory_helpers_filter_by_module_and_status():
    assert all(stage.module == "assets" for stage in stages_by_module("assets"))
    assert all(stage.status == "planned" for stage in stages_by_status("planned"))


def test_learning_is_now_an_executable_factory_stage():
    learning = next(stage for stage in FACTORY_LINE if stage.key == "learning")
    assert learning.executable is True
    assert learning.pipeline_step is not None


def test_content_score_is_now_an_executable_factory_stage():
    content_score = next(stage for stage in FACTORY_LINE if stage.key == "content_score")
    assert content_score.executable is True
    assert content_score.pipeline_step is not None


def test_auto_retry_is_now_an_executable_factory_stage():
    auto_retry = next(stage for stage in FACTORY_LINE if stage.key == "auto_retry")
    assert auto_retry.executable is True
    assert auto_retry.pipeline_step is not None


def test_knowledge_base_is_now_an_executable_factory_stage():
    knowledge_base = next(stage for stage in FACTORY_LINE if stage.key == "knowledge_base")
    assert knowledge_base.executable is True
    assert knowledge_base.pipeline_step is not None


def test_v5_factory_stages_are_executable():
    for key in ("media_analyze", "retention", "ai_director", "creative_memory", "seo"):
        stage = next(stage for stage in FACTORY_LINE if stage.key == key)
        assert stage.executable is True
        assert stage.pipeline_step is not None
