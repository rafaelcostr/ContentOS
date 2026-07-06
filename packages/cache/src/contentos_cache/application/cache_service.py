"""Cache Manager application service."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from contentos_cache.domain.cache_key import build_cache_key
from contentos_cache.infrastructure.redis_cache import RedisCacheBackend

# TTL per agent (seconds)
AGENT_TTL_SECONDS: dict[str, int] = {
    "research": 7 * 24 * 3600,
    "script": 24 * 3600,
    "scene": 24 * 3600,
    "publisher": 24 * 3600,
    "clip_research": 7 * 24 * 3600,
    "analytics": 24 * 3600,
    "thumbnail": 24 * 3600,
}


def cache_enabled() -> bool:
    return os.getenv("USE_AI_CACHE", "true").lower() in ("true", "1", "yes")


class CacheService:
    """Redis cache for LLM JSON responses."""

    def __init__(self, backend: RedisCacheBackend | None = None) -> None:
        self._backend = backend or RedisCacheBackend()

    def ttl_for_agent(self, agent: str) -> int:
        return AGENT_TTL_SECONDS.get(agent, int(os.getenv("CACHE_DEFAULT_TTL_SECONDS", "86400")))

    def make_key(
        self,
        *,
        agent: str,
        topic: str,
        prompt_version: str,
        model: str,
        memory_context: str = "",
    ) -> str:
        return build_cache_key(
            agent=agent,
            topic=topic,
            prompt_version=prompt_version,
            model=model,
            memory_context=memory_context,
        )

    async def get(self, key: str) -> dict[str, Any] | None:
        if not cache_enabled():
            return None
        try:
            return await self._backend.get(key)
        except Exception:
            return None

    async def set(self, key: str, value: dict[str, Any], *, agent: str) -> None:
        if not cache_enabled():
            return
        try:
            await self._backend.set(key, value, self.ttl_for_agent(agent))
        except Exception:
            pass

    async def delete(self, key: str) -> bool:
        if not key.startswith("contentos:cache:"):
            key = f"contentos:cache:{key}" if ":" not in key else key
        try:
            return await self._backend.delete(key)
        except Exception:
            return False

    async def delete_agent(self, agent: str) -> int:
        try:
            return await self._backend.delete_agent(agent)
        except Exception:
            return 0

    async def stats(self) -> dict[str, Any]:
        base = {"enabled": cache_enabled(), "redis_url": os.getenv("CACHE_REDIS_URL", "")}
        if not cache_enabled():
            return {**base, "total_keys": 0, "by_agent": {}, "ttl_seconds": AGENT_TTL_SECONDS}
        try:
            data = await self._backend.stats()
            return {**base, **data, "ttl_seconds": AGENT_TTL_SECONDS}
        except Exception as exc:
            return {**base, "total_keys": 0, "by_agent": {}, "error": str(exc), "ttl_seconds": AGENT_TTL_SECONDS}


@lru_cache(maxsize=1)
def get_cache_service() -> CacheService:
    return CacheService()
