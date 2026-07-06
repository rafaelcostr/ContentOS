"""Organization API key helpers (V3 Tier C5)."""

from __future__ import annotations

import hashlib
import os
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from contentos_database.models import ApiKeyScope, OrganizationApiKey, User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

KEY_PREFIX = "cos_"


def default_rate_limit() -> int:
    try:
        return max(1, int(os.getenv("API_KEY_DEFAULT_RATE_LIMIT", "120")))
    except ValueError:
        return 120


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_api_key_material() -> tuple[str, str, str]:
    """Return (raw_key, key_prefix, key_hash). Raw key shown once to the user."""
    prefix = secrets.token_hex(6)
    secret = secrets.token_urlsafe(24)
    raw = f"{KEY_PREFIX}{prefix}_{secret}"
    return raw, prefix, hash_api_key(raw)


def parse_key_prefix(raw_key: str) -> str | None:
    if not raw_key.startswith(KEY_PREFIX) or "_" not in raw_key:
        return None
    rest = raw_key[len(KEY_PREFIX) :]
    prefix, sep, secret = rest.partition("_")
    if not prefix or not sep or not secret:
        return None
    return prefix


def scope_to_role(scope: ApiKeyScope | str) -> str:
    value = scope.value if isinstance(scope, ApiKeyScope) else str(scope)
    return "editor" if value == ApiKeyScope.WRITE.value else "viewer"


@dataclass
class ValidatedApiKey:
    record: OrganizationApiKey
    user: User


class ApiKeyRateLimiter:
    """Per-key fixed-window rate limit (Redis with in-memory fallback)."""

    def __init__(self) -> None:
        self._memory: dict[str, tuple[int, int]] = {}

    async def check(self, key_id: UUID, limit: int) -> None:
        bucket = int(time.time()) // 60
        redis_key = f"ratelimit:apikey:{key_id}:{bucket}"
        count = await self._increment(redis_key, bucket)
        if count > limit:
            from fastapi import HTTPException

            raise HTTPException(status_code=429, detail="API key rate limit exceeded")

    async def _increment(self, redis_key: str, bucket: int) -> int:
        try:
            import redis.asyncio as aioredis

            url = os.getenv("API_KEY_REDIS_URL") or os.getenv("REDIS_URL", "redis://localhost:6379/0")
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


_rate_limiter: ApiKeyRateLimiter | None = None


def get_rate_limiter() -> ApiKeyRateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = ApiKeyRateLimiter()
    return _rate_limiter


async def validate_api_key(db: AsyncSession, raw_key: str) -> ValidatedApiKey:
    from fastapi import HTTPException

    prefix = parse_key_prefix(raw_key.strip())
    if not prefix:
        raise HTTPException(status_code=401, detail="Invalid API key")

    result = await db.execute(
        select(OrganizationApiKey).where(
            OrganizationApiKey.key_prefix == prefix,
            OrganizationApiKey.is_active.is_(True),
        )
    )
    record = result.scalar_one_or_none()
    if not record or record.key_hash != hash_api_key(raw_key.strip()):
        raise HTTPException(status_code=401, detail="Invalid API key")

    user = await db.get(User, record.created_by_user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="API key owner inactive")

    await get_rate_limiter().check(record.id, record.rate_limit_per_minute)
    record.last_used_at = datetime.now(timezone.utc)
    return ValidatedApiKey(record=record, user=user)
