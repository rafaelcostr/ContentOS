"""Post Manager tests — Growth OS Fase 12."""

from __future__ import annotations

from uuid import uuid4

import pytest
from contentos_growth.application.post_manager import (
    build_post_payload,
    generate_post_report,
    is_text_content_type,
    is_video_content_type,
    plan_calendar_post,
    resolve_text_formats,
)
from contentos_growth.domain import GrowthStrategy


def test_is_text_and_video_content_types():
    assert is_text_content_type("post")
    assert is_text_content_type("thread")
    assert is_video_content_type("short")
    assert is_video_content_type("reel")
    assert not is_text_content_type("video")


def test_resolve_text_formats_by_platform():
    assert resolve_text_formats("x", "post") == ["thread_x"]
    assert resolve_text_formats("linkedin", "post") == ["linkedin_post"]
    assert resolve_text_formats("youtube", "short", include_companion=True) == ["seo_article"]


def test_plan_calendar_post_text_mode():
    item = {
        "id": str(uuid4()),
        "project_id": str(uuid4()),
        "title": "Dica de produtividade",
        "topic": "Como focar no trabalho remoto",
        "metadata": {"platform": "linkedin", "content_type": "post"},
    }
    plan = plan_calendar_post(calendar_item=item, strategy=None)
    assert plan.mode == "text"
    assert plan.text_formats == ("linkedin_post",)
    assert plan.payload["topic"] == "Como focar no trabalho remoto"


def test_build_post_payload_includes_growth_fields():
    strategy = GrowthStrategy(project_id=str(uuid4()), positioning="Autoridade B2B", goals=["Leads"])
    item = {
        "id": str(uuid4()),
        "project_id": strategy.project_id,
        "title": "Post",
        "topic": "IA para marketing",
        "metadata": {"platform": "x", "content_type": "post"},
    }
    payload = build_post_payload(calendar_item=item, strategy=strategy)
    assert payload["growth_source"] == "growth_post_manager"
    assert payload["script"]["hook"]
    assert payload["objective"] == "Autoridade B2B"


def test_generate_post_report_uses_multi_content():
    item = {
        "id": str(uuid4()),
        "project_id": str(uuid4()),
        "title": "Thread sobre IA",
        "topic": "IA generativa em 2026",
        "metadata": {"platform": "x", "content_type": "post"},
    }
    plan = plan_calendar_post(calendar_item=item, strategy=None)
    result = generate_post_report(plan=plan)
    assert result.artifacts
    assert result.artifacts[0]["format"] == "thread_x"
    assert "IA generativa" in result.artifacts[0]["content"] or "Thread" in result.artifacts[0]["title"]


def test_generate_post_report_requires_formats():
    item = {
        "id": str(uuid4()),
        "project_id": str(uuid4()),
        "title": "TikTok",
        "topic": "Trend",
        "metadata": {"platform": "tiktok", "content_type": "post"},
    }
    plan = plan_calendar_post(calendar_item=item, strategy=None)
    with pytest.raises(ValueError, match="No text formats"):
        generate_post_report(plan=plan)
