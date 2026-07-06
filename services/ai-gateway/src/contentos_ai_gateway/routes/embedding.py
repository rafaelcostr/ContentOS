from typing import Any

from contentos_ai_gateway.deps import ai_service
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1/embeddings", tags=["Embeddings"])


class EmbedRequest(BaseModel):
    provider: str = Field(default="ollama")
    text: str
    model: str | None = None
    agent: str | None = None


@router.post("")
async def embed(body: EmbedRequest) -> dict[str, Any]:
    try:
        vector = await ai_service.embed(
            provider=body.provider,
            text=body.text,
            model=body.model,
            agent=body.agent,
        )
        return {"embedding": vector, "dimensions": len(vector)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
