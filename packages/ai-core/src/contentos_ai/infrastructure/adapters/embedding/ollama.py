"""Ollama embedding adapter."""

from __future__ import annotations

import os

import httpx


class OllamaEmbeddingAdapter:
    name = "ollama"

    def __init__(self, model: str | None = None) -> None:
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434").rstrip("/")
        self.model = model or os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

    async def embed(self, text: str) -> list[float]:
        payload = {"model": self.model, "prompt": text}
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{self.base_url}/api/embeddings", json=payload)
            response.raise_for_status()
            data = response.json()
            embedding = data.get("embedding")
            if not isinstance(embedding, list):
                raise ValueError("Ollama embeddings response missing 'embedding' list")
            return [float(x) for x in embedding]
