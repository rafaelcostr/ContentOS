"""Dynamic provider factory for AI Core — delegates to ProviderRegistry."""

from typing import Any

from contentos_ai.application.provider_registry import ProviderRegistry, get_provider_registry


class AIProviderFactory:
    """Resolves provider adapters by key and optional model override."""

    def __init__(self, registry: ProviderRegistry | None = None) -> None:
        self._registry = registry or get_provider_registry()

    def text(self, provider_key: str | None = None, model: str | None = None) -> Any:
        return self._registry.text(provider_key, model)

    def speech(self, provider_key: str | None = None, model: str | None = None) -> Any:
        return self._registry.speech(provider_key, model)

    def subtitle(self, provider_key: str | None = None, model: str | None = None) -> Any:
        return self._registry.subtitle(provider_key, model)

    def image(self, provider_key: str | None = None, model: str | None = None) -> Any:
        return self._registry.image(provider_key, model)

    def vision(self, provider_key: str | None = None, model: str | None = None) -> Any:
        return self._registry.vision(provider_key, model)

    def embedding(self, provider_key: str | None = None, model: str | None = None) -> Any:
        return self._registry.embedding(provider_key, model)


_factory: AIProviderFactory | None = None


def get_ai_factory() -> AIProviderFactory:
    global _factory
    if _factory is None:
        _factory = AIProviderFactory()
    return _factory
