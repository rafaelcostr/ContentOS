"""Seed built-in workflow templates into PostgreSQL."""

from contentos_database.models import WorkflowDefinition
from contentos_shared.workflow_templates import BUILTIN_TEMPLATES
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def ensure_workflow_templates(db: AsyncSession) -> int:
    """Insert missing built-ins and sync steps/config for existing built-ins.

    Returns count of newly created rows (updates are applied in-place).
    """
    created = 0
    for tpl in BUILTIN_TEMPLATES.values():
        result = await db.execute(select(WorkflowDefinition).where(WorkflowDefinition.name == tpl["name"]))
        existing = result.scalar_one_or_none()
        if not existing:
            db.add(
                WorkflowDefinition(
                    name=tpl["name"],
                    description=tpl.get("description"),
                    steps=tpl["steps"],
                    config=tpl.get("config"),
                    is_default=tpl.get("is_default", False),
                    is_builtin=True,
                )
            )
            created += 1
            continue

        # Keep built-in definitions aligned with code (e.g. v3-quality gains new steps).
        existing.description = tpl.get("description")
        existing.steps = list(tpl["steps"])
        existing.config = tpl.get("config") or {}
        existing.is_default = bool(tpl.get("is_default", False))
        existing.is_builtin = True
        existing.org_id = None
        existing.slug = None
    return created
