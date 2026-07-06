"""Project memory API routes."""

from uuid import UUID

from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user, require_editor
from contentos_gateway.services.org_service import get_accessible_project
from contentos_memory import ProjectMemoryData, get_memory_service, reset_memory_service_cache
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/projects", tags=["Memory"])


class ProjectMemoryResponse(BaseModel):
    project_id: str
    tone: str = ""
    vocabulary: list[str] = Field(default_factory=list)
    cta: str = ""
    avg_duration: float | None = None
    hook_style: str = ""
    niche: str = ""
    goal: str = ""
    style: dict = Field(default_factory=dict)
    history: list[dict] = Field(default_factory=list)
    humor_level: float | None = None
    pace: str = ""
    visual_style: dict = Field(default_factory=dict)
    narrator_persona: str = ""
    preferred_formats: list[str] = Field(default_factory=list)
    hook_patterns: list[str] = Field(default_factory=list)
    cta_style: str = ""
    memory_context_preview: str = ""
    dna_context_preview: str = ""


class ProjectMemoryUpdateBody(BaseModel):
    tone: str = ""
    vocabulary: list[str] = Field(default_factory=list)
    cta: str = ""
    avg_duration: float | None = None
    hook_style: str = ""
    niche: str = ""
    goal: str = ""
    style: dict = Field(default_factory=dict)
    history: list[dict] = Field(default_factory=list)
    humor_level: float | None = None
    pace: str = ""
    visual_style: dict = Field(default_factory=dict)
    narrator_persona: str = ""
    preferred_formats: list[str] = Field(default_factory=list)
    hook_patterns: list[str] = Field(default_factory=list)
    cta_style: str = ""


def _to_response(data: ProjectMemoryData) -> ProjectMemoryResponse:
    payload = data.to_dict()
    payload.pop("dna_context_preview", None)
    return ProjectMemoryResponse(
        **payload,
        memory_context_preview=data.format_context(),
        dna_context_preview=data.format_dna_context(),
    )


@router.get("/{project_id}/memory", response_model=ProjectMemoryResponse)
async def get_project_memory(
    project_id: UUID,
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> ProjectMemoryResponse:
    await get_accessible_project(db, project_id, user.id)
    data = await get_memory_service().get_async(db, project_id)
    return _to_response(data)


@router.put("/{project_id}/memory", response_model=ProjectMemoryResponse)
async def update_project_memory(
    project_id: UUID,
    body: ProjectMemoryUpdateBody,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_editor()),
) -> ProjectMemoryResponse:
    await get_accessible_project(db, project_id, user.id)
    data = ProjectMemoryData.from_dict(project_id, body.model_dump())
    updated = await get_memory_service().update(db, data)
    reset_memory_service_cache()
    return _to_response(updated)
