from typing import Any

from contentos_ai_gateway.deps import ai_service
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

router = APIRouter(prefix="/v1/subtitle", tags=["Subtitle"])


@router.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    provider: str = Form(default="local"),
    model: str | None = Form(default=None),
    agent: str | None = Form(default=None),
) -> dict[str, Any]:
    try:
        audio_bytes = await file.read()
        return await ai_service.transcribe(
            provider=provider,
            audio_bytes=audio_bytes,
            filename=file.filename or "audio.mp3",
            model=model,
            agent=agent,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
