"""Gateway-backed providers implementing shared protocols."""

import os
from typing import Any

from contentos_ai_client.client import AIGatewayClient


def _fallback_enabled() -> bool:
    return os.getenv("AI_GATEWAY_FALLBACK", "true").lower() in ("true", "1", "yes")


def _direct_text(provider_key: str, model: str | None = None):
    """Load V1 direct adapter — never routes through gateway (avoids recursion)."""
    key = provider_key.lower()
    if key in ("ollama", "qwen", "llama"):
        from contentos_shared.providers.ai.ollama import OllamaTextProvider

        return OllamaTextProvider(model=model)
    if key == "openai":
        from contentos_shared.providers.ai.openai import OpenAITextProvider

        return OpenAITextProvider(model=model)
    raise ValueError(f"No direct fallback for text provider: {key}")


def _direct_speech(provider_key: str, model: str | None = None):
    key = provider_key.lower()
    if key == "piper":
        from contentos_shared.providers.speech.piper import PiperSpeechProvider

        return PiperSpeechProvider(voice=model)
    if key == "elevenlabs":
        from contentos_shared.providers.speech.elevenlabs import ElevenLabsSpeechProvider

        return ElevenLabsSpeechProvider(voice_id=model)
    raise ValueError(f"No direct fallback for speech provider: {key}")


def _direct_subtitle(provider_key: str, model: str | None = None):
    key = provider_key.lower()
    if key in ("local", "whisper"):
        from contentos_shared.providers.subtitle.local_whisper import LocalWhisperProvider

        return LocalWhisperProvider(model=model)
    if key == "openai":
        from contentos_shared.providers.subtitle.openai_whisper import OpenAIWhisperProvider

        return OpenAIWhisperProvider(model=model)
    raise ValueError(f"No direct fallback for subtitle provider: {key}")


class GatewayTextProvider:
    """TextProvider that routes through AI Gateway with optional V1 fallback."""

    def __init__(
        self,
        provider_key: str | None = None,
        model: str | None = None,
        agent: str | None = None,
    ) -> None:
        self.provider_key = (provider_key or os.getenv("TEXT_PROVIDER", "ollama")).lower()
        self.model = model or os.getenv("TEXT_MODEL")
        self.agent = agent
        self._client = AIGatewayClient()

    async def chat_json(self, system: str, user: str) -> dict[str, Any]:
        try:
            return await self._client.chat_json(
                provider=self.provider_key,
                system=system,
                user=user,
                model=self.model,
                agent=self.agent,
            )
        except Exception:
            if _fallback_enabled():
                return await _direct_text(self.provider_key, self.model).chat_json(system, user)
            raise


class GatewaySpeechProvider:
    def __init__(
        self,
        provider_key: str | None = None,
        model: str | None = None,
        agent: str | None = None,
    ) -> None:
        self.provider_key = (provider_key or os.getenv("SPEECH_PROVIDER", "piper")).lower()
        self.model = model or os.getenv("SPEECH_MODEL")
        self.agent = agent
        self._client = AIGatewayClient()

    async def text_to_speech(self, text: str) -> bytes:
        try:
            return await self._client.text_to_speech(
                provider=self.provider_key,
                text=text,
                model=self.model,
                agent=self.agent,
            )
        except Exception:
            if _fallback_enabled():
                return await _direct_speech(self.provider_key, self.model).text_to_speech(text)
            raise


class GatewaySubtitleProvider:
    def __init__(
        self,
        provider_key: str | None = None,
        model: str | None = None,
        agent: str | None = None,
    ) -> None:
        self.provider_key = (provider_key or os.getenv("SUBTITLE_PROVIDER", "local")).lower()
        self.model = model or os.getenv("SUBTITLE_MODEL")
        self.agent = agent
        self._client = AIGatewayClient()

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.mp3") -> dict[str, Any]:
        try:
            return await self._client.transcribe(
                provider=self.provider_key,
                audio_bytes=audio_bytes,
                filename=filename,
                model=self.model,
                agent=self.agent,
            )
        except Exception:
            if _fallback_enabled():
                return await _direct_subtitle(self.provider_key, self.model).transcribe(audio_bytes, filename)
            raise


class GatewayImageProvider:
    def __init__(
        self,
        provider_key: str | None = None,
        model: str | None = None,
        agent: str | None = None,
    ) -> None:
        self.provider_key = (provider_key or os.getenv("IMAGE_PROVIDER", "local")).lower()
        self.model = model or os.getenv("IMAGE_MODEL")
        self.agent = agent
        self._client = AIGatewayClient()

    async def generate_image(self, prompt: str, size: str = "1080x1920") -> bytes:
        try:
            return await self._client.generate_image(
                provider=self.provider_key,
                prompt=prompt,
                size=size,
                model=self.model,
                agent=self.agent,
            )
        except Exception:
            if _fallback_enabled():
                from contentos_ai.infrastructure.adapters.image.local import LocalImageAdapter

                return await LocalImageAdapter(model=self.model).generate_image(prompt, size)
            raise


class GatewayVisionProvider:
    def __init__(
        self,
        provider_key: str | None = None,
        model: str | None = None,
        agent: str | None = None,
    ) -> None:
        self.provider_key = (provider_key or os.getenv("VISION_PROVIDER", "ollama")).lower()
        self.model = model or os.getenv("VISION_MODEL") or os.getenv("OLLAMA_VISION_MODEL")
        self.agent = agent
        self._client = AIGatewayClient()

    async def analyze_image(self, image_bytes: bytes, prompt: str) -> dict[str, Any]:
        return await self._client.analyze_image(
            provider=self.provider_key,
            image_bytes=image_bytes,
            prompt=prompt,
            model=self.model,
            agent=self.agent,
        )


class GatewayEmbeddingProvider:
    def __init__(
        self,
        provider_key: str | None = None,
        model: str | None = None,
        agent: str | None = None,
    ) -> None:
        self.provider_key = (provider_key or os.getenv("EMBEDDING_PROVIDER", "ollama")).lower()
        self.model = model or os.getenv("EMBEDDING_MODEL") or os.getenv("OLLAMA_EMBED_MODEL")
        self.agent = agent
        self._client = AIGatewayClient()

    async def embed(self, text: str) -> list[float]:
        return await self._client.embed(
            provider=self.provider_key,
            text=text,
            model=self.model,
            agent=self.agent,
        )
