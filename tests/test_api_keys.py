"""Tier C5 — organization API keys."""

import pytest
from contentos_database.models import ApiKeyScope
from contentos_gateway.services.api_key_service import (
    ApiKeyRateLimiter,
    generate_api_key_material,
    hash_api_key,
    parse_key_prefix,
    scope_to_role,
)


def test_generate_and_parse_api_key():
    raw, prefix, key_hash = generate_api_key_material()
    assert raw.startswith("cos_")
    assert parse_key_prefix(raw) == prefix
    assert hash_api_key(raw) == key_hash
    assert len(key_hash) == 64


def test_parse_key_prefix_invalid():
    assert parse_key_prefix("invalid") is None
    assert parse_key_prefix("cos_onlyprefix") is None
    assert parse_key_prefix("cos_abc_") is None


def test_scope_to_role():
    assert scope_to_role(ApiKeyScope.READ) == "viewer"
    assert scope_to_role(ApiKeyScope.WRITE) == "editor"
    assert scope_to_role("read") == "viewer"
    assert scope_to_role("write") == "editor"


@pytest.mark.asyncio
async def test_rate_limiter_in_memory_fallback(monkeypatch):
    monkeypatch.setenv("API_KEY_REDIS_URL", "redis://localhost:0/0")
    monkeypatch.setattr("contentos_gateway.services.api_key_service.time.time", lambda: 1234567890)
    limiter = ApiKeyRateLimiter()
    key_id = __import__("uuid").uuid4()
    for _ in range(3):
        await limiter.check(key_id, 3)
    with pytest.raises(Exception) as exc:
        await limiter.check(key_id, 3)
    assert exc.value.status_code == 429
