import os

import httpx


class ElevenLabsSpeechAdapter:
    name = "elevenlabs"

    def __init__(self, model: str | None = None) -> None:
        self.api_key = os.getenv("ELEVENLABS_API_KEY", "")
        self.voice_id = model or os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
        self.base_url = "https://api.elevenlabs.io/v1"

    async def text_to_speech(self, text: str) -> bytes:
        if not self.api_key:
            raise ValueError("elevenlabs: set ELEVENLABS_API_KEY to enable this provider")
        url = f"{self.base_url}/text-to-speech/{self.voice_id}"
        headers = {"xi-api-key": self.api_key, "Content-Type": "application/json"}
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.content
