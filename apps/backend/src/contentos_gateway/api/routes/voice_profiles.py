"""Voice profile API — V5.1.1 + preview studio (V5.1.5)."""

from __future__ import annotations

from uuid import UUID

from contentos_database.models import User
from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user, require_editor
from contentos_gateway.services.org_service import get_accessible_project
from contentos_gateway.services.voice_profile_service import VoiceProfileService
from contentos_shared.voice.narration import build_profiled_speech_provider, synthesize_narration
from contentos_shared.voice.profile import (
    BUILTIN_PROFILES,
    VoiceProfileSettings,
    normalize_pause_ms,
    normalize_pitch,
    normalize_speed,
    resolve_builtin_profile,
)
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/voice-profiles", tags=["Voice Profiles"])


class VoiceProfileBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    project_id: UUID | None = None
    provider: str = "piper"
    voice_id: str | None = None
    speed: float = 1.0
    pitch_semitones: float = 0.0
    pause_ms: int = 300
    is_default: bool = False

    @field_validator("speed")
    @classmethod
    def validate_speed(cls, value: float) -> float:
        return normalize_speed(value)

    @field_validator("pitch_semitones")
    @classmethod
    def validate_pitch(cls, value: float) -> float:
        return normalize_pitch(value)

    @field_validator("pause_ms")
    @classmethod
    def validate_pause(cls, value: int) -> int:
        return normalize_pause_ms(value)


class VoiceProfilePatchBody(BaseModel):
    name: str | None = None
    provider: str | None = None
    voice_id: str | None = None
    speed: float | None = None
    pitch_semitones: float | None = None
    pause_ms: int | None = None
    is_default: bool | None = None


class VoicePreviewBody(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)
    profile_id: UUID | None = None
    builtin_name: str | None = None
    provider: str = "piper"
    voice_id: str | None = None
    speed: float | None = None
    pitch_semitones: float | None = None
    pause_ms: int | None = None

    @field_validator("speed")
    @classmethod
    def validate_speed(cls, value: float | None) -> float | None:
        return normalize_speed(value) if value is not None else value

    @field_validator("pitch_semitones")
    @classmethod
    def validate_pitch(cls, value: float | None) -> float | None:
        return normalize_pitch(value) if value is not None else value

    @field_validator("pause_ms")
    @classmethod
    def validate_pause(cls, value: int | None) -> int | None:
        return normalize_pause_ms(value) if value is not None else value


class VoiceProfileResponse(BaseModel):
    id: str
    project_id: str | None
    name: str
    slug: str
    provider: str
    voice_id: str | None
    speed: float
    pitch_semitones: float
    pause_ms: int
    is_default: bool
    is_builtin: bool = False


def _to_response(row) -> VoiceProfileResponse:
    return VoiceProfileResponse(
        id=str(row.id),
        project_id=str(row.project_id) if row.project_id else None,
        name=row.name,
        slug=row.slug,
        provider=row.provider,
        voice_id=row.voice_id,
        speed=row.speed,
        pitch_semitones=row.pitch_semitones,
        pause_ms=row.pause_ms,
        is_default=row.is_default,
    )


def _resolve_preview_profile(body: VoicePreviewBody, db_profile: VoiceProfileSettings | None) -> VoiceProfileSettings:
    if db_profile:
        base = db_profile
    elif body.builtin_name:
        base = resolve_builtin_profile(body.builtin_name)
    else:
        base = BUILTIN_PROFILES["default"]

    return VoiceProfileSettings(
        name=base.name,
        provider=str(body.provider or base.provider),
        voice_id=str(body.voice_id or base.voice_id or ""),
        speed=body.speed if body.speed is not None else base.speed,
        pitch_semitones=body.pitch_semitones if body.pitch_semitones is not None else base.pitch_semitones,
        pause_ms=body.pause_ms if body.pause_ms is not None else base.pause_ms,
        is_builtin=base.is_builtin,
        profile_id=base.profile_id,
    )


@router.get("/builtins", response_model=list[VoiceProfileResponse])
async def list_builtin_voice_profiles(
    _user: User = Depends(get_current_user),
) -> list[VoiceProfileResponse]:
    return [
        VoiceProfileResponse(
            id=f"builtin:{profile.name}",
            project_id=None,
            name=profile.name,
            slug=profile.name,
            provider=profile.provider,
            voice_id=profile.voice_id or None,
            speed=profile.speed,
            pitch_semitones=profile.pitch_semitones,
            pause_ms=profile.pause_ms,
            is_default=profile.name == "default",
            is_builtin=True,
        )
        for profile in VoiceProfileService.builtin_profiles()
    ]


@router.post("/preview")
async def preview_voice_profile(
    body: VoicePreviewBody,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> Response:
    db_profile: VoiceProfileSettings | None = None
    if body.profile_id:
        service = VoiceProfileService(db)
        row = await service.get_profile(body.profile_id)
        if not row:
            raise HTTPException(status_code=404, detail="Voice profile not found")
        db_profile = VoiceProfileSettings(
            name=row.name,
            provider=row.provider,
            voice_id=row.voice_id or "",
            speed=float(row.speed),
            pitch_semitones=float(row.pitch_semitones),
            pause_ms=int(row.pause_ms),
            profile_id=str(row.id),
        )

    profile = _resolve_preview_profile(body, db_profile)
    provider = build_profiled_speech_provider(profile, agent="voice")
    try:
        audio = await synthesize_narration(provider, body.text, profile)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"TTS preview unavailable: {exc}") from exc
    if not audio:
        raise HTTPException(status_code=400, detail="Empty preview audio")
    return Response(content=audio, media_type="audio/mpeg")


@router.get("", response_model=list[VoiceProfileResponse])
async def list_voice_profiles(
    project_id: UUID | None = None,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[VoiceProfileResponse]:
    if project_id:
        await get_accessible_project(db, project_id, user.id)
    service = VoiceProfileService(db)
    rows = await service.list_profiles(project_id=project_id)
    return [_to_response(row) for row in rows]


@router.post("", response_model=VoiceProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_voice_profile(
    body: VoiceProfileBody,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> VoiceProfileResponse:
    if body.project_id:
        project = await get_accessible_project(db, body.project_id, user.id)
        org_id = project.org_id
    else:
        org_id = None

    service = VoiceProfileService(db)
    try:
        profile = await service.create_profile(
            name=body.name,
            project_id=body.project_id,
            org_id=org_id,
            provider=body.provider,
            voice_id=body.voice_id,
            speed=body.speed,
            pitch_semitones=body.pitch_semitones,
            pause_ms=body.pause_ms,
            is_default=body.is_default,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return _to_response(profile)


@router.get("/{profile_id}", response_model=VoiceProfileResponse)
async def get_voice_profile(
    profile_id: UUID,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> VoiceProfileResponse:
    service = VoiceProfileService(db)
    profile = await service.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Voice profile not found")
    return _to_response(profile)


@router.patch("/{profile_id}", response_model=VoiceProfileResponse)
async def patch_voice_profile(
    profile_id: UUID,
    body: VoiceProfilePatchBody,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_editor()),
) -> VoiceProfileResponse:
    service = VoiceProfileService(db)
    try:
        profile = await service.update_profile(profile_id, **body.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not profile:
        raise HTTPException(status_code=404, detail="Voice profile not found")
    await db.commit()
    return _to_response(profile)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_voice_profile(
    profile_id: UUID,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_editor()),
) -> None:
    service = VoiceProfileService(db)
    deleted = await service.delete_profile(profile_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Voice profile not found")
    await db.commit()
