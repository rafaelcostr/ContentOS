from typing import Any

from contentos_ai_gateway.deps import ai_service
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

router = APIRouter(prefix="/v1/vision", tags=["Vision"])


@router.post("/analyze")
async def analyze_image(
    file: UploadFile = File(...),
    prompt: str = Form(default="Describe this image as JSON"),
    provider: str = Form(default="ollama"),
    model: str | None = Form(default=None),
    agent: str | None = Form(default=None),
) -> dict[str, Any]:
    try:
        image_bytes = await file.read()
        return await ai_service.analyze_image(
            provider=provider,
            image_bytes=image_bytes,
            prompt=prompt,
            model=model,
            agent=agent,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
