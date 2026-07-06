"""Tests for Multi Content video (V4.2.2 / Epic 2b)."""

from __future__ import annotations

from uuid import uuid4

from contentos_events.domain.event_types import ALL_TYPES, VIDEO_VARIANTS_GENERATED, resolve_event_type
from contentos_intelligence.application.multi_content_video.heuristics import GENERATORS, generate_variant
from contentos_intelligence.application.multi_content_video.service import MultiContentVideoService
from contentos_intelligence.domain.context import IntelligenceContext
from contentos_intelligence.domain.video_variants import VIDEO_PLATFORMS
from contentos_shared.enums import PipelineStep
from contentos_shared.workflow_templates import BUILTIN_TEMPLATES, get_builtin, list_builtin_names


def test_video_platforms_complete():
    assert VIDEO_PLATFORMS == frozenset({"tiktok", "youtube_shorts", "instagram_reels"})
    assert set(GENERATORS.keys()) == set(VIDEO_PLATFORMS)


def test_youtube_shorts_heuristic_from_render():
    variant = generate_variant(
        "youtube_shorts",
        {
            "topic": "GTA 6",
            "render_ref": {"id": "render-abc", "url": "s3://bucket/video.mp4"},
            "publication": {
                "title": "GTA 6 revelado",
                "description": "O mapa é gigante e ninguém esperava.",
                "hashtags": ["gta6", "gaming"],
            },
            "duration_seconds": 45,
        },
    )
    assert variant.platform == "youtube_shorts"
    assert variant.crop_spec.width == 1080
    assert variant.crop_spec.height == 1920
    assert variant.metadata.get("is_short") is True
    assert variant.metadata.get("ready_to_publish") is True
    assert variant.render_ref is not None
    assert "shorts" in [h.lower() for h in variant.hashtags]


def test_multi_content_video_service_generates_all_platforms():
    service = MultiContentVideoService()
    ctx = IntelligenceContext(
        project_id=uuid4(),
        pipeline_id=uuid4(),
        topic="IA no trabalho",
        payload={
            "script": {
                "title": "ChatGPT na empresa",
                "full_text": "A IA mudou o marketing.",
            },
            "publication": {"title": "ChatGPT na empresa", "hashtags": ["ia", "trabalho"]},
        },
    )
    report = service.generate(ctx)
    assert len(report.variants) == 3
    platforms = {v.platform for v in report.variants}
    assert platforms == set(VIDEO_PLATFORMS)


def test_v4_multi_full_template():
    assert "v4-multi-full" in BUILTIN_TEMPLATES
    tpl = get_builtin("v4-multi-full")
    assert tpl is not None
    steps = tpl["steps"]
    assert steps[-3] == "publisher"
    assert steps[-2] == "multi_content"
    assert steps[-1] == "multi_content_video"
    assert len(steps) == 19
    assert tpl["config"]["enable_multi_content_video"] is True


def test_v4_multi_full_ordered_enum():
    steps = [s.value for s in PipelineStep.v4_multi_full_ordered()]
    assert steps[-1] == "multi_content_video"
    assert steps[-2] == "multi_content"


def test_list_builtin_includes_v4_multi_full():
    assert "v4-multi-full" in list_builtin_names()


def test_video_variants_generated_event_registered():
    assert VIDEO_VARIANTS_GENERATED in ALL_TYPES
    assert resolve_event_type("VideoVariantsGenerated") == VIDEO_VARIANTS_GENERATED
