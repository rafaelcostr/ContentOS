"""Piper TTS HTTP service — local speech synthesis for ContentOS."""

import os
import subprocess
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

app = FastAPI(title="ContentOS Piper TTS", version="1.0.0")

PIPER_BIN = os.getenv("PIPER_BIN", "/usr/local/bin/piper")
MODEL_DIR = Path(os.getenv("PIPER_MODEL_DIR", "/models"))
DEFAULT_VOICE = os.getenv("PIPER_VOICE", "pt_BR-faber-medium")


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    voice: str | None = None


def _model_paths(voice: str) -> tuple[Path, Path]:
    onnx = MODEL_DIR / f"{voice}.onnx"
    config = MODEL_DIR / f"{voice}.onnx.json"
    if not onnx.exists() or not config.exists():
        raise HTTPException(status_code=404, detail=f"Voice model not found: {voice}")
    return onnx, config


def _synthesize_mp3(text: str, voice: str) -> bytes:
    onnx, _ = _model_paths(voice)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        wav_path = tmp_path / "out.wav"
        mp3_path = tmp_path / "out.mp3"

        result = subprocess.run(
            [PIPER_BIN, "--model", str(onnx), "--output_file", str(wav_path)],
            input=text.encode("utf-8"),
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Piper failed: {result.stderr.decode(errors='replace')}",
            )

        ffmpeg = subprocess.run(
            ["ffmpeg", "-y", "-i", str(wav_path), "-codec:a", "libmp3lame", "-q:a", "4", str(mp3_path)],
            capture_output=True,
            check=False,
        )
        if ffmpeg.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"FFmpeg conversion failed: {ffmpeg.stderr.decode(errors='replace')}",
            )
        return mp3_path.read_bytes()


@app.get("/health")
async def health():
    voice = DEFAULT_VOICE
    ready = (MODEL_DIR / f"{voice}.onnx").exists()
    return {"status": "ok" if ready else "loading", "service": "piper", "voice": voice, "model_ready": ready}


@app.post("/api/tts")
async def text_to_speech(body: TTSRequest):
    voice = body.voice or DEFAULT_VOICE
    audio = _synthesize_mp3(body.text, voice)
    return Response(content=audio, media_type="audio/mpeg")
