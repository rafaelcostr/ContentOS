"""Database access for agent model settings."""

from __future__ import annotations

import os
from datetime import UTC, datetime

from contentos_models.defaults import DEFAULT_AGENT_MODELS, default_model_for_agent
from contentos_models.domain.agent_model_config import AgentModelConfig
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def _row_to_config(row) -> AgentModelConfig:
    return AgentModelConfig(
        agent=row.agent,
        provider_type=row.provider_type,
        provider=row.provider,
        model=row.model,
        updated_at=row.updated_at,
    )


class AgentModelRepository:
    """Async repository for API / gateway."""

    async def list_all(self, db: AsyncSession) -> list[AgentModelConfig]:
        from contentos_database.models import AgentModelSetting

        result = await db.execute(select(AgentModelSetting))
        rows = {r.agent: r for r in result.scalars().all()}
        configs: list[AgentModelConfig] = []
        for agent in DEFAULT_AGENT_MODELS:
            if agent in rows:
                configs.append(_row_to_config(rows[agent]))
            else:
                defaults = default_model_for_agent(agent)
                configs.append(AgentModelConfig(agent=agent, **defaults))
        return configs

    async def get(self, db: AsyncSession, agent: str) -> AgentModelConfig | None:
        from contentos_database.models import AgentModelSetting

        result = await db.execute(select(AgentModelSetting).where(AgentModelSetting.agent == agent))
        row = result.scalar_one_or_none()
        if row:
            return _row_to_config(row)
        if agent in DEFAULT_AGENT_MODELS:
            defaults = default_model_for_agent(agent)
            return AgentModelConfig(agent=agent, **defaults)
        return None

    async def upsert(
        self,
        db: AsyncSession,
        agent: str,
        provider_type: str,
        provider: str,
        model: str,
    ) -> AgentModelConfig:
        from contentos_database.models import AgentModelSetting

        result = await db.execute(select(AgentModelSetting).where(AgentModelSetting.agent == agent))
        row = result.scalar_one_or_none()
        now = datetime.now(UTC)
        if row:
            row.provider_type = provider_type
            row.provider = provider
            row.model = model
            row.updated_at = now
        else:
            row = AgentModelSetting(
                agent=agent,
                provider_type=provider_type,
                provider=provider,
                model=model,
                updated_at=now,
            )
            db.add(row)
        await db.flush()
        return _row_to_config(row)

    async def ensure_defaults(self, db: AsyncSession) -> int:
        from contentos_database.models import AgentModelSetting

        result = await db.execute(select(AgentModelSetting.agent))
        existing = set(result.scalars().all())
        created = 0
        for agent, meta in DEFAULT_AGENT_MODELS.items():
            if agent in existing:
                continue
            defaults = default_model_for_agent(agent)
            db.add(
                AgentModelSetting(
                    agent=agent,
                    provider_type=defaults["provider_type"],
                    provider=defaults["provider"],
                    model=defaults["model"],
                )
            )
            created += 1
        if created:
            await db.flush()
        return created


def load_all_sync() -> dict[str, AgentModelConfig]:
    """Sync load for Celery workers (PostgreSQL via psycopg2)."""
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        return _defaults_only()

    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace(
        "postgresql://", "postgresql+psycopg2://"
    )
    try:
        from contentos_database.models import AgentModelSetting
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        engine = create_engine(sync_url, pool_pre_ping=True)
        with Session(engine) as session:
            rows = session.execute(select(AgentModelSetting)).scalars().all()
            by_agent = {r.agent: _row_to_config(r) for r in rows}
    except Exception:
        return _defaults_only()

    configs = _defaults_only()
    configs.update(by_agent)
    return configs


def _defaults_only() -> dict[str, AgentModelConfig]:
    return {
        agent: AgentModelConfig(agent=agent, **default_model_for_agent(agent))
        for agent in DEFAULT_AGENT_MODELS
    }
