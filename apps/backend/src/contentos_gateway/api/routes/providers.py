"""Provider configuration API."""

import os

import httpx
from contentos_database.models import User
from contentos_gateway.api.deps import get_current_user
from contentos_shared.providers.factory import get_provider_factory
from contentos_shared.providers.health import check_all_providers
from fastapi import APIRouter, Depends
from pydantic import BaseModel

router = APIRouter(prefix="/providers", tags=["Providers"])


class ProviderStatus(BaseModel):
    text: str
    speech: str
    subtitle: str
    mode: str = "direct"
    ai_gateway_url: str | None = None
    available_text: list[str]
    available_speech: list[str]
    available_subtitle: list[str]


class ProviderHealthItem(BaseModel):
    name: str
    url: str
    healthy: bool
    detail: str = ""


class ProvidersHealthResponse(BaseModel):
    all_healthy: bool
    providers: list[ProviderHealthItem]


@router.get("/status", response_model=ProviderStatus)
async def provider_status(_user: User = Depends(get_current_user)) -> ProviderStatus:
    factory = get_provider_factory()
    status = factory.status()
    gateway_url = os.getenv("AI_GATEWAY_URL") if status.get("mode") == "ai-gateway" else None
    available_text = ["ollama", "openai", "claude", "gemini", "deepseek", "mistral", "qwen", "llama"]
    return ProviderStatus(
        text=status["text"],
        speech=status["speech"],
        subtitle=status["subtitle"],
        mode=status.get("mode", "direct"),
        ai_gateway_url=gateway_url,
        available_text=available_text,
        available_speech=["piper", "elevenlabs"],
        available_subtitle=["local", "whisper", "openai"],
    )


@router.get("/ai-gateway/health")
async def ai_gateway_health(_user: User = Depends(get_current_user)) -> dict:
    """Proxy health check for the AI Gateway service."""
    base = os.getenv("AI_GATEWAY_URL", "http://ai-gateway:8020").rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base}/health")
            response.raise_for_status()
            return {"healthy": True, "url": base, **response.json()}
    except Exception as exc:
        return {"healthy": False, "url": base, "error": str(exc)}


@router.get("/health", response_model=ProvidersHealthResponse)
async def providers_health(_user: User = Depends(get_current_user)) -> ProvidersHealthResponse:
    results = await check_all_providers()
    items = [ProviderHealthItem(name=r.name, url=r.url, healthy=r.healthy, detail=r.detail) for r in results]
    return ProvidersHealthResponse(
        all_healthy=all(r.healthy for r in results),
        providers=items,
    )
