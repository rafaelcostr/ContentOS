"""Custom workflow CRUD (V3 Tier D2)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from contentos_database.models import WorkflowDefinition
from contentos_shared.workflow_validation import (
    WorkflowValidationError,
    custom_workflow_name,
    validate_slug,
    validate_workflow_steps,
)
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession


async def list_workflows_for_org(db: AsyncSession, org_id: UUID) -> list[WorkflowDefinition]:
    result = await db.execute(
        select(WorkflowDefinition)
        .where(or_(WorkflowDefinition.is_builtin.is_(True), WorkflowDefinition.org_id == org_id))
        .order_by(WorkflowDefinition.is_builtin.desc(), WorkflowDefinition.name)
    )
    return list(result.scalars().all())


async def get_custom_workflow(db: AsyncSession, org_id: UUID, slug: str) -> WorkflowDefinition | None:
    result = await db.execute(
        select(WorkflowDefinition).where(
            WorkflowDefinition.org_id == org_id,
            WorkflowDefinition.slug == slug,
            WorkflowDefinition.is_builtin.is_(False),
        )
    )
    return result.scalar_one_or_none()


async def create_custom_workflow(
    db: AsyncSession,
    *,
    org_id: UUID,
    user_id: UUID,
    slug: str,
    description: str | None,
    steps: list[str],
) -> WorkflowDefinition:
    clean_slug = validate_slug(slug)
    clean_steps = validate_workflow_steps(steps)
    if await get_custom_workflow(db, org_id, clean_slug):
        raise WorkflowValidationError("Workflow slug already exists in this organization")

    row = WorkflowDefinition(
        name=custom_workflow_name(str(org_id), clean_slug),
        slug=clean_slug,
        org_id=org_id,
        description=description,
        steps=clean_steps,
        config={},
        is_default=False,
        is_builtin=False,
        created_by_user_id=user_id,
    )
    db.add(row)
    await db.flush()
    return row


async def update_custom_workflow(
    db: AsyncSession,
    *,
    org_id: UUID,
    slug: str,
    description: str | None,
    steps: list[str] | None,
) -> WorkflowDefinition:
    row = await get_custom_workflow(db, org_id, slug)
    if not row:
        raise WorkflowValidationError("Custom workflow not found")
    if description is not None:
        row.description = description
    if steps is not None:
        row.steps = validate_workflow_steps(steps)
    row.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return row


async def delete_custom_workflow(db: AsyncSession, org_id: UUID, slug: str) -> None:
    row = await get_custom_workflow(db, org_id, slug)
    if not row:
        raise WorkflowValidationError("Custom workflow not found")
    await db.delete(row)
    await db.flush()
