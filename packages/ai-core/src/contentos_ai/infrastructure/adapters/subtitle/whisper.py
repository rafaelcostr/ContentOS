import os
from typing import Any

import httpx


class WhisperSubtitleAdapter:
    name = "whisper"

    def __init__(self, model: str | None = None) -> None:
        self.base_url = os.getenv("WHISPER_URL", "http://whisper:8080").rstrip("/")
        self.model = model or os.getenv("WHISPER_MODEL", "large-v3")

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.mp3") -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=600.0) as client:
            response = await client.post(
                f"{self.base_url}/transcribe",
                files={"file": (filename, audio_bytes, "audio/mpeg")},
                data={"model": self.model},
            )
            response.raise_for_status()
            return response.json()
