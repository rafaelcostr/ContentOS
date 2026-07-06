"""Build provider instances with explicit provider key and model.

Phase 9: gateway is the default path. Direct adapters only when USE_AI_GATEWAY=false.
"""

import os

from contentos_shared.providers.protocols import SpeechProvider, SubtitleProvider, TextProvider


def _use_ai_gateway() -> bool:
    # Default true — agents must not call Ollama/Piper/Whisper directly.
    return os.getenv("USE_AI_GATEWAY", "true").lower() in ("true", "1", "yes")


def build_text_provider(
    provider_key: str,
    model: str | None = None,
    *,
    agent: str | None = None,
) -> TextProvider:
    if _use_ai_gateway():
        from contentos_ai_client.providers import GatewayTextProvider

        return GatewayTextProvider(provider_key=provider_key, model=model, agent=agent)

    key = provider_key.lower()
    if key in ("ollama", "qwen", "llama"):
        from contentos_shared.providers.ai.ollama import OllamaTextProvider

        return OllamaTextProvider(model=model)
    if key == "openai":
        from contentos_shared.providers.ai.openai import OpenAITextProvider

        return OpenAITextProvider(model=model)
    raise ValueError(f"Unknown text provider for direct mode: {key}. Enable USE_AI_GATEWAY for cloud providers.")


def build_speech_provider(
    provider_key: str,
    model: str | None = None,
    *,
    agent: str | None = None,
) -> SpeechProvider:
    if _use_ai_gateway():
        from contentos_ai_client.providers import GatewaySpeechProvider

        return GatewaySpeechProvider(provider_key=provider_key, model=model, agent=agent)

    key = provider_key.lower()
    if key == "piper":
        from contentos_shared.providers.speech.piper import PiperSpeechProvider

        return PiperSpeechProvider(voice=model)
    if key == "elevenlabs":
        from contentos_shared.providers.speech.elevenlabs import ElevenLabsSpeechProvider

        return ElevenLabsSpeechProvider(voice_id=model)
    raise ValueError(f"Unknown speech provider: {key}")


def build_subtitle_provider(
    provider_key: str,
    model: str | None = None,
    *,
    agent: str | None = None,
) -> SubtitleProvider:
    if _use_ai_gateway():
        from contentos_ai_client.providers import GatewaySubtitleProvider

        return GatewaySubtitleProvider(provider_key=provider_key, model=model, agent=agent)

    key = provider_key.lower()
    if key in ("local", "whisper"):
        from contentos_shared.providers.subtitle.local_whisper import LocalWhisperProvider

        return LocalWhisperProvider(model=model)
    if key == "openai":
        from contentos_shared.providers.subtitle.openai_whisper import OpenAIWhisperProvider

        return OpenAIWhisperProvider(model=model)
    raise ValueError(f"Unknown subtitle provider: {key}")
