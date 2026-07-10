"""Post-render retention + platform publication audit tests."""

from uuid import uuid4

import pytest
from contentos_intelligence.application.retention import RetentionAnalyzer
from contentos_intelligence.application.retention.post_render import (
    enrich_payload_for_post_render,
    retention_analysis_mode,
)


def test_retention_post_render_mode_after_quality():
    payload = enrich_payload_for_post_render(
        {
            "duration_seconds": 28.5,
            "quality_passed": True,
            "quality_score": 8,
            "render_diagnostics": {"missing_clip_count": 0, "used_silent_audio": False},
            "scenes": [{"label": "main", "start_seconds": 0, "end_seconds": 28.5}],
            "emotion": {"curiosity": 8, "retention": 7},
        }
    )
    assert retention_analysis_mode(payload) == "post_render"
    report = RetentionAnalyzer().analyze(payload)
    assert report.analysis_mode == "post_render"
    assert report.render_duration_seconds == pytest.approx(28.5)
    assert report.quality_score_at_analysis == 8


def test_retention_penalized_when_quality_failed():
    payload = enrich_payload_for_post_render(
        {
            "duration_seconds": 20,
            "quality_passed": False,
            "quality_score": 4,
            "render_diagnostics": {"missing_clip_count": 2, "used_silent_audio": True},
            "scenes": [{"label": "main", "start_seconds": 0, "end_seconds": 20}],
            "emotion": {"curiosity": 8, "retention": 8},
        }
    )
    baseline = RetentionAnalyzer().analyze(
        {
            **payload,
            "quality_passed": True,
            "_retention_penalty_reasons": [],
        }
    ).overall_score
    penalized = RetentionAnalyzer().analyze(payload).overall_score
    assert penalized < baseline


def test_retention_skips_missing_clip_penalty_when_quality_passed():
    payload = enrich_payload_for_post_render(
        {
            "duration_seconds": 27.7,
            "quality_passed": True,
            "quality_score": 9,
            "render_diagnostics": {"missing_clip_count": 6, "used_silent_audio": False},
            "scenes": [
                {"label": "gta_logo", "start_seconds": 0, "end_seconds": 6},
                {"label": "community_theories", "start_seconds": 6, "end_seconds": 17},
                {"label": "future_scenes", "start_seconds": 17, "end_seconds": 24},
                {"label": "advanced_ai", "start_seconds": 24, "end_seconds": 27.7},
            ],
            "emotion": {"curiosity": 8, "retention": 7},
            "director_plan": {
                "segments": [
                    {"movement": "static", "transition": "fade"},
                    {"movement": "pan-left", "transition": "fade"},
                    {"movement": "static", "transition": "fade"},
                    {"movement": "static", "transition": "fade"},
                ],
            },
        }
    )
    report = RetentionAnalyzer().analyze(payload)
    assert report.overall_score > 0
    assert report.completion_pct > 0
    assert "missing_clips:" not in str(payload.get("_retention_penalty_reasons", []))


def test_factory_full_retention_after_quality():
    from contentos_shared.enums import PipelineStep

    steps = PipelineStep.factory_full_ordered()
    assert steps.index(PipelineStep.QUALITY) < steps.index(PipelineStep.RETENTION)
    assert steps.index(PipelineStep.RETENTION) < steps.index(PipelineStep.VIDEO_REVIEW)


def test_v5_autopilot_retention_after_quality():
    from contentos_shared.enums import PipelineStep

    steps = PipelineStep.v5_media_autopilot_ordered()
    assert steps.index(PipelineStep.QUALITY) + 1 == steps.index(PipelineStep.RETENTION)


@pytest.mark.asyncio
async def test_persist_platform_publications(monkeypatch):
    from contentos_database import platform_publications as mod

    stored: list[dict] = []

    class FakeSession:
        def add(self, row):
            stored.append(
                {
                    "platform": row.platform,
                    "status": row.status,
                    "external_id": row.external_id,
                }
            )

        async def commit(self):
            return None

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://x")
    monkeypatch.setattr(mod, "get_session_factory", lambda: FakeSession)

    count = await mod.persist_platform_publications(
        uuid4(),
        uuid4(),
        "dry_run",
        {
            "youtube": {
                "status": "dry_run",
                "title": "Demo",
                "external_id": None,
                "publish_url": "https://preview",
                "payload": {"mode": "dry_run"},
            }
        },
    )
    assert count == 1
    assert stored[0]["platform"] == "youtube"
