"""Factory truth table + media production policy tests."""

from contentos_events.domain.event_types import STEP_TO_DOMAIN_EVENT
from contentos_shared.enums import PipelineStep
from contentos_shared.factory_truth import build_factory_truth_rows, format_factory_truth_markdown
from contentos_shared.media_production import render_allow_placeholder, require_media_assets, scene_clip_coverage


def test_factory_truth_row_count():
    rows = build_factory_truth_rows()
    assert len(rows) == 31
    assert rows[0].step == "research"
    assert rows[-1].step == "publisher"


def test_factory_truth_matches_pipeline_order():
    steps = [step.value for step in PipelineStep.factory_full_ordered()]
    rows = build_factory_truth_rows()
    assert [r.step for r in rows] == steps


def test_factory_truth_queue_and_event():
    rows = build_factory_truth_rows()
    for row in rows:
        assert row.queue == f"contentos.{row.step}"
        assert row.event == STEP_TO_DOMAIN_EVENT.get(row.step, "step.completed")


def test_factory_truth_markdown_contains_table():
    md = format_factory_truth_markdown()
    assert "| `research` |" in md
    assert "| `publisher` |" in md
    assert "31 steps" in md


def test_render_allow_placeholder_defaults(monkeypatch):
    monkeypatch.delenv("RENDER_ALLOW_PLACEHOLDER", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    assert render_allow_placeholder() is True
    monkeypatch.setenv("APP_ENV", "production")
    assert render_allow_placeholder() is False
    monkeypatch.setenv("RENDER_ALLOW_PLACEHOLDER", "true")
    assert render_allow_placeholder() is True


def test_require_media_assets_follows_production(monkeypatch):
    monkeypatch.delenv("MEDIA_REQUIRE_ASSETS", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    assert require_media_assets() is True


def test_scene_clip_coverage_basic():
    coverage = scene_clip_coverage(
        ["a", "b"],
        [{"label": "a", "asset_key": "takes/a.mp4"}],
    )
    assert coverage["passed"] is False
    assert coverage["missing_scene_labels"] == ["b"]
