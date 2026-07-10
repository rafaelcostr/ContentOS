"""Tests for Channel Memory — Growth OS Fase 6."""

from __future__ import annotations

from uuid import uuid4

from contentos_growth.channel_memory_model import (
    ChannelMemoryData,
    extract_patterns_from_media,
)


def test_format_channel_context_full():
    memory = ChannelMemoryData(
        channel_id=uuid4(),
        project_id=uuid4(),
        top_hooks=["Você não vai acreditar", "3 erros fatais"],
        top_ctas=["inscreva", "comente"],
        top_hashtags=["#financas", "#investir"],
        best_posting_hours=[18, 20],
        insights=["Postar shorts 3x por semana"],
        notes="Evitar tom agressivo",
    )
    ctx = memory.format_channel_context()
    assert "Você não vai acreditar" in ctx
    assert "#financas" in ctx
    assert "18h" in ctx
    assert "Evitar tom agressivo" in ctx


def test_extract_patterns_from_media_ranks_by_engagement():
    media = [
        {"title": "Low", "external_media_id": "a", "metrics": {"title": "Low", "engagement_rate": 0.01}},
        {"title": "High", "external_media_id": "b", "metrics": {"title": "High", "engagement_rate": 0.09, "published_at": "2026-07-01T20:00:00Z"}},
        {"title": "Mid", "external_media_id": "c", "metrics": {"title": "Mid", "engagement_rate": 0.05}},
    ]
    patterns = extract_patterns_from_media(media)
    assert patterns["winning_videos"][0]["title"] == "High"
    assert patterns["top_hooks"][0] == "High"
    assert 20 in patterns["best_posting_hours"]


def test_apply_patch_updates_notes():
    memory = ChannelMemoryData(channel_id=uuid4(), project_id=uuid4(), notes="old")
    memory.apply_patch({"notes": "new note", "top_hooks": ["hook a"]})
    assert memory.notes == "new note"
    assert memory.top_hooks == ["hook a"]


def test_merge_seed_preserves_notes():
    memory = ChannelMemoryData(channel_id=uuid4(), project_id=uuid4(), notes="manual")
    memory.merge_seed(
        winning_videos=[{"title": "Winner"}],
        losing_videos=[],
        top_hooks=["hook"],
        top_ctas=["cta"],
        top_themes=["theme"],
        top_hashtags=["#tag"],
        best_posting_hours=[9],
        insights=["insight"],
    )
    assert memory.notes == "manual"
    assert memory.winning_videos[0]["title"] == "Winner"
    assert memory.top_hooks == ["hook"]


def test_to_dict_includes_preview():
    memory = ChannelMemoryData(channel_id=uuid4(), project_id=uuid4(), top_hooks=["x"])
    payload = memory.to_dict()
    assert "channel_context_preview" in payload
    assert "x" in payload["channel_context_preview"]


def test_channel_memory_patch_body_fields():
    from contentos_gateway.api.routes.channel_memory import ChannelMemoryPatchBody

    body = ChannelMemoryPatchBody(notes="test", top_hooks=["a"])
    assert body.notes == "test"
    assert body.top_hooks == ["a"]


def test_growth_service_analyze_channel_signature_accepts_db():
    import inspect

    from contentos_growth.application.service import GrowthService

    params = inspect.signature(GrowthService.analyze_channel).parameters
    assert "db" in params
