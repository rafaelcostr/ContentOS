"""Embedding client via AI Gateway."""

from __future__ import annotations

import os

import httpx

from contentos_intelligence.application.noop import NoOpEmbeddingClient


class GatewayEmbeddingClient:
    """IEmbeddingClient — routes embed requests through AI Gateway."""

    def __init__(
        self,
        base_url: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.base_url = (base_url or os.getenv("AI_GATEWAY_URL", "http://ai-gateway:8020")).rstrip("/")
        self.provider = provider or os.getenv("KNOWLEDGE_EMBED_PROVIDER", "ollama")
        self.model = model or os.getenv("KNOWLEDGE_EMBED_MODEL")
        self.timeout = timeout

    async def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for text in texts:
                stripped = (text or "").strip()
                if not stripped:
                    vectors.append([])
                    continue
                payload: dict = {"provider": self.provider, "text": stripped, "agent": "knowledge"}
                if self.model:
                    payload["model"] = self.model
                try:
                    response = await client.post(f"{self.base_url}/v1/embeddings", json=payload)
                    response.raise_for_status()
                    vectors.append(list(response.json().get("embedding") or []))
                except Exception:
                    vectors.append([])
        return vectors


_default_client: GatewayEmbeddingClient | NoOpEmbeddingClient | None = None


def get_gateway_embedding_client():
    global _default_client
    if _default_client is None:
        if os.getenv("KNOWLEDGE_EMBED_DISABLED", "").lower() in ("1", "true", "yes"):
            _default_client = NoOpEmbeddingClient()
        else:
            _default_client = GatewayEmbeddingClient()
    return _default_client


def reset_embedding_client() -> None:
    global _default_client
    _default_client = None
