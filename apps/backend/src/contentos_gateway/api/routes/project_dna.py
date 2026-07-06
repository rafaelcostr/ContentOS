"""Project DNA API routes — Epic 8 V4."""

from uuid import UUID

from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user, require_editor
from contentos_gateway.services.org_service import get_accessible_project
from contentos_memory import get_memory_service, reset_memory_service_cache
from contentos_memory.domain.project_dna import VALID_FORMATS, VALID_PACES, clamp_humor_level, normalize_pace
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/projects", tags=["Project DNA"])


class ProjectDnaResponse(BaseModel):
    project_id: str
    humor_level: float | None = None
    pace: str = ""
    visual_style: dict = Field(default_factory=dict)
    narrator_persona: str = ""
    preferred_formats: list[str] = Field(default_factory=list)
    hook_patterns: list[str] = Field(default_factory=list)
    cta_style: str = ""
    dna_context_preview: str = ""


class ProjectDnaPatchBody(BaseModel):
    humor_level: float | None = None
    pace: str | None = None
    visual_style: dict | None = None
    narrator_persona: str | None = None
    preferred_formats: list[str] | None = None
    hook_patterns: list[str] | None = None
    cta_style: str | None = None

    @field_validator("humor_level")
    @classmethod
    def validate_humor(cls, value: float | None) -> float | None:
        return clamp_humor_level(value)

    @field_validator("pace")
    @classmethod
    def validate_pace(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return value
        normalized = normalize_pace(value)
        if not normalized:
            raise ValueError(f"pace must be one of: {', '.join(sorted(VALID_PACES))}")
        return normalized

    @field_validator("preferred_formats")
    @classmethod
    def validate_formats(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        invalid = [f for f in value if f not in VALID_FORMATS]
        if invalid:
            raise ValueError(f"unknown formats: {', '.join(invalid)}")
        return value


def _to_dna_response(data) -> ProjectDnaResponse:
    dna = data.to_dna_dict()
    return ProjectDnaResponse(project_id=str(data.project_id), **dna)


@router.get("/{project_id}/dna", response_model=ProjectDnaResponse)
async def get_project_dna(
    project_id: UUID,
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> ProjectDnaResponse:
    await get_accessible_project(db, project_id, user.id)
    data = await get_memory_service().get_async(db, project_id)
    return _to_dna_response(data)


@router.patch("/{project_id}/dna", response_model=ProjectDnaResponse)
async def patch_project_dna(
    project_id: UUID,
    body: ProjectDnaPatchBody,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_editor()),
) -> ProjectDnaResponse:
    await get_accessible_project(db, project_id, user.id)
    patch = body.model_dump(exclude_unset=True)
    if not patch:
        raise HTTPException(status_code=400, detail="No DNA fields provided")
    updated = await get_memory_service().update_dna(db, project_id, patch)
    reset_memory_service_cache()
    return _to_dna_response(updated)
