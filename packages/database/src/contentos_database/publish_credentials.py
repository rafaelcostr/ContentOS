"""Load project credentials in worker context (Tier D4)."""

from __future__ import annotations

import os
from uuid import UUID

from contentos_database.channel_credentials import fetch_project_credentials, merge_credentials
from contentos_database.models import Channel
from contentos_database.oauth_tokens import refresh_channel_token_if_needed
from contentos_database.session import get_session_factory, init_db
from sqlalchemy import select


async def load_merged_project_credentials(
    project_id: UUID,
    env_credentials: dict[str, dict],
) -> dict[str, dict]:
    """Load DB channel credentials (with token refresh) merged over env fallback."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return env_credentials

    try:
        session_factory = get_session_factory()
        if session_factory is None:
            init_db(database_url)
        session_factory = get_session_factory()
        if session_factory is None:
            return env_credentials

        async with session_factory() as db:
            result = await db.execute(
                select(Channel)
                .where(Channel.project_id == project_id, Channel.is_active.is_(True))
                .order_by(Channel.created_at.desc())
            )
            for channel in result.scalars().all():
                await refresh_channel_token_if_needed(channel)
            await db.commit()
            db_creds = await fetch_project_credentials(db, project_id)
            return merge_credentials(env_credentials, db_creds)
    except Exception:
        return env_credentials
