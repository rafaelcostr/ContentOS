"""Provider contracts — Dependency Inversion (SOLID).

Agents depend only on these Protocols, never on Ollama, Whisper, or Piper directly.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class TextProvider(Protocol):
    """LLM for research, scripts, scenes, and publisher metadata."""

    async def chat_json(self, system: str, user: str) -> dict[str, Any]:
        """Return structured JSON from the model."""
        ...


@runtime_checkable
class SpeechProvider(Protocol):
    """Text-to-speech for voice narration."""

    async def text_to_speech(self, text: str) -> bytes:
        """Return audio bytes (typically MP3)."""
        ...


@runtime_checkable
class SubtitleProvider(Protocol):
    """Speech-to-text for synchronized captions."""

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.mp3") -> dict[str, Any]:
        """Return transcription with segments and timestamps."""
        ...
