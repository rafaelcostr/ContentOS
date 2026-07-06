"""Ollama vision adapter — analyze images with multimodal models (llava, etc.)."""

from __future__ import annotations

import base64
import json
import os
from typing import Any

import httpx


class OllamaVisionAdapter:
    name = "ollama"

    def __init__(self, model: str | None = None) -> None:
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434").rstrip("/")
        self.model = model or os.getenv("OLLAMA_VISION_MODEL", "llava")

    async def analyze_image(self, image_bytes: bytes, prompt: str) -> dict[str, Any]:
        encoded = base64.b64encode(image_bytes).decode("ascii")
        system = (
            "You analyze images for short-form video production. "
            "Respond ONLY with valid JSON."
        )
        user = prompt or "Describe this image and suggest a short-form thumbnail caption."
        payload = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": user,
                    "images": [encoded],
                },
            ],
        }
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            content = response.json()["message"]["content"]
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                data = {"description": content}
            if not isinstance(data, dict):
                data = {"result": data}
            data.setdefault("model", self.model)
            data.setdefault("provider", self.name)
            return data
