"""Provider Factory — Strategy + Dependency Injection.

Select implementation via environment variables without changing agents.
When USE_AI_GATEWAY=true, routes through the AI Gateway (V2) with V1 fallback.
"""

import os
from functools import lru_cache
from typing import TYPE_CHECKING

from contentos_shared.providers.protocols import SpeechProvider, SubtitleProvider, TextProvider

if TYPE_CHECKING:
    pass


def _use_ai_gateway() -> bool:
    # Phase 9: gateway is default. Set USE_AI_GATEWAY=false only for emergency direct mode.
    return os.getenv("USE_AI_GATEWAY", "true").lower() in ("true", "1", "yes")

_TEXT_REGISTRY: dict[str, str] = {
    "ollama": "contentos_shared.providers.ai.ollama.OllamaTextProvider",
    "openai": "contentos_shared.providers.ai.openai.OpenAITextProvider",
}

_SPEECH_REGISTRY: dict[str, str] = {
    "piper": "contentos_shared.providers.speech.piper.PiperSpeechProvider",
    "elevenlabs": "contentos_shared.providers.speech.elevenlabs.ElevenLabsSpeechProvider",
}

_SUBTITLE_REGISTRY: dict[str, str] = {
    "local": "contentos_shared.providers.subtitle.local_whisper.LocalWhisperProvider",
    "whisper": "contentos_shared.providers.subtitle.local_whisper.LocalWhisperProvider",
    "openai": "contentos_shared.providers.subtitle.openai_whisper.OpenAIWhisperProvider",
}


def _load_class(dotted_path: str) -> type:
    module_path, class_name = dotted_path.rsplit(".", 1)
    import importlib

    module = importlib.import_module(module_path)
    return getattr(module, class_name)


class ProviderFactory:
    """Creates provider instances based on configuration."""

    def __init__(
        self,
        text_provider: str | None = None,
        speech_provider: str | None = None,
        subtitle_provider: str | None = None,
    ) -> None:
        self._text_key = (text_provider or os.getenv("TEXT_PROVIDER", "ollama")).lower()
        self._speech_key = (speech_provider or os.getenv("SPEECH_PROVIDER", "piper")).lower()
        self._subtitle_key = (subtitle_provider or os.getenv("SUBTITLE_PROVIDER", "local")).lower()

    def text(self, *, agent: str | None = None) -> TextProvider:
        if _use_ai_gateway():
            from contentos_ai_client.providers import GatewayTextProvider

            return GatewayTextProvider(provider_key=self._text_key, agent=agent)
        path = _TEXT_REGISTRY.get(self._text_key)
        if path is None:
            raise ValueError(f"Unknown TEXT_PROVIDER: {self._text_key}. Options: {list(_TEXT_REGISTRY)}")
        return _load_class(path)()

    def speech(self, *, agent: str | None = None) -> SpeechProvider:
        if _use_ai_gateway():
            from contentos_ai_client.providers import GatewaySpeechProvider

            return GatewaySpeechProvider(provider_key=self._speech_key, agent=agent)
        path = _SPEECH_REGISTRY.get(self._speech_key)
        if path is None:
            raise ValueError(f"Unknown SPEECH_PROVIDER: {self._speech_key}. Options: {list(_SPEECH_REGISTRY)}")
        return _load_class(path)()

    def subtitle(self, *, agent: str | None = None) -> SubtitleProvider:
        if _use_ai_gateway():
            from contentos_ai_client.providers import GatewaySubtitleProvider

            return GatewaySubtitleProvider(provider_key=self._subtitle_key, agent=agent)
        path = _SUBTITLE_REGISTRY.get(self._subtitle_key)
        if path is None:
            raise ValueError(f"Unknown SUBTITLE_PROVIDER: {self._subtitle_key}. Options: {list(_SUBTITLE_REGISTRY)}")
        return _load_class(path)()

    def status(self) -> dict[str, str]:
        mode = "ai-gateway" if _use_ai_gateway() else "direct"
        return {
            "text": self._text_key,
            "speech": self._speech_key,
            "subtitle": self._subtitle_key,
            "mode": mode,
        }


@lru_cache(maxsize=1)
def get_provider_factory() -> ProviderFactory:
    return ProviderFactory()
