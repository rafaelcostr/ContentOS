import json
import os
from typing import Any

import httpx


class _AnthropicCompatibleAdapter:
    """Shared HTTP adapter for Anthropic-style message APIs."""

    name: str = "base"
    api_key_env: str = ""
    base_url: str = ""
    default_model: str = ""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.getenv(f"{self.name.upper()}_MODEL", self.default_model)
        self.api_key = os.getenv(self.api_key_env, "")

    async def chat_json(self, system: str, user: str) -> dict[str, Any]:
        if not self.api_key:
            raise ValueError(f"{self.name}: set {self.api_key_env} to enable this provider")
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "system": system + "\nRespond ONLY with valid JSON.",
            "messages": [{"role": "user", "content": user}],
        }
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(f"{self.base_url}/v1/messages", json=payload, headers=headers)
            response.raise_for_status()
            text = response.json()["content"][0]["text"]
            return json.loads(text)


class ClaudeTextAdapter(_AnthropicCompatibleAdapter):
    name = "claude"
    api_key_env = "ANTHROPIC_API_KEY"
    base_url = "https://api.anthropic.com"
    default_model = "claude-3-5-sonnet-20241022"
