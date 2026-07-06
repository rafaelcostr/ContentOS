import os

import httpx


class PiperSpeechProvider:
    """Piper local TTS — default for zero-cost production.

    Expects a Piper HTTP server (Phase 2 docker service) or falls back to
    the configured PIPER_URL endpoint.
    """

    def __init__(self, voice: str | None = None) -> None:
        self.base_url = os.getenv("PIPER_URL", "http://piper:5000").rstrip("/")
        self.voice = voice or os.getenv("PIPER_VOICE", "pt_BR-faber-medium")

    async def text_to_speech(self, text: str) -> bytes:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/tts",
                json={"text": text, "voice": self.voice},
            )
            response.raise_for_status()
            return response.content
