"""Model Manager application service."""

from __future__ import annotations

import time
from functools import lru_cache

from contentos_models.defaults import DEFAULT_AGENT_MODELS, EDITABLE_AGENTS, PROVIDER_CATALOG, default_model_for_agent
from contentos_models.domain.agent_model_config import AgentModelConfig
from contentos_models.infrastructure.db_repository import AgentModelRepository, load_all_sync
from sqlalchemy.ext.asyncio import AsyncSession


class ModelManager:
    """Resolves provider/model per agent — DB-backed with env fallbacks."""

    def __init__(self, cache_ttl_seconds: float = 30.0) -> None:
        self._repo = AgentModelRepository()
        self._cache_ttl = cache_ttl_seconds
        self._cache: dict[str, AgentModelConfig] = {}
        self._cache_loaded_at: float = 0.0

    def get_config(self, agent: str) -> AgentModelConfig:
        self._refresh_cache_if_needed()
        if agent in self._cache:
            return self._cache[agent]
        defaults = default_model_for_agent(agent)
        return AgentModelConfig(agent=agent, **defaults)

    def provider_and_model(self, agent: str) -> tuple[str, str]:
        cfg = self.get_config(agent)
        return cfg.provider, cfg.model

    def invalidate_cache(self) -> None:
        self._cache_loaded_at = 0.0
        self._cache.clear()

    async def list_configs(self, db: AsyncSession) -> list[AgentModelConfig]:
        return await self._repo.list_all(db)

    async def get_config_async(self, db: AsyncSession, agent: str) -> AgentModelConfig | None:
        return await self._repo.get(db, agent)

    async def update_config(
        self,
        db: AsyncSession,
        agent: str,
        provider: str,
        model: str,
    ) -> AgentModelConfig:
        if agent not in EDITABLE_AGENTS:
            raise ValueError(f"Agent '{agent}' is not configurable")
        meta = DEFAULT_AGENT_MODELS.get(agent)
        if not meta:
            raise ValueError(f"Unknown agent: {agent}")
        provider_type = meta["provider_type"]
        allowed = PROVIDER_CATALOG.get(provider_type, [])
        if provider not in allowed:
            raise ValueError(f"Provider '{provider}' not allowed for {provider_type}. Options: {allowed}")
        updated = await self._repo.upsert(db, agent, provider_type, provider, model)
        self.invalidate_cache()
        return updated

    async def ensure_defaults(self, db: AsyncSession) -> int:
        created = await self._repo.ensure_defaults(db)
        self.invalidate_cache()
        return created

    def catalog(self) -> dict[str, list[str]]:
        return PROVIDER_CATALOG

    def _refresh_cache_if_needed(self) -> None:
        now = time.monotonic()
        if self._cache and (now - self._cache_loaded_at) < self._cache_ttl:
            return
        self._cache = load_all_sync()
        self._cache_loaded_at = now


@lru_cache(maxsize=1)
def get_model_manager() -> ModelManager:
    return ModelManager()


def reset_model_manager_cache() -> None:
    get_model_manager.cache_clear()
