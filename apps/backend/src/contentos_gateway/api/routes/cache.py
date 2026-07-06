"""Cache Manager API routes."""

from contentos_cache import get_cache_service
from contentos_gateway.api.deps import get_current_user, require_platform_admin
from fastapi import APIRouter, Depends
from pydantic import BaseModel

router = APIRouter(prefix="/cache", tags=["Cache"])


class CacheStatsResponse(BaseModel):
    enabled: bool
    total_keys: int
    by_agent: dict[str, int]
    ttl_seconds: dict[str, int]
    redis_url: str = ""
    error: str | None = None


class CacheDeleteResponse(BaseModel):
    deleted: bool | int
    key: str | None = None
    agent: str | None = None


@router.get("/stats", response_model=CacheStatsResponse)
async def cache_stats(_user=Depends(get_current_user)) -> CacheStatsResponse:
    data = await get_cache_service().stats()
    return CacheStatsResponse(**data)


@router.delete("/agent/{agent}", response_model=CacheDeleteResponse)
async def delete_agent_cache(agent: str, _user=Depends(require_platform_admin())) -> CacheDeleteResponse:
    count = await get_cache_service().delete_agent(agent)
    return CacheDeleteResponse(deleted=count, agent=agent)


@router.delete("/{key:path}", response_model=CacheDeleteResponse)
async def delete_cache_key(key: str, _user=Depends(require_platform_admin())) -> CacheDeleteResponse:
    deleted = await get_cache_service().delete(key)
    return CacheDeleteResponse(deleted=deleted, key=key)
