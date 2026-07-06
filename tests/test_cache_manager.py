"""Tests for Cache Manager."""

import pytest
from contentos_cache.application.cache_service import AGENT_TTL_SECONDS, CacheService, cache_enabled
from contentos_cache.domain.cache_key import agent_from_key, build_cache_key


def test_build_cache_key_deterministic():
    k1 = build_cache_key(
        agent="research",
        topic="GTA 6",
        prompt_version="1.0.0",
        model="qwen2.5:7b",
        memory_context="Nicho: games",
    )
    k2 = build_cache_key(
        agent="research",
        topic="GTA 6",
        prompt_version="1.0.0",
        model="qwen2.5:7b",
        memory_context="Nicho: games",
    )
    assert k1 == k2
    assert k1.startswith("contentos:cache:research:")


def test_build_cache_key_differs_by_memory():
    k1 = build_cache_key(agent="research", topic="x", prompt_version="1", model="m", memory_context="a")
    k2 = build_cache_key(agent="research", topic="x", prompt_version="1", model="m", memory_context="b")
    assert k1 != k2


def test_agent_from_key():
    key = build_cache_key(agent="script", topic="t", prompt_version="1", model="m")
    assert agent_from_key(key) == "script"


def test_ttl_research_longer_than_script():
    assert AGENT_TTL_SECONDS["research"] > AGENT_TTL_SECONDS["script"]


def test_cache_enabled_env(monkeypatch):
    monkeypatch.setenv("USE_AI_CACHE", "false")
    assert cache_enabled() is False
    monkeypatch.setenv("USE_AI_CACHE", "true")
    assert cache_enabled() is True


@pytest.mark.asyncio
async def test_cache_service_get_miss_without_redis(monkeypatch):
    monkeypatch.setenv("USE_AI_CACHE", "true")
    monkeypatch.setenv("CACHE_REDIS_URL", "redis://localhost:59999/2")
    service = CacheService()
    result = await service.get("contentos:cache:research:deadbeef")
    assert result is None
