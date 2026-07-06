import json
import os
from typing import Any

import httpx


class MistralTextAdapter:
    name = "mistral"

    def __init__(self, model: str | None = None) -> None:
        self.api_key = os.getenv("MISTRAL_API_KEY", "")
        self.model = model or os.getenv("MISTRAL_MODEL", "mistral-small-latest")

    async def chat_json(self, system: str, user: str) -> dict[str, Any]:
        if not self.api_key:
            raise ValueError("mistral: set MISTRAL_API_KEY to enable this provider")
        payload = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post("https://api.mistral.ai/v1/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return json.loads(content)
