"""Gateway-wide rate limiting (V5.5.4)."""

from __future__ import annotations

import os
import time


def gateway_rate_limit_enabled() -> bool:
    return os.getenv("GATEWAY_RATE_LIMIT_ENABLED", "true").lower() in ("1", "true", "yes")


def gateway_rate_limit_per_minute() -> int:
    try:
        return max(1, int(os.getenv("GATEWAY_RATE_LIMIT_PER_MINUTE", "300")))
    except ValueError:
        return 300


def gateway_rate_limit_exempt_paths() -> set[str]:
    raw = os.getenv("GATEWAY_RATE_LIMIT_EXEMPT_PATHS", "/health,/health/ready,/metrics,/docs,/redoc,/openapi.json")
    return {p.strip() for p in raw.split(",") if p.strip()}


class GatewayRateLimiter:
    """Per-client fixed-window rate limit (Redis with in-memory fallback)."""

    def __init__(self) -> None:
        self._memory: dict[str, tuple[int, int]] = {}

    async def check(self, client_key: str, limit: int) -> bool:
        """Return True if request is allowed."""
        bucket = int(time.time()) // 60
        redis_key = f"ratelimit:gateway:{client_key}:{bucket}"
        count = await self._increment(redis_key, bucket)
        return count <= limit

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


_limiter: GatewayRateLimiter | None = None


def get_gateway_rate_limiter() -> GatewayRateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = GatewayRateLimiter()
    return _limiter
