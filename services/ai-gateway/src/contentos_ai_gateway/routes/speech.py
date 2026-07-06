from contentos_ai_gateway.deps import ai_service
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1/speech", tags=["Speech"])


class TTSRequest(BaseModel):
    provider: str = Field(default="piper")
    text: str
    model: str | None = None
    voice: str | None = None
    agent: str | None = Field(default=None, description="Agent name for Model Manager routing")


@router.post("/tts")
async def text_to_speech(body: TTSRequest) -> Response:
    try:
        audio = await ai_service.text_to_speech(
            provider=body.provider,
            text=body.text,
            model=body.model,
            voice=body.voice,
            agent=body.agent,
        )
        return Response(content=audio, media_type="audio/mpeg")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
