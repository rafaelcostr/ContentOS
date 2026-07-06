"""External service adapters — Dependency Inversion.

Structure:
    providers/
    ├── protocols.py      # TextProvider, SpeechProvider, SubtitleProvider
    ├── factory.py        # ProviderFactory (Strategy + DI)
    ├── health.py         # Health checks for local stack
    ├── ai/               # Ollama, OpenAI
    ├── speech/           # Piper, ElevenLabs
    └── subtitle/         # Local Whisper, OpenAI Whisper
"""

from contentos_shared.providers.factory import ProviderFactory, get_provider_factory
from contentos_shared.providers.protocols import SpeechProvider, SubtitleProvider, TextProvider

__all__ = [
    "TextProvider",
    "SpeechProvider",
    "SubtitleProvider",
    "ProviderFactory",
    "get_provider_factory",
    "OpenAIProvider",
    "ElevenLabsProvider",
    "WhisperProvider",
]


def __getattr__(name: str):
    """Lazy backward-compatible aliases."""
    if name == "OpenAIProvider":
        from contentos_shared.providers.ai.openai import OpenAITextProvider

        return OpenAITextProvider
    if name == "ElevenLabsProvider":
        from contentos_shared.providers.speech.elevenlabs import ElevenLabsSpeechProvider

        return ElevenLabsSpeechProvider
    if name == "WhisperProvider":
        from contentos_shared.providers.subtitle.openai_whisper import OpenAIWhisperProvider

        return OpenAIWhisperProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
