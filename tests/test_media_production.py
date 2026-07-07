"""Media production policy — placeholders, clip coverage, handler guards."""

from uuid import uuid4

import pytest
from contentos_agents.handlers.editor import EditorAgentHandler
from contentos_agents.handlers.takes import TakesAgentHandler
from contentos_shared.enums import AssetCategory
from contentos_shared.media_production import (
    is_placeholder_asset_key,
    render_allow_placeholder,
    require_clip_coverage,
    require_media_assets,
    scene_clip_coverage,
)
from contentos_shared.providers.ffmpeg_filters import RenderSpec, SceneSegment
from contentos_shared.providers.ffmpeg_provider import FFmpegProvider, PlaceholderRenderBlockedError
from contentos_shared.schemas.agent import AgentTaskInput


def test_is_placeholder_asset_key():
    assert is_placeholder_asset_key(None) is True
    assert is_placeholder_asset_key("") is True
    assert is_placeholder_asset_key("takes/placeholder_0.mp4") is True
    assert is_placeholder_asset_key("takes/real_clip.mp4") is False


def test_scene_clip_coverage_ignores_placeholder_keys():
    labels = ["intro", "cta"]
    clips = [
        {"label": "intro", "asset_key": "takes/real.mp4"},
        {"label": "cta", "asset_key": "takes/placeholder_1.mp4"},
    ]
    coverage = scene_clip_coverage(labels, clips)
    assert coverage["passed"] is False
    assert coverage["missing_scene_labels"] == ["cta"]


def test_require_clip_coverage_follows_production(monkeypatch):
    monkeypatch.delenv("MEDIA_REQUIRE_CLIPS", raising=False)
    monkeypatch.delenv("MEDIA_REQUIRE_ASSETS", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    assert require_clip_coverage() is False
    monkeypatch.setenv("APP_ENV", "production")
    assert require_clip_coverage() is True
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("MEDIA_REQUIRE_CLIPS", "false")
    assert require_clip_coverage() is False


def test_render_allow_placeholder_defaults(monkeypatch):
    monkeypatch.delenv("RENDER_ALLOW_PLACEHOLDER", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    assert render_allow_placeholder() is True
    monkeypatch.setenv("APP_ENV", "production")
    assert render_allow_placeholder() is False


def test_require_media_assets_follows_production(monkeypatch):
    monkeypatch.delenv("MEDIA_REQUIRE_ASSETS", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    assert require_media_assets() is True


@pytest.mark.asyncio
async def test_ffmpeg_blocks_placeholder_scene_in_production(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENV", "production")
    provider = FFmpegProvider()
    spec = RenderSpec(width=1080, height=1920, fps=60, total_duration=5)
    scene = SceneSegment(index=0, duration=3, label="intro", clip_path=None)
    with pytest.raises(PlaceholderRenderBlockedError, match="intro"):
        await provider._render_scene_segment(spec, scene, tmp_path / "out.mp4", tmp_path)


@pytest.mark.asyncio
async def test_takes_fails_when_clips_missing_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")

    class EmptyProvider:
        def __init__(self, *args, **kwargs):
            pass

        async def get_clips_for_scenes(self, theme, labels):
            return []

    monkeypatch.setattr("contentos_agents.handlers.takes.MinIOTakeLibraryProvider", EmptyProvider)

    handler = TakesAgentHandler()
    handler.get_asset_manager = lambda: object()

    task = AgentTaskInput(
        job_id=uuid4(),
        pipeline_id=uuid4(),
        project_id=uuid4(),
        step="takes",
        payload={
            "scenes": [{"label": "intro"}, {"label": "cta"}],
            "topic": "gaming",
        },
    )
    out = await handler.execute(task)
    assert out.status == "failed"
    assert "insufficient clips" in (out.error or "")


@pytest.mark.asyncio
async def test_takes_rejects_placeholder_asset_keys_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    handler = TakesAgentHandler()
    handler.get_asset_manager = lambda: object()

    task = AgentTaskInput(
        job_id=uuid4(),
        pipeline_id=uuid4(),
        project_id=uuid4(),
        step="takes",
        payload={
            "scenes": [{"label": "intro"}],
            "topic": "gaming",
            "asset_matches": [
                {
                    "scene_label": "intro",
                    "selected": {"asset_key": "takes/placeholder_0.mp4", "bucket": "contentos"},
                }
            ],
        },
    )
    out = await handler.execute(task)
    assert out.status == "failed"
    assert "insufficient clips" in (out.error or "")


@pytest.mark.asyncio
async def test_editor_blocks_placeholder_render_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")

    class FakeAssetManager:
        async def get(self, ref):
            if ref.category in {AssetCategory.AUDIO, AssetCategory.CAPTIONS}:
                return b"fake-bytes"
            raise FileNotFoundError("missing clip")

        async def exists(self, ref):
            return False

    handler = EditorAgentHandler()
    handler.get_asset_manager = lambda: FakeAssetManager()

    task = AgentTaskInput(
        job_id=uuid4(),
        pipeline_id=uuid4(),
        project_id=uuid4(),
        step="editor",
        payload={
            "script": {"duration_seconds": 20},
            "audio_ref": {"key": "audio/narration.mp3", "bucket": "contentos"},
            "scenes": [{"label": "intro", "start_seconds": 0, "end_seconds": 5}],
            "clips": [{"label": "intro", "asset_key": "takes/missing.mp4", "bucket": "contentos"}],
        },
    )
    out = await handler.execute(task)
    assert out.status == "failed"
    assert "placeholder render blocked" in (out.error or "")
