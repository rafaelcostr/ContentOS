"""Project voice library — builtins + custom profiles (V5.1.2)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from contentos_database.models import ProjectMemory, VoiceProfile
from contentos_gateway.services.voice_profile_service import VoiceProfileService
from contentos_shared.voice.profile import BUILTIN_PROFILES, resolve_builtin_profile
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class VoiceLibraryEntry:
    id: str
    name: str
    slug: str
    provider: str
    voice_id: str | None
    speed: float
    pitch_semitones: float
    pause_ms: int
    is_default: bool
    is_builtin: bool
    source: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "provider": self.provider,
            "voice_id": self.voice_id,
            "speed": self.speed,
            "pitch_semitones": self.pitch_semitones,
            "pause_ms": self.pause_ms,
            "is_default": self.is_default,
            "is_builtin": self.is_builtin,
            "source": self.source,
        }


@dataclass
class VoiceLibrarySnapshot:
    project_id: str
    default_id: str | None
    default_builtin: str | None
    builtins: list[VoiceLibraryEntry]
    custom: list[VoiceLibraryEntry]

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "default_id": self.default_id,
            "default_builtin": self.default_builtin,
            "builtins": [item.to_dict() for item in self.builtins],
            "custom": [item.to_dict() for item in self.custom],
            "entries": [item.to_dict() for item in self.builtins + self.custom],
        }


class VoiceLibraryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.profiles = VoiceProfileService(session)

    async def get_library(self, project_id: UUID) -> VoiceLibrarySnapshot:
        custom_rows = await self.profiles.list_profiles(project_id=project_id)
        memory = await self.session.get(ProjectMemory, project_id)
        default_builtin = (memory.default_voice_builtin or "").strip().lower() if memory else ""
        default_profile = next((row for row in custom_rows if row.is_default), None)

        builtins: list[VoiceLibraryEntry] = []
        for name, profile in BUILTIN_PROFILES.items():
            builtins.append(
                VoiceLibraryEntry(
                    id=f"builtin:{name}",
                    name=profile.name,
                    slug=name,
                    provider=profile.provider,
                    voice_id=profile.voice_id or None,
                    speed=profile.speed,
                    pitch_semitones=profile.pitch_semitones,
                    pause_ms=profile.pause_ms,
                    is_default=not default_profile and default_builtin == name,
                    is_builtin=True,
                    source="builtin",
                )
            )

        custom = [
            VoiceLibraryEntry(
                id=str(row.id),
                name=row.name,
                slug=row.slug,
                provider=row.provider,
                voice_id=row.voice_id,
                speed=row.speed,
                pitch_semitones=row.pitch_semitones,
                pause_ms=row.pause_ms,
                is_default=row.is_default,
                is_builtin=False,
                source="project",
            )
            for row in custom_rows
        ]

        return VoiceLibrarySnapshot(
            project_id=str(project_id),
            default_id=str(default_profile.id) if default_profile else None,
            default_builtin=default_builtin or None,
            builtins=builtins,
            custom=custom,
        )

    async def set_default(
        self,
        project_id: UUID,
        *,
        profile_id: UUID | None = None,
        builtin_name: str | None = None,
    ) -> VoiceLibrarySnapshot:
        memory = await self.session.get(ProjectMemory, project_id)
        if not memory:
            memory = ProjectMemory(project_id=project_id)
            self.session.add(memory)

        if profile_id:
            profile = await self.profiles.get_profile(profile_id)
            if not profile or profile.project_id != project_id:
                raise ValueError("Voice profile not found for this project")
            await self.profiles._clear_project_default(project_id)
            profile.is_default = True
            memory.default_voice_builtin = None
        elif builtin_name:
            key = builtin_name.strip().lower()
            if key not in BUILTIN_PROFILES:
                raise ValueError(f"Unknown builtin profile: {builtin_name}")
            await self.profiles._clear_project_default(project_id)
            memory.default_voice_builtin = key
        else:
            raise ValueError("profile_id or builtin_name required")

        await self.session.flush()
        return await self.get_library(project_id)

    async def clone_builtin(
        self,
        project_id: UUID,
        *,
        builtin_name: str,
        name: str | None = None,
        org_id: UUID | None = None,
        make_default: bool = False,
    ) -> VoiceProfile:
        template = resolve_builtin_profile(builtin_name)
        profile = await self.profiles.create_profile(
            name=name or f"{template.name} (projeto)",
            project_id=project_id,
            org_id=org_id,
            provider=template.provider,
            voice_id=template.voice_id or None,
            speed=template.speed,
            pitch_semitones=template.pitch_semitones,
            pause_ms=template.pause_ms,
            is_default=make_default,
        )
        if make_default:
            memory = await self.session.get(ProjectMemory, project_id)
            if memory:
                memory.default_voice_builtin = None
        return profile
