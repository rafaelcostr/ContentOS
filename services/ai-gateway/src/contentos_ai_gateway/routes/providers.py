from typing import Any

from contentos_ai_gateway.deps import ai_service
from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter(prefix="/v1/providers", tags=["Providers"])


class ProvidersResponse(BaseModel):
    text: list[str]
    speech: list[str]
    subtitle: list[str]
    image: list[str] = []
    vision: list[str] = []
    embedding: list[str] = []


@router.get("", response_model=ProvidersResponse)
async def list_providers() -> ProvidersResponse:
    providers = ai_service.list_providers()
    return ProvidersResponse(**providers)


@router.get("/resolve")
async def resolve_route(
    provider_type: str = Query(default="text"),
    provider: str | None = Query(default=None),
    model: str | None = Query(default=None),
    agent: str | None = Query(default=None),
) -> dict[str, Any]:
    """Resolve provider/model for an agent (Model Manager routing)."""
    return ai_service.resolve_route(
        provider_type=provider_type,
        provider=provider,
        model=model,
        agent=agent,
    )
