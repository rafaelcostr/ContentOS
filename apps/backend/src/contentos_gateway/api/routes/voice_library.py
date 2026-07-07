"""Project voice library API — V5.1.2."""

from __future__ import annotations

from uuid import UUID

from contentos_database.models import User
from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user, require_editor
from contentos_gateway.api.routes.voice_profiles import VoiceProfileResponse, _to_response
from contentos_gateway.services.org_service import get_accessible_project
from contentos_gateway.services.voice_library_service import VoiceLibraryService
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/projects", tags=["Voice Library"])


class VoiceLibraryResponse(BaseModel):
    project_id: str
    default_id: str | None
    default_builtin: str | None
    builtins: list[dict]
    custom: list[dict]
    entries: list[dict]


class SetVoiceDefaultBody(BaseModel):
    profile_id: UUID | None = None
    builtin_name: str | None = None


class CloneBuiltinBody(BaseModel):
    builtin_name: str = Field(..., min_length=1, max_length=80)
    name: str | None = Field(None, max_length=120)
    make_default: bool = False


@router.get("/{project_id}/voice-library", response_model=VoiceLibraryResponse)
async def get_project_voice_library(
    project_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> VoiceLibraryResponse:
    await get_accessible_project(db, project_id, user.id)
    library = await VoiceLibraryService(db).get_library(project_id)
    return VoiceLibraryResponse(**library.to_dict())


@router.put("/{project_id}/voice-library/default", response_model=VoiceLibraryResponse)
async def set_project_voice_default(
    project_id: UUID,
    body: SetVoiceDefaultBody,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> VoiceLibraryResponse:
    await get_accessible_project(db, project_id, user.id)
    service = VoiceLibraryService(db)
    try:
        library = await service.set_default(
            project_id,
            profile_id=body.profile_id,
            builtin_name=body.builtin_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return VoiceLibraryResponse(**library.to_dict())


@router.post(
    "/{project_id}/voice-library/clone",
    response_model=VoiceProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def clone_builtin_to_project(
    project_id: UUID,
    body: CloneBuiltinBody,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
) -> VoiceProfileResponse:
    project = await get_accessible_project(db, project_id, user.id)
    service = VoiceLibraryService(db)
    try:
        profile = await service.clone_builtin(
            project_id,
            builtin_name=body.builtin_name,
            name=body.name,
            org_id=project.org_id,
            make_default=body.make_default,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return _to_response(profile)
