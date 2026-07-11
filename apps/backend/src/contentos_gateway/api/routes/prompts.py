"""Prompt API routes."""

from contentos_gateway.api.deps import get_current_user, require_editor
from contentos_prompts import get_prompt_service
from contentos_prompts.application.prompt_service import reset_prompt_service_cache
from contentos_prompts.domain.prompt_version import PromptDefinition, PromptSuggestion
from fastapi import APIRouter, Depends, HTTPException, Query
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


class PromptSuggestionCreateBody(BaseModel):
    content: str = Field(..., min_length=10, description="Full .md file with YAML frontmatter")
    reason: str = Field(..., min_length=3)
    author: str = "autopilot"
    score: float = Field(default=0, ge=0, le=100)
    performance_basis: dict = Field(default_factory=dict)


class PromptSuggestionDecisionBody(BaseModel):
    reason: str = ""
    actor: str = "editor"


class PromptRollbackBody(BaseModel):
    version: str
    reason: str = "rollback"
    actor: str = "editor"


class PromptRenderBody(BaseModel):
    variables: dict[str, str] = Field(default_factory=dict)


class PromptRenderResponse(BaseModel):
    id: str
    version: str
    system: str
    user: str


class PromptSuggestionResponse(BaseModel):
    id: str
    prompt_id: str
    proposed_version: str
    current_version: str
    score: float
    reason: str
    author: str
    content: str
    status: str
    performance_basis: dict = Field(default_factory=dict)
    created_at: str = ""
    decided_at: str | None = None
    decided_by: str | None = None
    decision_reason: str | None = None


class PromptApprovalResponse(BaseModel):
    prompt: PromptDetail
    suggestion: PromptSuggestionResponse


def _to_summary(p: PromptDefinition) -> PromptSummary:
    return PromptSummary(**p.to_dict())


def _to_detail(p: PromptDefinition) -> PromptDetail:
    data = p.to_dict()
    data["raw_content"] = p.raw_content
    return PromptDetail(**data)


def _to_suggestion(item: PromptSuggestion) -> PromptSuggestionResponse:
    return PromptSuggestionResponse(**item.to_dict())


@router.get("", response_model=list[PromptSummary])
async def list_prompts(_user=Depends(get_current_user)) -> list[PromptSummary]:
    return [PromptSummary(**item) for item in get_prompt_service().list_prompts()]


@router.post("/reload")
async def reload_prompts(_user=Depends(require_editor())) -> dict:
    reset_prompt_service_cache()
    service = get_prompt_service()
    service.reload()
    return {"status": "ok", "count": len(service.list_prompts())}


@router.get("/suggestions", response_model=list[PromptSuggestionResponse])
async def list_prompt_suggestions(
    status: str | None = Query(default=None, pattern="^(pending|approved|rejected)$"),
    _user=Depends(get_current_user),
) -> list[PromptSuggestionResponse]:
    return [_to_suggestion(item) for item in get_prompt_service().list_suggestions(status=status)]


@router.post("/suggestions/{suggestion_id}/approve", response_model=PromptApprovalResponse)
async def approve_prompt_suggestion(
    suggestion_id: str,
    body: PromptSuggestionDecisionBody,
    _user=Depends(require_editor()),
) -> PromptApprovalResponse:
    service = get_prompt_service()
    try:
        updated = service.approve_suggestion(suggestion_id, approver=body.actor, reason=body.reason or "approved")
        reset_prompt_service_cache()
        service = get_prompt_service()
        suggestion = service.get_suggestion(suggestion_id)
        return PromptApprovalResponse(prompt=_to_detail(updated), suggestion=_to_suggestion(suggestion))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/suggestions/{suggestion_id}/reject", response_model=PromptSuggestionResponse)
async def reject_prompt_suggestion(
    suggestion_id: str,
    body: PromptSuggestionDecisionBody,
    _user=Depends(require_editor()),
) -> PromptSuggestionResponse:
    try:
        rejected = get_prompt_service().reject_suggestion(
            suggestion_id,
            reviewer=body.actor,
            reason=body.reason or "rejected",
        )
        return _to_suggestion(rejected)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
        return [PromptVersionItem(version=v.version, updated_at=v.updated_at.isoformat(), source=v.source) for v in versions]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{prompt_id}/suggestions", response_model=PromptSuggestionResponse)
async def create_prompt_suggestion(
    prompt_id: str,
    body: PromptSuggestionCreateBody,
    _user=Depends(require_editor()),
) -> PromptSuggestionResponse:
    try:
        suggestion = get_prompt_service().suggest_prompt_update(
            prompt_id,
            body.content,
            reason=body.reason,
            author=body.author,
            score=body.score,
            performance_basis=body.performance_basis,
        )
        return _to_suggestion(suggestion)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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


@router.post("/{prompt_id}/rollback", response_model=PromptDetail)
async def rollback_prompt(
    prompt_id: str,
    body: PromptRollbackBody,
    _user=Depends(require_editor()),
) -> PromptDetail:
    try:
        rolled_back = get_prompt_service().rollback_prompt(
            prompt_id,
            body.version,
            author=body.actor,
            reason=body.reason,
        )
        reset_prompt_service_cache()
        return _to_detail(rolled_back)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
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
