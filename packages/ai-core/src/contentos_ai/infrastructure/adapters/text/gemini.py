import json
import os
from typing import Any

import httpx


class GeminiTextAdapter:
    name = "gemini"

    def __init__(self, model: str | None = None) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    async def chat_json(self, system: str, user: str) -> dict[str, Any]:
        if not self.api_key:
            raise ValueError("gemini: set GEMINI_API_KEY to enable this provider")
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            f"?key={self.api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": f"{system}\n\n{user}\n\nRespond ONLY with valid JSON."}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
