"""Fase 5 + 6 — audiovisual QA gate and publisher contracts."""

from uuid import uuid4

import pytest
from contentos_agents.handlers.publisher import PublisherAgentHandler
from contentos_agents.handlers.quality import QualityAgentHandler, _require_real_media
from contentos_shared.audiovisual_qa import (
    check_subtitle_sync,
    evaluate_publish_gate,
    normalize_publish_mode,
    parse_srt_cues,
    should_block_live_publish,
)
from contentos_shared.quality_scoring import build_quality_report
from contentos_shared.schemas.agent import AgentTaskInput
from contentos_shared.schemas.asset import AssetRef


def test_quality_real_media_policy_from_env(monkeypatch):
    monkeypatch.setenv("QUALITY_REQUIRE_REAL_MEDIA", "true")
    assert _require_real_media() is True
    monkeypatch.setenv("QUALITY_REQUIRE_REAL_MEDIA", "false")
    assert _require_real_media() is False


def test_quality_diagnostics_add_strict_media_errors():
    handler = QualityAgentHandler()
    probe_state = {"extra_errors": []}

    handler._apply_render_diagnostics(
        probe_state,
        {
            "missing_clip_count": 2,
            "placeholder_scene_labels": ["intro", "cta"],
            "used_silent_audio": True,
            "subtitles_embedded": False,
        },
        require_real_media=True,
    )

    assert probe_state["has_real_clips"] is False
    assert probe_state["has_narration_audio"] is False
    assert probe_state["missing_clip_count"] == 2
    assert "Render contains placeholder scenes: intro, cta" in probe_state["extra_errors"]
    assert "Render used generated/silent narration audio" in probe_state["extra_errors"]
    assert "Render was produced without embedded subtitles" in probe_state["extra_errors"]


def test_parse_srt_cues_and_sync():
    srt = "1\n00:00:00,000 --> 00:00:02,000\nHello\n\n2\n00:00:02,000 --> 00:00:04,000\nWorld\n"
    cues = parse_srt_cues(srt)
    assert len(cues) == 2
    segments = [{"start": 0.0, "end": 2.0, "text": "Hello"}, {"start": 2.0, "end": 4.0, "text": "World"}]
    ok, detail = check_subtitle_sync(segments, srt)
    assert ok is True
    assert "ok" in detail


def test_subtitle_sync_detects_drift():
    srt = "1\n00:00:05,000 --> 00:00:07,000\nLate\n"
    segments = [{"start": 0.0, "end": 2.0, "text": "Hello"}]
    ok, detail = check_subtitle_sync(segments, srt, tolerance_sec=1.0)
    assert ok is False
    assert "drift" in detail


def test_evaluate_publish_gate_all_pass():
    gate = evaluate_publish_gate(
        {
            "quality_passed": True,
            "video_review_passed": True,
            "retention_passed": True,
        }
    )
    assert gate["publishable"] is True
    assert gate["block_reasons"] == []


def test_evaluate_publish_gate_blocks_on_quality():
    gate = evaluate_publish_gate({"quality_passed": False, "video_review_passed": True})
    assert gate["publishable"] is False
    assert "quality" in gate["block_reasons"]


def test_should_block_live_publish_only_in_live_mode(monkeypatch):
    monkeypatch.setenv("PUBLISH_REQUIRE_QA", "true")
    payload = {"quality_passed": False, "video_review_passed": True}
    blocked, _ = should_block_live_publish(payload, mode="live")
    assert blocked is True
    blocked_dry, _ = should_block_live_publish(payload, mode="dry_run")
    assert blocked_dry is False


def test_normalize_publish_mode_aliases():
    assert normalize_publish_mode("prepare") == "prepare_only"
    assert normalize_publish_mode("LIVE") == "live"


def test_quality_report_bitrate_and_sync_dimensions():
    report = build_quality_report(
        has_render=True,
        render_exists=True,
        render_size_ok=True,
        has_audio_ref=True,
        has_audio_stream=True,
        has_subtitles=True,
        subtitle_sync_skipped=False,
        width=1080,
        height=1920,
        codec="h264",
        fps=60.0,
        duration=30.0,
        subtitle_sync_ok=False,
        bit_rate=500_000,
    )
    assert report.passed is False
    assert report.dimensions["subtitle_sync"] == 0
    assert report.dimensions["bitrate"] == 0


@pytest.mark.asyncio
async def test_publisher_blocks_live_when_qa_fails(monkeypatch):
    monkeypatch.setenv("PUBLISH_MODE", "live")
    monkeypatch.setenv("PUBLISH_REQUIRE_QA", "true")

    class FakeAssetManager:
        async def store(self, category, data, meta):
            return AssetRef(
                id=uuid4(),
                category=category,
                key="assets/publication.json",
                bucket="contentos",
                content_type="application/json",
            )

        async def get(self, ref):
            return b"video-bytes"

        async def exists(self, ref):
            return False

        async def get_presigned_url(self, ref, expires=3600):
            return "http://localhost:9000/contentos/renders/final.mp4?sig=1"

    handler = PublisherAgentHandler()
    handler.get_asset_manager = lambda: FakeAssetManager()

    task = AgentTaskInput(
        job_id=uuid4(),
        pipeline_id=uuid4(),
        project_id=uuid4(),
        step="publisher",
        payload={
            "topic": "GTA 6",
            "script": {"title": "GTA 6"},
            "quality_passed": False,
            "video_review_passed": True,
            "retention_passed": True,
            "render_ref": {"key": "renders/final.mp4", "bucket": "contentos"},
            "seo_package": {"title": "GTA 6", "description": "demo", "hashtags": ["gta6"]},
        },
    )
    out = await handler.execute(task)
    assert out.data["publication"]["status"] == "blocked_qa"
    assert out.data["publish_blocked"] is True
