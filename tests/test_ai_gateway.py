"""Tests for AI Core, AI Gateway, and gateway-backed providers."""

import pytest
from contentos_ai import AIService, get_ai_factory
from contentos_ai.infrastructure.adapters.text.ollama import OllamaTextAdapter
from contentos_ai_client.providers import GatewayTextProvider
from contentos_shared.providers.factory import ProviderFactory
from fastapi.testclient import TestClient


def test_ai_factory_text_ollama():
    factory = get_ai_factory()
    provider = factory.text("ollama")
    assert isinstance(provider, OllamaTextAdapter)
    assert provider.name == "ollama"


def test_ai_service_list_providers():
    service = AIService()
    providers = service.list_providers()
    assert "ollama" in providers["text"]
    assert "piper" in providers["speech"]
    assert "local" in providers["subtitle"]
    assert "local" in providers["image"]
    assert "ollama" in providers["vision"]
    assert "ollama" in providers["embedding"]


def test_ai_gateway_health():
    from contentos_ai_gateway.main import app

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ai_gateway_list_providers():
    from contentos_ai_gateway.main import app

    client = TestClient(app)
    response = client.get("/v1/providers")
    assert response.status_code == 200
    body = response.json()
    assert "ollama" in body["text"]


def test_ai_gateway_chat_json(monkeypatch):
    from contentos_ai_gateway.deps import ai_service
    from contentos_ai_gateway.main import app

    async def mock_chat_json(**kwargs):
        return {"title": "Test", "hook": "Hello", "agent": kwargs.get("agent")}

    monkeypatch.setattr(ai_service, "chat_json", mock_chat_json)
    client = TestClient(app)
    response = client.post(
        "/v1/text/chat-json",
        json={
            "provider": "ollama",
            "system": "You are helpful",
            "user": "Say hi",
            "agent": "script",
        },
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Test"
    assert response.json()["agent"] == "script"


def test_ai_gateway_resolve_route():
    from contentos_ai_gateway.main import app

    client = TestClient(app)
    response = client.get("/v1/providers/resolve", params={"agent": "voice", "provider_type": "speech"})
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "piper"
    assert body["agent"] == "voice"


def test_provider_factory_gateway_mode(monkeypatch):
    monkeypatch.setenv("USE_AI_GATEWAY", "true")
    from contentos_shared.providers.factory import get_provider_factory

    get_provider_factory.cache_clear()
    factory = ProviderFactory(text_provider="ollama")
    provider = factory.text()
    assert isinstance(provider, GatewayTextProvider)
    status = factory.status()
    assert status["mode"] == "ai-gateway"


def test_provider_factory_direct_mode(monkeypatch):
    monkeypatch.setenv("USE_AI_GATEWAY", "false")
    from contentos_shared.providers.factory import get_provider_factory

    get_provider_factory.cache_clear()
    factory = ProviderFactory(text_provider="ollama")
    provider = factory.text()
    assert isinstance(provider, OllamaTextAdapter) is False
    from contentos_shared.providers.ai.ollama import OllamaTextProvider

    assert isinstance(provider, OllamaTextProvider)
    assert factory.status()["mode"] == "direct"
