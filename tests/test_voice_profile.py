"""V5.1.1 — Voice profiles (speed, pitch, pause)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from contentos_shared.voice.profile import (
    VoiceProfileSettings,
    normalize_pause_ms,
    normalize_pitch,
    normalize_speed,
    resolve_builtin_profile,
    split_sentences,
)


def test_normalize_speed_clamps():
    assert normalize_speed(3.0) == 2.0
    assert normalize_speed(0.1) == 0.5
    assert normalize_speed("1.2") == 1.2


def test_normalize_pitch_clamps():
    assert normalize_pitch(20) == 12.0
    assert normalize_pitch(-20) == -12.0


def test_normalize_pause_ms_clamps():
    assert normalize_pause_ms(5000) == 2000
    assert normalize_pause_ms(-10) == 0


def test_split_sentences():
    parts = split_sentences("GTA 6 chegou! Será incrível. Prepare-se?")
    assert len(parts) == 3
    assert parts[0].endswith("!")


def test_builtin_profiles_exist():
    default = resolve_builtin_profile("default")
    hype = resolve_builtin_profile("hype")
    assert default.speed == 1.0
    assert hype.speed > default.speed
    assert hype.pause_ms < default.pause_ms


def test_voice_profile_from_dict():
    profile = VoiceProfileSettings.from_dict(
        {
            "name": "custom",
            "provider": "elevenlabs",
            "voice_id": "voice-1",
            "speed": 1.1,
            "pitch_semitones": 2,
            "pause_ms": 250,
        }
    )
    assert profile.provider == "elevenlabs"
    assert profile.voice_id == "voice-1"
    assert profile.speed == 1.1


@pytest.mark.asyncio
async def test_synthesize_narration_single_chunk():
    from contentos_shared.voice.narration import synthesize_narration

    class FakeProvider:
        async def text_to_speech(self, text: str) -> bytes:
            return f"audio:{text}".encode()

    profile = VoiceProfileSettings(pause_ms=0)
    audio = await synthesize_narration(FakeProvider(), "Uma frase só.", profile)
    assert audio.startswith(b"audio:")


@pytest.mark.asyncio
async def test_synthesize_narration_with_pauses(monkeypatch):
    from contentos_shared.voice import narration

    calls: list[str] = []

    class FakeProvider:
        async def text_to_speech(self, text: str) -> bytes:
            calls.append(text)
            return f"chunk-{len(calls)}".encode()

    async def fake_concat(chunks, pause_ms):
        assert pause_ms == 200
        assert len(chunks) == 2
        return b"merged"

    monkeypatch.setattr(narration, "concat_with_pauses", fake_concat)

    async def fake_apply(audio, **kwargs):
        return audio

    monkeypatch.setattr(narration, "apply_speed_pitch", fake_apply)

    profile = VoiceProfileSettings(pause_ms=200)
    audio = await narration.synthesize_narration(
        FakeProvider(),
        "Primeira frase. Segunda frase.",
        profile,
    )
    assert audio == b"merged"
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_voice_handler_uses_profile(monkeypatch):
    from contentos_agents.handlers.voice import VoiceAgentHandler
    from contentos_shared.schemas.agent import AgentTaskInput

    class FakeProvider:
        provider_key = "piper"

        async def text_to_speech(self, text: str) -> bytes:
            return b"mp3-bytes"

    async def fake_synth(provider, text, profile):
        assert profile.name == "hype"
        return b"processed"

    monkeypatch.setattr(
        "contentos_agents.handlers.voice.build_profiled_speech_provider",
        lambda profile, agent="voice": FakeProvider(),
    )
    monkeypatch.setattr("contentos_agents.handlers.voice.synthesize_narration", fake_synth)

    handler = VoiceAgentHandler()

    async def fake_store(_self, category, data, meta):
        return type("R", (), {"key": "audio/narration.mp3", "bucket": "contentos", "id": uuid4()})()

    handler.get_asset_manager = lambda: type("M", (), {"store": fake_store})()
    handler._record_speech_cost = lambda *args, **kwargs: None

    output = await handler.execute(
        AgentTaskInput(
            job_id=uuid4(),
            pipeline_id=uuid4(),
            project_id=uuid4(),
            step="voice",
            payload={
                "script": {"full_text": "Texto de teste."},
                "voice_profile_name": "hype",
            },
        )
    )

    assert output.status == "completed"
    assert output.data["voice_profile"]["name"] == "hype"
