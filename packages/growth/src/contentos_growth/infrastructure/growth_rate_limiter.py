"""Growth mutation rate limiter — Fase 18."""

from __future__ import annotations

import os
import time


def growth_rate_limit_enabled() -> bool:
    return os.getenv("GROWTH_RATE_LIMIT_ENABLED", "true").lower() in ("1", "true", "yes")


def growth_rate_limit_per_minute() -> int:
    try:
        return max(1, int(os.getenv("GROWTH_RATE_LIMIT_PER_MINUTE", "30")))
    except ValueError:
        return 30


class GrowthRateLimiter:
    """Per-key fixed-window limiter (Redis with in-memory fallback)."""

    def __init__(self) -> None:
        self._memory: dict[str, tuple[int, int]] = {}

    async def check(self, key: str, limit: int | None = None) -> bool:
        effective_limit = limit or growth_rate_limit_per_minute()
        bucket = int(time.time()) // 60
        redis_key = f"ratelimit:growth:{key}:{bucket}"
        count = await self._increment(redis_key, bucket)
        return count <= effective_limit

    async def _increment(self, redis_key: str, bucket: int) -> int:
        try:
            import redis.asyncio as aioredis

            url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            client = aioredis.from_url(url, decode_responses=True)
            try:
                count = await client.incr(redis_key)
                if count == 1:
                    await client.expire(redis_key, 60)
                return int(count)
            finally:
                await client.aclose()
        except Exception:
            current = self._memory.get(redis_key)
            if not current or current[0] != bucket:
                self._memory[redis_key] = (bucket, 1)
                return 1
            self._memory[redis_key] = (bucket, current[1] + 1)
            return current[1] + 1


_limiter: GrowthRateLimiter | None = None


def get_growth_rate_limiter() -> GrowthRateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = GrowthRateLimiter()
    return _limiter


async def assert_growth_rate_limit(user_id: str, action: str) -> None:
    if not growth_rate_limit_enabled():
        return
    allowed = await get_growth_rate_limiter().check(f"{user_id}:{action}")
    if not allowed:
        raise ValueError("Growth rate limit exceeded — tente novamente em alguns segundos")
