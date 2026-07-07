"""Voice profile domain — speed, pitch and pause controls (V5.1.1)."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

VALID_PROVIDERS = frozenset({"piper", "elevenlabs"})
SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+")


@dataclass(frozen=True)
class VoiceProfileSettings:
    name: str = "default"
    provider: str = "piper"
    voice_id: str = ""
    speed: float = 1.0
    pitch_semitones: float = 0.0
    pause_ms: int = 300
    is_builtin: bool = False
    profile_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> VoiceProfileSettings:
        if not data:
            return cls.default()
        return cls(
            name=str(data.get("name") or "custom"),
            provider=str(data.get("provider") or "piper").lower(),
            voice_id=str(data.get("voice_id") or data.get("voice") or ""),
            speed=normalize_speed(data.get("speed")),
            pitch_semitones=normalize_pitch(data.get("pitch_semitones", data.get("pitch"))),
            pause_ms=normalize_pause_ms(data.get("pause_ms", data.get("pause"))),
            is_builtin=bool(data.get("is_builtin")),
            profile_id=str(data["profile_id"]) if data.get("profile_id") else None,
        )

    @classmethod
    def default(cls) -> VoiceProfileSettings:
        return BUILTIN_PROFILES["default"]


BUILTIN_PROFILES: dict[str, VoiceProfileSettings] = {
    "default": VoiceProfileSettings(
        name="default",
        provider="piper",
        voice_id="",
        speed=1.0,
        pitch_semitones=0.0,
        pause_ms=300,
        is_builtin=True,
    ),
    "hype": VoiceProfileSettings(
        name="hype",
        provider="piper",
        voice_id="",
        speed=1.15,
        pitch_semitones=1.0,
        pause_ms=150,
        is_builtin=True,
    ),
    "calm": VoiceProfileSettings(
        name="calm",
        provider="piper",
        voice_id="",
        speed=0.92,
        pitch_semitones=-1.0,
        pause_ms=500,
        is_builtin=True,
    ),
    "documentary": VoiceProfileSettings(
        name="documentary",
        provider="piper",
        voice_id="",
        speed=0.95,
        pitch_semitones=-2.0,
        pause_ms=450,
        is_builtin=True,
    ),
}


def normalize_speed(value: Any) -> float:
    try:
        speed = float(value)
    except (TypeError, ValueError):
        return 1.0
    return max(0.5, min(2.0, speed))


def normalize_pitch(value: Any) -> float:
    try:
        pitch = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(-12.0, min(12.0, pitch))


def normalize_pause_ms(value: Any) -> int:
    try:
        pause = int(value)
    except (TypeError, ValueError):
        return 300
    return max(0, min(2000, pause))


def split_sentences(text: str) -> list[str]:
    stripped = (text or "").strip()
    if not stripped:
        return []
    parts = [part.strip() for part in SENTENCE_SPLIT.split(stripped) if part.strip()]
    return parts or [stripped]


def resolve_builtin_profile(name: str | None) -> VoiceProfileSettings:
    key = (name or "default").strip().lower()
    return BUILTIN_PROFILES.get(key, BUILTIN_PROFILES["default"])


def list_builtin_profiles() -> list[VoiceProfileSettings]:
    return list(BUILTIN_PROFILES.values())
