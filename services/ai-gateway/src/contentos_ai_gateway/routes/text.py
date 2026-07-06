from typing import Any

from contentos_ai_gateway.deps import ai_service
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1/text", tags=["Text"])


class ChatJsonRequest(BaseModel):
    provider: str = Field(default="ollama", description="Text provider key")
    system: str
    user: str
    model: str | None = None
    agent: str | None = Field(default=None, description="Agent name for Model Manager routing")


@router.post("/chat-json")
async def chat_json(body: ChatJsonRequest) -> dict[str, Any]:
    try:
        return await ai_service.chat_json(
            provider=body.provider,
            system=body.system,
            user=body.user,
            model=body.model,
            agent=body.agent,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
