from contentos_ai_gateway.deps import ai_service
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1/image", tags=["Image"])


class GenerateImageRequest(BaseModel):
    provider: str = Field(default="local")
    prompt: str
    size: str = Field(default="1080x1920")
    model: str | None = None
    agent: str | None = Field(default=None)


@router.post("/generate")
async def generate_image(body: GenerateImageRequest) -> Response:
    try:
        image = await ai_service.generate_image(
            provider=body.provider,
            prompt=body.prompt,
            size=body.size,
            model=body.model,
            agent=body.agent,
        )
        return Response(content=image, media_type="image/jpeg")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
