import json
import os
from typing import Any

from openai import AsyncOpenAI


class OpenAITextAdapter:
    name = "openai"

    def __init__(self, model: str | None = None) -> None:
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o")

    async def chat_json(self, system: str, user: str) -> dict[str, Any]:
        response = await self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return json.loads(response.choices[0].message.content or "{}")
