"""Project-scoped voice library helpers (V5.1.2)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contentos_shared.voice.profile import (
    BUILTIN_PROFILES,
    VoiceProfileSettings,
    resolve_builtin_profile,
)


async def project_voice_payload_hints(session: AsyncSession, project_id: UUID) -> dict[str, Any]:
    """Return payload keys for pipeline voice step when not explicitly set."""
    default = await resolve_project_default_profile(session, project_id)
    if not default:
        return {}
    if default.profile_id:
        return {"voice_profile_id": default.profile_id}
    if default.is_builtin:
        return {"voice_profile_name": default.name}
    return {}


async def resolve_project_default_profile(
    session: AsyncSession,
    project_id: UUID,
) -> VoiceProfileSettings | None:
    from contentos_database.models import ProjectMemory, VoiceProfile

    row = await session.execute(
        select(VoiceProfile)
        .where(
            VoiceProfile.project_id == project_id,
            VoiceProfile.is_default.is_(True),
        )
        .limit(1)
    )
    profile = row.scalar_one_or_none()
    if profile:
        return VoiceProfileSettings(
            name=profile.name,
            provider=profile.provider,
            voice_id=profile.voice_id or "",
            speed=float(profile.speed),
            pitch_semitones=float(profile.pitch_semitones),
            pause_ms=int(profile.pause_ms),
            profile_id=str(profile.id),
        )

    memory = await session.get(ProjectMemory, project_id)
    if memory and memory.default_voice_builtin:
        builtin = memory.default_voice_builtin.strip().lower()
        if builtin in BUILTIN_PROFILES:
            return resolve_builtin_profile(builtin)

    return None


def load_project_builtin_default_sync(project_id) -> VoiceProfileSettings | None:
    from contentos_memory.infrastructure.db_repository import load_sync

    memory = load_sync(project_id)
    if memory.default_voice_builtin:
        builtin = memory.default_voice_builtin.strip().lower()
        if builtin in BUILTIN_PROFILES:
            return resolve_builtin_profile(builtin)
    return None
