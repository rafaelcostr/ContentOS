"""Voice profile CRUD — Gateway service (V5.1.1)."""

from __future__ import annotations

import re
from uuid import UUID

from contentos_database.models import VoiceProfile
from contentos_shared.voice.profile import (
    VALID_PROVIDERS,
    VoiceProfileSettings,
    list_builtin_profiles,
    normalize_pause_ms,
    normalize_pitch,
    normalize_speed,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:80] or "profile"


class VoiceProfileService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_profiles(
        self,
        *,
        project_id: UUID | None = None,
        limit: int = 100,
    ) -> list[VoiceProfile]:
        query = select(VoiceProfile).order_by(VoiceProfile.created_at.desc()).limit(limit)
        if project_id:
            query = query.where(VoiceProfile.project_id == project_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_profile(self, profile_id: UUID) -> VoiceProfile | None:
        return await self.session.get(VoiceProfile, profile_id)

    async def create_profile(
        self,
        *,
        name: str,
        project_id: UUID | None = None,
        org_id: UUID | None = None,
        provider: str = "piper",
        voice_id: str | None = None,
        speed: float = 1.0,
        pitch_semitones: float = 0.0,
        pause_ms: int = 300,
        is_default: bool = False,
    ) -> VoiceProfile:
        provider = provider.lower()
        if provider not in VALID_PROVIDERS:
            raise ValueError(f"provider must be one of: {', '.join(sorted(VALID_PROVIDERS))}")

        if is_default and project_id:
            await self._clear_project_default(project_id)

        profile = VoiceProfile(
            project_id=project_id,
            org_id=org_id,
            name=name.strip(),
            slug=_slugify(name),
            provider=provider,
            voice_id=voice_id,
            speed=normalize_speed(speed),
            pitch_semitones=normalize_pitch(pitch_semitones),
            pause_ms=normalize_pause_ms(pause_ms),
            is_default=is_default,
        )
        self.session.add(profile)
        await self.session.flush()
        return profile

    async def update_profile(self, profile_id: UUID, **fields) -> VoiceProfile | None:
        profile = await self.get_profile(profile_id)
        if not profile:
            return None

        if fields.get("name"):
            profile.name = str(fields["name"]).strip()
            profile.slug = _slugify(profile.name)
        if fields.get("provider"):
            provider = str(fields["provider"]).lower()
            if provider not in VALID_PROVIDERS:
                raise ValueError(f"provider must be one of: {', '.join(sorted(VALID_PROVIDERS))}")
            profile.provider = provider
        if "voice_id" in fields:
            profile.voice_id = fields["voice_id"]
        if fields.get("speed") is not None:
            profile.speed = normalize_speed(fields["speed"])
        if fields.get("pitch_semitones") is not None:
            profile.pitch_semitones = normalize_pitch(fields["pitch_semitones"])
        if fields.get("pause_ms") is not None:
            profile.pause_ms = normalize_pause_ms(fields["pause_ms"])
        if fields.get("is_default") is True and profile.project_id:
            await self._clear_project_default(profile.project_id)
            profile.is_default = True
        elif fields.get("is_default") is False:
            profile.is_default = False

        await self.session.flush()
        return profile

    async def delete_profile(self, profile_id: UUID) -> bool:
        profile = await self.get_profile(profile_id)
        if not profile:
            return False
        await self.session.delete(profile)
        await self.session.flush()
        return True

    async def _clear_project_default(self, project_id: UUID) -> None:
        result = await self.session.execute(
            select(VoiceProfile).where(
                VoiceProfile.project_id == project_id,
                VoiceProfile.is_default.is_(True),
            )
        )
        for row in result.scalars():
            row.is_default = False

    @staticmethod
    def builtin_profiles() -> list[VoiceProfileSettings]:
        return list_builtin_profiles()
