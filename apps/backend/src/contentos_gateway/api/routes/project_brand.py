"""Brand Intelligence API — extends Project DNA on project_memory (Growth OS Fase 5)."""

from uuid import UUID

from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user, require_editor
from contentos_gateway.services.org_service import get_accessible_project
from contentos_memory import get_memory_service, reset_memory_service_cache
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/projects", tags=["Brand Intelligence"])


class BrandIdentityResponse(BaseModel):
    project_id: str
    mission: str = ""
    objectives: list[str] = Field(default_factory=list)
    values: list[str] = Field(default_factory=list)
    target_audience: str = ""
    editorial_rules: list[str] = Field(default_factory=list)
    color_palette: dict = Field(default_factory=dict)
    tone: str = ""
    vocabulary: list[str] = Field(default_factory=list)
    visual_style: dict = Field(default_factory=dict)
    narrator_persona: str = ""
    niche: str = ""
    goal: str = ""
    style: dict = Field(default_factory=dict)
    brand_context_preview: str = ""


class BrandIdentityPatchBody(BaseModel):
    mission: str | None = None
    objectives: list[str] | None = None
    values: list[str] | None = None
    target_audience: str | None = None
    editorial_rules: list[str] | None = None
    color_palette: dict | None = None
    tone: str | None = None
    vocabulary: list[str] | None = None
    visual_style: dict | None = None
    narrator_persona: str | None = None
    niche: str | None = None
    goal: str | None = None
    style: dict | None = None


def _to_brand_response(data) -> BrandIdentityResponse:
    brand = data.to_brand_dict()
    return BrandIdentityResponse(project_id=str(data.project_id), **brand)


@router.get("/{project_id}/brand", response_model=BrandIdentityResponse)
async def get_project_brand(
    project_id: UUID,
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
) -> BrandIdentityResponse:
    await get_accessible_project(db, project_id, user.id)
    data = await get_memory_service().get_async(db, project_id)
    return _to_brand_response(data)


@router.patch("/{project_id}/brand", response_model=BrandIdentityResponse)
async def patch_project_brand(
    project_id: UUID,
    body: BrandIdentityPatchBody,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_editor()),
) -> BrandIdentityResponse:
    await get_accessible_project(db, project_id, user.id)
    patch = body.model_dump(exclude_unset=True)
    if not patch:
        raise HTTPException(status_code=400, detail="No brand fields provided")
    updated = await get_memory_service().update_brand(db, project_id, patch)
    reset_memory_service_cache()
    return _to_brand_response(updated)
