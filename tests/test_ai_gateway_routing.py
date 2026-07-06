"""Phase 9 — ProviderRegistry + Model Manager routing."""

from contentos_ai import ProviderRegistry, RoutingService, get_provider_registry
from contentos_ai.infrastructure.adapters.text.ollama import OllamaTextAdapter


def test_provider_registry_lists_providers():
    registry = get_provider_registry()
    providers = registry.list_providers()
    assert "ollama" in providers["text"]
    assert "piper" in providers["speech"]
    assert "local" in providers["subtitle"]


def test_provider_registry_creates_text_adapter():
    registry = ProviderRegistry()
    adapter = registry.text("ollama", model="qwen2.5:7b")
    assert isinstance(adapter, OllamaTextAdapter)


def test_routing_without_agent_uses_request():
    routing = RoutingService()
    route = routing.resolve(provider_type="text", provider="openai", model="gpt-4o")
    assert route.provider == "openai"
    assert route.model == "gpt-4o"
    assert route.source == "request"


def test_routing_with_agent_defaults():
    routing = RoutingService()
    route = routing.resolve(provider_type="text", provider="ollama", agent="script")
    assert route.provider == "ollama"
    assert route.agent == "script"
    assert route.source in ("model-manager", "agent-default")


def test_routing_voice_agent():
    routing = RoutingService()
    route = routing.resolve(provider_type="speech", provider="piper", agent="voice")
    assert route.provider == "piper"
    assert route.agent == "voice"


def test_ai_service_resolve_route():
    from contentos_ai import AIService

    service = AIService()
    route = service.resolve_route(provider_type="text", agent="research", provider="ollama")
    assert route["provider"] == "ollama"
    assert route["agent"] == "research"
    assert route["source"] in ("model-manager", "agent-default")


def test_gateway_provider_passes_agent(monkeypatch):
    from contentos_ai_client.providers import GatewayTextProvider

    captured: dict = {}

    class FakeClient:
        async def chat_json(self, **kwargs):
            captured.update(kwargs)
            return {"ok": True}

    provider = GatewayTextProvider(provider_key="ollama", model="qwen2.5:7b", agent="script")
    provider._client = FakeClient()

    import asyncio

    result = asyncio.run(provider.chat_json("sys", "user"))
    assert result["ok"] is True
    assert captured["agent"] == "script"
    assert captured["provider"] == "ollama"


def test_gateway_fallback_uses_direct_not_gateway(monkeypatch):
    """Fallback must not recurse into GatewayTextProvider."""
    from contentos_ai_client import providers as gw

    monkeypatch.setenv("AI_GATEWAY_FALLBACK", "true")
    monkeypatch.setenv("USE_AI_GATEWAY", "true")

    class BoomClient:
        async def chat_json(self, **kwargs):
            raise RuntimeError("gateway down")

    called = {"direct": False}

    class Direct:
        async def chat_json(self, system, user):
            called["direct"] = True
            return {"fallback": True}

    monkeypatch.setattr(gw, "_direct_text", lambda key, model=None: Direct())

    provider = gw.GatewayTextProvider(provider_key="ollama", agent="research")
    provider._client = BoomClient()

    import asyncio

    result = asyncio.run(provider.chat_json("s", "u"))
    assert result["fallback"] is True
    assert called["direct"] is True


def test_default_use_ai_gateway_is_true(monkeypatch):
    monkeypatch.delenv("USE_AI_GATEWAY", raising=False)
    from contentos_ai_client.providers import GatewayTextProvider
    from contentos_shared.providers.factory import ProviderFactory, get_provider_factory

    get_provider_factory.cache_clear()
    factory = ProviderFactory(text_provider="ollama")
    assert factory.status()["mode"] == "ai-gateway"
    assert isinstance(factory.text(), GatewayTextProvider)
