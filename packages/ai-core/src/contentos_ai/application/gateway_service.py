"""Central AI service — single entry point for all AI operations."""

from typing import Any

from contentos_ai.application.provider_registry import ProviderRegistry, get_provider_registry
from contentos_ai.application.routing_service import RoutingService, get_routing_service
from contentos_ai.infrastructure.factory import AIProviderFactory, get_ai_factory


class AIService:
    """Application service used by the AI Gateway."""

    def __init__(
        self,
        factory: AIProviderFactory | None = None,
        registry: ProviderRegistry | None = None,
        routing: RoutingService | None = None,
    ) -> None:
        self._factory = factory or get_ai_factory()
        self._registry = registry or get_provider_registry()
        self._routing = routing or get_routing_service()

    async def chat_json(
        self,
        *,
        provider: str,
        system: str,
        user: str,
        model: str | None = None,
        agent: str | None = None,
    ) -> dict[str, Any]:
        route = self._routing.resolve(
            provider_type="text",
            provider=provider,
            model=model,
            agent=agent,
        )
        text_provider = self._registry.text(route.provider, route.model)
        return await text_provider.chat_json(system, user)

    async def text_to_speech(
        self,
        *,
        provider: str,
        text: str,
        model: str | None = None,
        voice: str | None = None,
        agent: str | None = None,
    ) -> bytes:
        route = self._routing.resolve(
            provider_type="speech",
            provider=provider,
            model=model,
            agent=agent,
        )
        speech_provider = self._registry.speech(route.provider, route.model)
        if voice and hasattr(speech_provider, "voice"):
            speech_provider.voice = voice
        return await speech_provider.text_to_speech(text)

    async def transcribe(
        self,
        *,
        provider: str,
        audio_bytes: bytes,
        filename: str = "audio.mp3",
        model: str | None = None,
        agent: str | None = None,
    ) -> dict[str, Any]:
        route = self._routing.resolve(
            provider_type="subtitle",
            provider=provider,
            model=model,
            agent=agent,
        )
        subtitle_provider = self._registry.subtitle(route.provider, route.model)
        return await subtitle_provider.transcribe(audio_bytes, filename)

    async def generate_image(
        self,
        *,
        provider: str,
        prompt: str,
        size: str = "1080x1920",
        model: str | None = None,
        agent: str | None = None,
    ) -> bytes:
        route = self._routing.resolve(
            provider_type="image",
            provider=provider,
            model=model,
            agent=agent,
        )
        image_provider = self._registry.image(route.provider, route.model)
        return await image_provider.generate_image(prompt, size)

    async def analyze_image(
        self,
        *,
        provider: str,
        image_bytes: bytes,
        prompt: str,
        model: str | None = None,
        agent: str | None = None,
    ) -> dict[str, Any]:
        route = self._routing.resolve(
            provider_type="vision",
            provider=provider,
            model=model,
            agent=agent,
        )
        vision_provider = self._registry.vision(route.provider, route.model)
        return await vision_provider.analyze_image(image_bytes, prompt)

    async def embed(
        self,
        *,
        provider: str,
        text: str,
        model: str | None = None,
        agent: str | None = None,
    ) -> list[float]:
        route = self._routing.resolve(
            provider_type="embedding",
            provider=provider,
            model=model,
            agent=agent,
        )
        embedding_provider = self._registry.embedding(route.provider, route.model)
        return await embedding_provider.embed(text)

    def list_providers(self) -> dict[str, list[str]]:
        return self._registry.list_providers()

    def resolve_route(
        self,
        *,
        provider_type: str,
        provider: str | None = None,
        model: str | None = None,
        agent: str | None = None,
    ) -> dict[str, Any]:
        route = self._routing.resolve(
            provider_type=provider_type,
            provider=provider,
            model=model,
            agent=agent,
        )
        return {
            "provider": route.provider,
            "model": route.model,
            "agent": route.agent,
            "source": route.source,
        }
