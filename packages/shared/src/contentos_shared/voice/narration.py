"""Narration synthesis with voice profile controls (V5.1.1)."""

from __future__ import annotations

import os
from typing import Any, Protocol, runtime_checkable

from contentos_shared.providers.builder import build_speech_provider
from contentos_shared.voice.audio_processor import apply_speed_pitch, concat_with_pauses
from contentos_shared.voice.profile import (
    VoiceProfileSettings,
    normalize_pause_ms,
    resolve_builtin_profile,
    split_sentences,
)


@runtime_checkable
class SpeechSynth(Protocol):
    async def text_to_speech(self, text: str) -> bytes: ...


async def synthesize_narration(
    provider: SpeechSynth,
    text: str,
    profile: VoiceProfileSettings,
) -> bytes:
    stripped = (text or "").strip()
    if not stripped:
        return b""

    sentences = split_sentences(stripped)
    pause_ms = normalize_pause_ms(profile.pause_ms)
    if pause_ms > 0 and len(sentences) > 1:
        chunks = [await provider.text_to_speech(sentence) for sentence in sentences]
        audio = await concat_with_pauses(chunks, pause_ms)
    else:
        audio = await provider.text_to_speech(stripped)

    return await apply_speed_pitch(
        audio,
        speed=profile.speed,
        pitch_semitones=profile.pitch_semitones,
    )


def build_profiled_speech_provider(profile: VoiceProfileSettings, *, agent: str = "voice") -> SpeechSynth:
    model = profile.voice_id or None
    return build_speech_provider(profile.provider, model, agent=agent)


def resolve_voice_profile(payload: dict[str, Any], project_id=None) -> VoiceProfileSettings:
    if isinstance(payload.get("voice_profile"), dict):
        return VoiceProfileSettings.from_dict(payload["voice_profile"])

    profile_id = payload.get("voice_profile_id")
    if profile_id:
        loaded = load_voice_profile_sync(str(profile_id))
        if loaded:
            return loaded

    if project_id:
        project_default = load_project_default_voice_profile_sync(project_id)
        if project_default:
            return project_default
        from contentos_shared.voice.project_library import load_project_builtin_default_sync

        builtin_default = load_project_builtin_default_sync(project_id)
        if builtin_default:
            return builtin_default

    preset = payload.get("voice_profile_name") or os.getenv("DEFAULT_VOICE_PROFILE", "default")
    return resolve_builtin_profile(str(preset))


def load_voice_profile_sync(profile_id: str) -> VoiceProfileSettings | None:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url or not profile_id:
        return None
    try:
        from uuid import UUID

        profile_uuid = UUID(str(profile_id))
    except ValueError:
        return None
    url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace(
        "postgresql://", "postgresql+psycopg2://"
    )
    try:
        from contentos_database.models import VoiceProfile
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        engine = create_engine(url, pool_pre_ping=True)
        with Session(engine) as session:
            row = session.get(VoiceProfile, profile_uuid)
            if not row:
                return None
            return _row_to_settings(row)
    except Exception:
        return None


def load_project_default_voice_profile_sync(project_id) -> VoiceProfileSettings | None:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url or not project_id:
        return None
    url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace(
        "postgresql://", "postgresql+psycopg2://"
    )
    try:
        from contentos_database.models import VoiceProfile
        from sqlalchemy import create_engine, select
        from sqlalchemy.orm import Session

        engine = create_engine(url, pool_pre_ping=True)
        with Session(engine) as session:
            row = session.execute(
                select(VoiceProfile)
                .where(
                    VoiceProfile.project_id == project_id,
                    VoiceProfile.is_default.is_(True),
                )
                .limit(1)
            ).scalar_one_or_none()
            if not row:
                return None
            return _row_to_settings(row)
    except Exception:
        return None


def _row_to_settings(row) -> VoiceProfileSettings:
    return VoiceProfileSettings(
        name=row.name,
        provider=row.provider,
        voice_id=row.voice_id or "",
        speed=float(row.speed),
        pitch_semitones=float(row.pitch_semitones),
        pause_ms=int(row.pause_ms),
        profile_id=str(row.id),
    )
