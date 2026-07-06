import os

import httpx


class PiperSpeechAdapter:
    name = "piper"

    def __init__(self, model: str | None = None) -> None:
        self.base_url = os.getenv("PIPER_URL", "http://piper:5000").rstrip("/")
        self.voice = model or os.getenv("PIPER_VOICE", "pt_BR-faber-medium")

    async def text_to_speech(self, text: str) -> bytes:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/synthesize",
                json={"text": text, "voice": self.voice},
            )
            response.raise_for_status()
            return response.content
