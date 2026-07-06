"""Workflow builder API (V3 Tier D2)."""

from uuid import UUID

from contentos_database.models import User
from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user, require_editor
from contentos_gateway.services.org_service import ORG_HEADER, resolve_org_id
from contentos_gateway.services.workflow_builder_service import (
    create_custom_workflow,
    delete_custom_workflow,
    list_workflows_for_org,
    update_custom_workflow,
)
from contentos_shared.workflow_validation import STEP_CATALOG, WorkflowValidationError
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/workflows", tags=["Workflow Builder"])


class StepCatalogItem(BaseModel):
    key: str
    label: str
    tier: str


class WorkflowTemplateResponse(BaseModel):
    name: str
    slug: str | None
    org_id: UUID | None
    description: str | None
    steps: list[str]
    config: dict | None
    is_default: bool
    is_builtin: bool


class CustomWorkflowCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=80)
    description: str | None = None
    steps: list[str] = Field(min_length=1)


class CustomWorkflowUpdate(BaseModel):
    description: str | None = None
    steps: list[str] | None = Field(default=None, min_length=1)


def _to_response(w) -> WorkflowTemplateResponse:
    return WorkflowTemplateResponse(
        name=w.name,
        slug=w.slug,
        org_id=w.org_id,
        description=w.description,
        steps=list(w.steps),
        config=w.config,
        is_default=w.is_default,
        is_builtin=w.is_builtin,
    )


@router.get("/steps/catalog", response_model=list[StepCatalogItem])
async def step_catalog(_user: User = Depends(get_current_user)) -> list[StepCatalogItem]:
    return [StepCatalogItem(**item) for item in STEP_CATALOG]


@router.get("", response_model=list[WorkflowTemplateResponse])
async def list_workflows(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
    x_organization_id: str | None = Header(None, alias=ORG_HEADER),
) -> list[WorkflowTemplateResponse]:
    from contentos_database.workflow_seed import ensure_workflow_templates

    await ensure_workflow_templates(db)
    org_id = await resolve_org_id(db, user, x_organization_id)
    workflows = await list_workflows_for_org(db, org_id)
    return [_to_response(w) for w in workflows]


@router.get("/{name}", response_model=WorkflowTemplateResponse)
async def get_workflow(
    name: str,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
    x_organization_id: str | None = Header(None, alias=ORG_HEADER),
) -> WorkflowTemplateResponse:
    from contentos_database.models import WorkflowDefinition
    from sqlalchemy import select

    org_id = await resolve_org_id(db, user, x_organization_id)
    result = await db.execute(select(WorkflowDefinition).where(WorkflowDefinition.name == name))
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow template not found")
    if not workflow.is_builtin and workflow.org_id != org_id:
        raise HTTPException(status_code=404, detail="Workflow template not found")
    return _to_response(workflow)


@router.post("/custom", response_model=WorkflowTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_custom(
    body: CustomWorkflowCreate,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
    x_organization_id: str | None = Header(None, alias=ORG_HEADER),
) -> WorkflowTemplateResponse:
    org_id = await resolve_org_id(db, user, x_organization_id)
    try:
        row = await create_custom_workflow(
            db,
            org_id=org_id,
            user_id=user.id,
            slug=body.slug,
            description=body.description,
            steps=body.steps,
        )
    except WorkflowValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_response(row)


@router.put("/custom/{slug}", response_model=WorkflowTemplateResponse)
async def update_custom(
    slug: str,
    body: CustomWorkflowUpdate,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
    x_organization_id: str | None = Header(None, alias=ORG_HEADER),
) -> WorkflowTemplateResponse:
    org_id = await resolve_org_id(db, user, x_organization_id)
    try:
        row = await update_custom_workflow(
            db,
            org_id=org_id,
            slug=slug,
            description=body.description,
            steps=body.steps,
        )
    except WorkflowValidationError as exc:
        raise HTTPException(status_code=404 if "not found" in str(exc) else 400, detail=str(exc)) from exc
    return _to_response(row)


@router.delete("/custom/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom(
    slug: str,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor()),
    x_organization_id: str | None = Header(None, alias=ORG_HEADER),
) -> None:
    org_id = await resolve_org_id(db, user, x_organization_id)
    try:
        await delete_custom_workflow(db, org_id, slug)
    except WorkflowValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
