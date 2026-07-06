"""AI provider protocols — Dependency Inversion."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class AIProvider(Protocol):
    """Base marker for all AI providers."""

    name: str


@runtime_checkable
class TextProvider(AIProvider, Protocol):
    async def chat_json(self, system: str, user: str) -> dict[str, Any]: ...


@runtime_checkable
class SpeechProvider(AIProvider, Protocol):
    async def text_to_speech(self, text: str) -> bytes: ...


@runtime_checkable
class SubtitleProvider(AIProvider, Protocol):
    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.mp3") -> dict[str, Any]: ...


@runtime_checkable
class VisionProvider(AIProvider, Protocol):
    async def analyze_image(self, image_bytes: bytes, prompt: str) -> dict[str, Any]: ...


@runtime_checkable
class ImageProvider(AIProvider, Protocol):
    async def generate_image(self, prompt: str, size: str = "1024x1024") -> bytes: ...


@runtime_checkable
class EmbeddingProvider(AIProvider, Protocol):
    async def embed(self, text: str) -> list[float]: ...
