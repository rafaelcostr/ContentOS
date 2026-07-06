"""HTTP client for AI Gateway — used by agents via ProviderFactory."""

import os
from typing import Any

import httpx


class AIGatewayClient:
    def __init__(self, base_url: str | None = None, timeout: float = 300.0) -> None:
        self.base_url = (base_url or os.getenv("AI_GATEWAY_URL", "http://ai-gateway:8020")).rstrip("/")
        self.timeout = timeout

    async def health(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()

    async def chat_json(
        self,
        *,
        provider: str,
        system: str,
        user: str,
        model: str | None = None,
        agent: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"provider": provider, "system": system, "user": user}
        if model:
            payload["model"] = model
        if agent:
            payload["agent"] = agent
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/v1/text/chat-json", json=payload)
            response.raise_for_status()
            return response.json()

    async def text_to_speech(
        self,
        *,
        provider: str,
        text: str,
        model: str | None = None,
        voice: str | None = None,
        agent: str | None = None,
    ) -> bytes:
        payload: dict[str, Any] = {"provider": provider, "text": text}
        if model:
            payload["model"] = model
        if voice:
            payload["voice"] = voice
        if agent:
            payload["agent"] = agent
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/v1/speech/tts", json=payload)
            response.raise_for_status()
            return response.content

    async def transcribe(
        self,
        *,
        provider: str,
        audio_bytes: bytes,
        filename: str = "audio.mp3",
        model: str | None = None,
        agent: str | None = None,
    ) -> dict[str, Any]:
        data: dict[str, str] = {"provider": provider}
        if model:
            data["model"] = model
        if agent:
            data["agent"] = agent
        async with httpx.AsyncClient(timeout=600.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/subtitle/transcribe",
                files={"file": (filename, audio_bytes, "audio/mpeg")},
                data=data,
            )
            response.raise_for_status()
            return response.json()

    async def generate_image(
        self,
        *,
        provider: str,
        prompt: str,
        size: str = "1080x1920",
        model: str | None = None,
        agent: str | None = None,
    ) -> bytes:
        payload: dict[str, Any] = {"provider": provider, "prompt": prompt, "size": size}
        if model:
            payload["model"] = model
        if agent:
            payload["agent"] = agent
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/v1/image/generate", json=payload)
            response.raise_for_status()
            return response.content

    async def analyze_image(
        self,
        *,
        provider: str,
        image_bytes: bytes,
        prompt: str,
        filename: str = "image.jpg",
        model: str | None = None,
        agent: str | None = None,
    ) -> dict[str, Any]:
        data: dict[str, str] = {"provider": provider, "prompt": prompt}
        if model:
            data["model"] = model
        if agent:
            data["agent"] = agent
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/v1/vision/analyze",
                files={"file": (filename, image_bytes, "image/jpeg")},
                data=data,
            )
            response.raise_for_status()
            return response.json()

    async def embed(
        self,
        *,
        provider: str,
        text: str,
        model: str | None = None,
        agent: str | None = None,
    ) -> list[float]:
        payload: dict[str, Any] = {"provider": provider, "text": text}
        if model:
            payload["model"] = model
        if agent:
            payload["agent"] = agent
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{self.base_url}/v1/embeddings", json=payload)
            response.raise_for_status()
            return response.json()["embedding"]

    async def list_providers(self) -> dict[str, list[str]]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}/v1/providers")
            response.raise_for_status()
            return response.json()
