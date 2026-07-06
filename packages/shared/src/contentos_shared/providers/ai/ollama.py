import json
import os
from typing import Any

import httpx


class OllamaTextProvider:
    """Ollama local LLM adapter — default for zero-cost production."""

    def __init__(self, model: str | None = None) -> None:
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434").rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

    async def chat_json(self, system: str, user: str) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            content = response.json()["message"]["content"]
        return json.loads(content)
