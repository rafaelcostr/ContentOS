"""Prompt API routes."""

from contentos_gateway.api.deps import get_current_user, require_editor
from contentos_prompts import get_prompt_service
from contentos_prompts.application.prompt_service import reset_prompt_service_cache
from contentos_prompts.domain.prompt_version import PromptDefinition
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/prompts", tags=["Prompts"])


class PromptSummary(BaseModel):
    id: str
    version: str
    agent: str
    variables: list[str]
    description: str = ""
    source: str


class PromptDetail(PromptSummary):
    system_template: str
    user_template: str
    raw_content: str = ""


class PromptVersionItem(BaseModel):
    version: str
    updated_at: str
    source: str


class PromptUpdateBody(BaseModel):
    content: str = Field(..., min_length=10, description="Full .md file with YAML frontmatter")


class PromptRenderBody(BaseModel):
    variables: dict[str, str] = Field(default_factory=dict)


class PromptRenderResponse(BaseModel):
    id: str
    version: str
    system: str
    user: str


def _to_summary(p: PromptDefinition) -> PromptSummary:
    return PromptSummary(**p.to_dict())


def _to_detail(p: PromptDefinition) -> PromptDetail:
    data = p.to_dict()
    data["raw_content"] = p.raw_content
    return PromptDetail(**data)


@router.get("", response_model=list[PromptSummary])
async def list_prompts(_user=Depends(get_current_user)) -> list[PromptSummary]:
    return [PromptSummary(**item) for item in get_prompt_service().list_prompts()]


@router.post("/reload")
async def reload_prompts(_user=Depends(require_editor())) -> dict:
    reset_prompt_service_cache()
    service = get_prompt_service()
    service.reload()
    return {"status": "ok", "count": len(service.list_prompts())}


@router.get("/{prompt_id}", response_model=PromptDetail)
async def get_prompt(prompt_id: str, _user=Depends(get_current_user)) -> PromptDetail:
    try:
        return _to_detail(get_prompt_service().get_prompt(prompt_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{prompt_id}/versions", response_model=list[PromptVersionItem])
async def get_prompt_versions(prompt_id: str, _user=Depends(get_current_user)) -> list[PromptVersionItem]:
    try:
        versions = get_prompt_service().get_versions(prompt_id)
        return [
            PromptVersionItem(version=v.version, updated_at=v.updated_at.isoformat(), source=v.source)
            for v in versions
        ]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/{prompt_id}", response_model=PromptDetail)
async def update_prompt(
    prompt_id: str,
    body: PromptUpdateBody,
    _user=Depends(require_editor()),
) -> PromptDetail:
    try:
        updated = get_prompt_service().update_prompt(prompt_id, body.content)
        reset_prompt_service_cache()
        return _to_detail(updated)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{prompt_id}/render", response_model=PromptRenderResponse)
async def render_prompt(
    prompt_id: str,
    body: PromptRenderBody,
    _user=Depends(get_current_user),
) -> PromptRenderResponse:
    try:
        rendered = get_prompt_service().render(prompt_id, body.variables)
        return PromptRenderResponse(**rendered.to_dict())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
