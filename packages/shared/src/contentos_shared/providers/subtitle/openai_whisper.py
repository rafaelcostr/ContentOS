import json
import os
import tempfile
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI


class OpenAIWhisperProvider:
    """OpenAI Whisper API — swap via SUBTITLE_PROVIDER=openai."""

    def __init__(self, model: str | None = None) -> None:
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        self.model = model or os.getenv("OPENAI_WHISPER_MODEL", "whisper-1")

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.mp3") -> dict[str, Any]:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            with open(tmp_path, "rb") as f:
                response = await self.client.audio.transcriptions.create(
                    model=self.model,
                    file=f,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                )
            if hasattr(response, "model_dump"):
                return response.model_dump()
            return json.loads(response) if isinstance(response, str) else dict(response)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
