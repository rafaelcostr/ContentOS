"""Unified ProviderRegistry — single source of truth for AI adapters."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from contentos_ai.domain.registry import (
    EMBEDDING_REGISTRY,
    IMAGE_REGISTRY,
    SPEECH_REGISTRY,
    SUBTITLE_REGISTRY,
    TEXT_REGISTRY,
    VISION_REGISTRY,
)


class ProviderRegistry:
    """Registry + factory for all AI provider types."""

    def __init__(
        self,
        text: dict[str, str] | None = None,
        speech: dict[str, str] | None = None,
        subtitle: dict[str, str] | None = None,
        image: dict[str, str] | None = None,
        vision: dict[str, str] | None = None,
        embedding: dict[str, str] | None = None,
    ) -> None:
        self._text = dict(text or TEXT_REGISTRY)
        self._speech = dict(speech or SPEECH_REGISTRY)
        self._subtitle = dict(subtitle or SUBTITLE_REGISTRY)
        self._image = dict(image or IMAGE_REGISTRY)
        self._vision = dict(vision or VISION_REGISTRY)
        self._embedding = dict(embedding or EMBEDDING_REGISTRY)

    def list_providers(self) -> dict[str, list[str]]:
        return {
            "text": sorted(self._text.keys()),
            "speech": sorted(self._speech.keys()),
            "subtitle": sorted(self._subtitle.keys()),
            "image": sorted(self._image.keys()),
            "vision": sorted(self._vision.keys()),
            "embedding": sorted(self._embedding.keys()),
        }

    def has(self, provider_type: str, key: str) -> bool:
        return key.lower() in self._registry_for(provider_type)

    def register(self, provider_type: str, key: str, class_path: str) -> None:
        self._registry_for(provider_type)[key.lower()] = class_path

    def create(self, provider_type: str, key: str, model: str | None = None) -> Any:
        registry = self._registry_for(provider_type)
        path = registry.get(key.lower())
        if not path:
            raise ValueError(f"Unknown {provider_type} provider: {key}. Available: {list(registry)}")
        cls = self._load_class(path)
        return cls(model=model)

    def text(self, key: str | None = None, model: str | None = None) -> Any:
        return self.create("text", key or "ollama", model)

    def speech(self, key: str | None = None, model: str | None = None) -> Any:
        return self.create("speech", key or "piper", model)

    def subtitle(self, key: str | None = None, model: str | None = None) -> Any:
        return self.create("subtitle", key or "local", model)

    def image(self, key: str | None = None, model: str | None = None) -> Any:
        return self.create("image", key or "local", model)

    def vision(self, key: str | None = None, model: str | None = None) -> Any:
        return self.create("vision", key or "ollama", model)

    def embedding(self, key: str | None = None, model: str | None = None) -> Any:
        return self.create("embedding", key or "ollama", model)

    def _registry_for(self, provider_type: str) -> dict[str, str]:
        mapping = {
            "text": self._text,
            "speech": self._speech,
            "subtitle": self._subtitle,
            "image": self._image,
            "vision": self._vision,
            "embedding": self._embedding,
        }
        if provider_type not in mapping:
            raise ValueError(f"Unknown provider type: {provider_type}")
        return mapping[provider_type]

    @staticmethod
    def _load_class(path: str) -> type:
        module_path, class_name = path.rsplit(".", 1)
        module = import_module(module_path)
        return getattr(module, class_name)


_registry: ProviderRegistry | None = None


def get_provider_registry() -> ProviderRegistry:
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
    return _registry
