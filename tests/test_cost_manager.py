"""Tests for Cost Manager (incl. Tier A4 modalities)."""

from uuid import uuid4

from contentos_cost.application.cost_tracker import CostTracker
from contentos_cost.infrastructure.pricing_table import (
    estimate_cost_usd,
    estimate_image_cost_usd,
    estimate_speech_cost_usd,
    estimate_subtitle_cost_usd,
    estimate_tokens,
)


def test_estimate_tokens():
    assert estimate_tokens("hello world") >= 2
    assert estimate_tokens("") == 0


def test_local_provider_zero_cost():
    cost = estimate_cost_usd("ollama", "qwen2.5:7b", 1000, 500)
    assert cost == 0.0


def test_cache_hit_zero_cost():
    cost = estimate_cost_usd("openai", "gpt-4o", 1000, 500, from_cache=True)
    assert cost == 0.0


def test_openai_has_cost():
    cost = estimate_cost_usd("openai", "gpt-4o", 1000, 1000)
    assert cost > 0


def test_speech_local_zero_cloud_positive():
    assert estimate_speech_cost_usd("piper", 5000) == 0.0
    assert estimate_speech_cost_usd("elevenlabs", 1000) > 0


def test_subtitle_local_zero_cloud_positive():
    assert estimate_subtitle_cost_usd("local", audio_bytes=100_000) == 0.0
    assert estimate_subtitle_cost_usd("openai", duration_seconds=60) > 0


def test_image_local_zero_cloud_positive():
    assert estimate_image_cost_usd("local") == 0.0
    assert estimate_image_cost_usd("openai", 2) > 0


def test_record_text_chat_returns_entry():
    tracker = CostTracker()
    entry = tracker.record_text_chat(
        project_id=uuid4(),
        pipeline_id=uuid4(),
        job_id=uuid4(),
        agent="research",
        provider="ollama",
        model="qwen2.5:7b",
        system="sys",
        user="user prompt",
        response_data={"topics": []},
        duration_ms=120,
        from_cache=False,
    )
    assert entry.estimated_cost_usd == 0.0
    assert entry.tokens_input > 0
    assert entry.agent == "research"


def test_record_speech_entry():
    tracker = CostTracker()
    entry = tracker.record_speech(
        project_id=uuid4(),
        pipeline_id=uuid4(),
        job_id=uuid4(),
        agent="voice",
        provider="piper",
        model="pt_BR-faber-medium",
        text="Olá mundo " * 20,
        audio_bytes=12_000,
        duration_ms=80,
    )
    assert entry.operation == "speech_tts"
    assert entry.tokens_input > 0
    assert entry.estimated_cost_usd == 0.0


def test_record_subtitle_entry():
    tracker = CostTracker()
    entry = tracker.record_subtitle(
        project_id=uuid4(),
        pipeline_id=uuid4(),
        job_id=uuid4(),
        agent="subtitle",
        provider="local",
        model="large-v3",
        audio_bytes=50_000,
        segment_count=12,
        duration_ms=200,
        duration_seconds=45,
    )
    assert entry.operation == "subtitle_stt"
    assert entry.tokens_output == 12


def test_record_image_entry():
    tracker = CostTracker()
    entry = tracker.record_image(
        project_id=uuid4(),
        pipeline_id=uuid4(),
        job_id=uuid4(),
        agent="thumbnail",
        provider="local",
        model="pillow-thumbnail",
        image_bytes=40_000,
        duration_ms=50,
    )
    assert entry.operation == "image_generate"
    assert entry.tokens_output == 1

