"""V5.1.5 — Voice Studio dashboard + preview API."""

from __future__ import annotations

from uuid import uuid4

import pytest
from contentos_gateway.api.routes.voice_profiles import VoicePreviewBody, _resolve_preview_profile
from contentos_shared.voice.profile import BUILTIN_PROFILES, VoiceProfileSettings


def test_resolve_preview_profile_builtin_overrides():
    body = VoicePreviewBody(text="hello", builtin_name="hype", speed=1.3, pause_ms=100)
    profile = _resolve_preview_profile(body, None)
    assert profile.name == "hype"
    assert profile.speed == 1.3
    assert profile.pause_ms == 100
    assert profile.pitch_semitones == BUILTIN_PROFILES["hype"].pitch_semitones


def test_resolve_preview_profile_db_base_with_overrides():
    base = VoiceProfileSettings(
        name="custom",
        provider="piper",
        voice_id="voice-a",
        speed=1.0,
        pitch_semitones=0.0,
        pause_ms=300,
        profile_id=str(uuid4()),
    )
    body = VoicePreviewBody(text="test", pitch_semitones=2.0)
    profile = _resolve_preview_profile(body, base)
    assert profile.voice_id == "voice-a"
    assert profile.pitch_semitones == 2.0


def test_voice_preview_body_validates_speed():
    body = VoicePreviewBody(text="ok", speed=3.0)
    assert body.speed == 2.0


@pytest.mark.asyncio
async def test_preview_voice_profile_endpoint(monkeypatch):
    from contentos_gateway.api.routes import voice_profiles as routes

    async def fake_synth(_provider, _text, _profile):
        return b"fake-audio"

    monkeypatch.setattr(routes, "synthesize_narration", fake_synth)
    monkeypatch.setattr(
        routes,
        "build_profiled_speech_provider",
        lambda profile, agent="voice": object(),
    )

    body = VoicePreviewBody(text="Preview do estúdio.", builtin_name="calm")
    response = await routes.preview_voice_profile(body, db=None, _user=object())
    assert response.body == b"fake-audio"
    assert response.media_type == "audio/mpeg"
