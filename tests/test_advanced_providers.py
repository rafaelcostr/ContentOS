"""Phase 10 — Image, Vision, Embedding providers."""

import asyncio

import pytest
from contentos_ai import AIService, ProviderRegistry, get_provider_registry
from contentos_ai.infrastructure.adapters.embedding.ollama import OllamaEmbeddingAdapter
from contentos_ai.infrastructure.adapters.image.local import LocalImageAdapter
from contentos_ai.infrastructure.adapters.vision.ollama import OllamaVisionAdapter


def test_registry_lists_advanced_providers():
    providers = get_provider_registry().list_providers()
    assert "local" in providers["image"]
    assert "ollama" in providers["vision"]
    assert "ollama" in providers["embedding"]


def test_local_image_adapter_generates_jpeg():
    adapter = LocalImageAdapter()
    image = asyncio.run(adapter.generate_image("GTA 6 | cinematic", size="1080x1920"))
    assert image[:2] == b"\xff\xd8"  # JPEG magic
    assert len(image) > 1000


def test_ai_service_generate_image():
    service = AIService()
    image = asyncio.run(
        service.generate_image(provider="local", prompt="Viral hook", size="540x960", agent="thumbnail")
    )
    assert image[:2] == b"\xff\xd8"


def test_ai_service_resolve_image_route():
    service = AIService()
    route = service.resolve_route(provider_type="image", agent="thumbnail")
    assert route["provider"] == "local"
    assert route["agent"] == "thumbnail"


def test_gateway_image_route(monkeypatch):
    from contentos_ai_gateway.deps import ai_service
    from contentos_ai_gateway.main import app
    from fastapi.testclient import TestClient

    async def mock_generate(**kwargs):
        return b"\xff\xd8\xff\xe0fakejpeg"

    monkeypatch.setattr(ai_service, "generate_image", mock_generate)
    client = TestClient(app)
    response = client.post(
        "/v1/image/generate",
        json={"provider": "local", "prompt": "Test", "agent": "thumbnail"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content.startswith(b"\xff\xd8")


def test_gateway_list_includes_advanced():
    from contentos_ai_gateway.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.get("/v1/providers")
    assert response.status_code == 200
    body = response.json()
    assert "local" in body["image"]
    assert "ollama" in body["vision"]
    assert "ollama" in body["embedding"]


def test_gateway_embedding_route(monkeypatch):
    from contentos_ai_gateway.deps import ai_service
    from contentos_ai_gateway.main import app
    from fastapi.testclient import TestClient

    async def mock_embed(**kwargs):
        return [0.1, 0.2, 0.3]

    monkeypatch.setattr(ai_service, "embed", mock_embed)
    client = TestClient(app)
    response = client.post("/v1/embeddings", json={"provider": "ollama", "text": "hello"})
    assert response.status_code == 200
    assert response.json()["dimensions"] == 3


def test_gateway_vision_route(monkeypatch):
    from contentos_ai_gateway.deps import ai_service
    from contentos_ai_gateway.main import app
    from fastapi.testclient import TestClient

    async def mock_analyze(**kwargs):
        return {"description": "a car", "provider": "ollama"}

    monkeypatch.setattr(ai_service, "analyze_image", mock_analyze)
    client = TestClient(app)
    response = client.post(
        "/v1/vision/analyze",
        files={"file": ("frame.jpg", b"fakeimage", "image/jpeg")},
        data={"prompt": "Describe", "provider": "ollama"},
    )
    assert response.status_code == 200
    assert response.json()["description"] == "a car"


def test_gateway_image_provider_passes_agent():
    from contentos_ai_client.providers import GatewayImageProvider

    captured: dict = {}

    class FakeClient:
        async def generate_image(self, **kwargs):
            captured.update(kwargs)
            return b"\xff\xd8img"

    provider = GatewayImageProvider(provider_key="local", agent="thumbnail")
    provider._client = FakeClient()
    result = asyncio.run(provider.generate_image("Title", "1080x1920"))
    assert result.startswith(b"\xff\xd8")
    assert captured["agent"] == "thumbnail"


def test_registry_creates_adapters():
    registry = ProviderRegistry()
    assert isinstance(registry.image("local"), LocalImageAdapter)
    assert isinstance(registry.vision("ollama"), OllamaVisionAdapter)
    assert isinstance(registry.embedding("ollama"), OllamaEmbeddingAdapter)
