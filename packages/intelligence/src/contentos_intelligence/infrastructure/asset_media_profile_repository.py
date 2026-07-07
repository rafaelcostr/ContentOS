"""Load asset media embeddings for take recommendation."""

from __future__ import annotations

import os
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session


def _sync_url(database_url: str | None = None) -> str:
    url = database_url or os.getenv("DATABASE_URL", "")
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace(
        "postgresql://", "postgresql+psycopg2://"
    )


def load_embeddings_by_asset_ids(
    asset_ids: list[UUID],
    *,
    database_url: str | None = None,
) -> dict[str, list[float]]:
    if not asset_ids:
        return {}
    url = _sync_url(database_url)
    if not url:
        return {}
    try:
        from contentos_database.models import AssetMediaProfile
        from sqlalchemy import create_engine
    except ImportError:
        return {}

    engine = create_engine(url, pool_pre_ping=True)
    try:
        with Session(engine) as session:
            rows = session.execute(
                select(AssetMediaProfile).where(AssetMediaProfile.asset_id.in_(asset_ids))
            ).scalars()
            out: dict[str, list[float]] = {}
            for row in rows:
                if row.embedding:
                    out[str(row.asset_id)] = list(row.embedding)
            return out
    except Exception:
        return {}
    finally:
        engine.dispose()


async def count_profiles_with_embeddings(session) -> int:
    """Count media profiles that have embeddings (async session)."""
    from contentos_database.models import AssetMediaProfile
    from sqlalchemy import func, select

    result = await session.scalar(
        select(func.count())
        .select_from(AssetMediaProfile)
        .where(AssetMediaProfile.embedding.isnot(None))
    )
    return int(result or 0)
