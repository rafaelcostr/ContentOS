"""Redis-backed cache storage."""

from __future__ import annotations

import json
import os
from typing import Any

from contentos_cache.domain.cache_key import agent_key_pattern


class RedisCacheBackend:
    def __init__(self, redis_url: str | None = None) -> None:
        self.redis_url = redis_url or os.getenv(
            "CACHE_REDIS_URL",
            os.getenv("REDIS_URL", "redis://redis:6379/2"),
        )

    async def _client(self):
        import redis.asyncio as aioredis

        return aioredis.from_url(self.redis_url, decode_responses=True)

    async def get(self, key: str) -> dict[str, Any] | None:
        client = await self._client()
        try:
            raw = await client.get(key)
            if not raw:
                return None
            return json.loads(raw)
        finally:
            await client.aclose()

    async def set(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        client = await self._client()
        try:
            await client.set(key, json.dumps(value), ex=ttl_seconds)
        finally:
            await client.aclose()

    async def delete(self, key: str) -> bool:
        client = await self._client()
        try:
            return bool(await client.delete(key))
        finally:
            await client.aclose()

    async def delete_agent(self, agent: str) -> int:
        client = await self._client()
        try:
            pattern = agent_key_pattern(agent)
            deleted = 0
            async for key in client.scan_iter(match=pattern, count=200):
                deleted += await client.delete(key)
            return deleted
        finally:
            await client.aclose()

    async def stats(self) -> dict[str, Any]:
        client = await self._client()
        try:
            by_agent: dict[str, int] = {}
            total = 0
            async for key in client.scan_iter(match="contentos:cache:*", count=200):
                total += 1
                parts = key.split(":")
                if len(parts) >= 3:
                    agent = parts[2]
                    by_agent[agent] = by_agent.get(agent, 0) + 1
            return {"total_keys": total, "by_agent": by_agent}
        finally:
            await client.aclose()
