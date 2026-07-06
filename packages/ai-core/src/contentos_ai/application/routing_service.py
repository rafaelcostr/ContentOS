"""Per-agent model routing via Model Manager (with env defaults fallback)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderRoute:
    provider: str
    model: str | None
    agent: str | None = None
    source: str = "request"


_DEFAULTS: dict[str, dict[str, str]] = {
    "research": {"type": "text", "provider": "ollama"},
    "hook": {"type": "text", "provider": "ollama"},
    "script": {"type": "text", "provider": "ollama"},
    "script_review": {"type": "text", "provider": "ollama"},
    "emotion": {"type": "text", "provider": "ollama"},
    "video_review": {"type": "text", "provider": "ollama"},
    "storyboard": {"type": "text", "provider": "ollama"},
    "scene": {"type": "text", "provider": "ollama"},
    "publisher": {"type": "text", "provider": "ollama"},
    "analytics": {"type": "text", "provider": "ollama"},
    "thumbnail": {"type": "image", "provider": "local"},
    "clip_research": {"type": "text", "provider": "ollama"},
    "voice": {"type": "speech", "provider": "piper"},
    "subtitle": {"type": "subtitle", "provider": "local"},
}


class RoutingService:
    """Resolve provider/model for an agent. Model Manager wins when available."""

    def resolve(
        self,
        *,
        provider_type: str,
        provider: str | None = None,
        model: str | None = None,
        agent: str | None = None,
    ) -> ProviderRoute:
        if not agent:
            return ProviderRoute(
                provider=(provider or self._default_provider(provider_type)).lower(),
                model=model,
                source="request",
            )

        routed = self._from_model_manager(agent, provider_type)
        if routed:
            return routed

        defaults = _DEFAULTS.get(agent)
        if defaults and defaults["type"] == provider_type:
            return ProviderRoute(
                provider=(provider or defaults["provider"]).lower(),
                model=model,
                agent=agent,
                source="agent-default",
            )

        return ProviderRoute(
            provider=(provider or self._default_provider(provider_type)).lower(),
            model=model,
            agent=agent,
            source="request",
        )

    def _from_model_manager(self, agent: str, provider_type: str) -> ProviderRoute | None:
        try:
            from contentos_models import get_model_manager

            cfg = get_model_manager().get_config(agent)
        except Exception:
            return None
        if cfg.provider_type != provider_type:
            return None
        return ProviderRoute(
            provider=cfg.provider.lower(),
            model=cfg.model or None,
            agent=agent,
            source="model-manager",
        )

    @staticmethod
    def _default_provider(provider_type: str) -> str:
        return {
            "text": "ollama",
            "speech": "piper",
            "subtitle": "local",
            "image": "local",
            "vision": "ollama",
            "embedding": "ollama",
        }.get(provider_type, "ollama")


_routing: RoutingService | None = None


def get_routing_service() -> RoutingService:
    global _routing
    if _routing is None:
        _routing = RoutingService()
    return _routing
