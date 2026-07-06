"""Model Manager API — per-agent provider and model configuration."""

from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user, require_platform_admin
from contentos_models import get_model_manager
from contentos_models.application.model_manager import reset_model_manager_cache
from contentos_models.defaults import EDITABLE_AGENTS
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/models", tags=["Models"])


class AgentModelResponse(BaseModel):
    agent: str
    provider_type: str
    provider: str
    model: str
    updated_at: str | None = None
    editable: bool = False


class AgentModelUpdateBody(BaseModel):
    provider: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)


class ProviderCatalogResponse(BaseModel):
    text: list[str]
    speech: list[str]
    subtitle: list[str]
    compute: list[str]


@router.get("/catalog", response_model=ProviderCatalogResponse)
async def get_provider_catalog(_user=Depends(get_current_user)) -> ProviderCatalogResponse:
    catalog = get_model_manager().catalog()
    return ProviderCatalogResponse(**catalog)


@router.get("", response_model=list[AgentModelResponse])
async def list_agent_models(
    db: AsyncSession = Depends(get_session),
    _user=Depends(get_current_user),
) -> list[AgentModelResponse]:
    configs = await get_model_manager().list_configs(db)
    return [
        AgentModelResponse(
            **cfg.to_dict(),
            editable=cfg.agent in EDITABLE_AGENTS,
        )
        for cfg in configs
    ]


@router.post("/seed")
async def seed_agent_models(
    db: AsyncSession = Depends(get_session),
    _user=Depends(require_platform_admin()),
) -> dict:
    created = await get_model_manager().ensure_defaults(db)
    reset_model_manager_cache()
    return {"status": "ok", "created": created}


@router.get("/{agent}", response_model=AgentModelResponse)
async def get_agent_model(
    agent: str,
    db: AsyncSession = Depends(get_session),
    _user=Depends(get_current_user),
) -> AgentModelResponse:
    cfg = await get_model_manager().get_config_async(db, agent)
    if not cfg:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent}")
    return AgentModelResponse(**cfg.to_dict(), editable=agent in EDITABLE_AGENTS)


@router.put("/{agent}", response_model=AgentModelResponse)
async def update_agent_model(
    agent: str,
    body: AgentModelUpdateBody,
    db: AsyncSession = Depends(get_session),
    _user=Depends(require_platform_admin()),
) -> AgentModelResponse:
    try:
        updated = await get_model_manager().update_config(db, agent, body.provider, body.model)
        reset_model_manager_cache()
        return AgentModelResponse(**updated.to_dict(), editable=agent in EDITABLE_AGENTS)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
