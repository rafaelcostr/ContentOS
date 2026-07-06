"""Whisper STT HTTP service — faster-whisper large-v3 for ContentOS."""

import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, UploadFile
from faster_whisper import WhisperModel

app = FastAPI(title="ContentOS Whisper", version="1.0.0")

MODEL_NAME = os.getenv("WHISPER_MODEL", "large-v3")
DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

_model: WhisperModel | None = None


@app.on_event("startup")
def load_model() -> None:
    global _model
    _model = WhisperModel(MODEL_NAME, device=DEVICE, compute_type=COMPUTE_TYPE)


@app.get("/health")
async def health():
    return {
        "status": "ok" if _model is not None else "loading",
        "service": "whisper",
        "model": MODEL_NAME,
        "device": DEVICE,
        "loaded": _model is not None,
    }


@app.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    model: str = Form(default=""),
) -> dict[str, Any]:
    if _model is None:
        return {"error": "Model not loaded", "segments": []}

    suffix = Path(file.filename or "audio.mp3").suffix or ".mp3"
    audio_bytes = await file.read()

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        segments_iter, info = _model.transcribe(tmp_path, beam_size=5, language="pt")
        segments = [
            {"start": seg.start, "end": seg.end, "text": seg.text.strip()}
            for seg in segments_iter
        ]
        full_text = " ".join(s["text"] for s in segments)
        return {
            "text": full_text,
            "language": info.language,
            "duration": info.duration,
            "segments": segments,
        }
    finally:
        Path(tmp_path).unlink(missing_ok=True)
