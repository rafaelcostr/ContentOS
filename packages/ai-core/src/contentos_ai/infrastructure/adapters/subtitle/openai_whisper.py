import os
from typing import Any

from openai import AsyncOpenAI


class OpenAIWhisperAdapter:
    name = "openai_whisper"

    def __init__(self, model: str | None = None) -> None:
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        self.model = model or os.getenv("OPENAI_WHISPER_MODEL", "whisper-1")

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.mp3") -> dict[str, Any]:
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("openai whisper: set OPENAI_API_KEY to enable this provider")
        import io

        buffer = io.BytesIO(audio_bytes)
        buffer.name = filename
        result = await self.client.audio.transcriptions.create(model=self.model, file=buffer)
        return {"text": result.text, "segments": []}
