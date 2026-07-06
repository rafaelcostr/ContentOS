"""Organization bootstrap and backfill (V3 Tier C1)."""

from __future__ import annotations

import re
from uuid import uuid4

from contentos_database.models import Organization, OrganizationMember, Pipeline, Project, User, UserRole
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:50]
    return slug or "org"


async def _unique_slug(db: AsyncSession, base: str) -> str:
    slug = slugify(base)
    candidate = slug
    n = 0
    while True:
        exists = await db.execute(select(Organization.id).where(Organization.slug == candidate))
        if not exists.scalar_one_or_none():
            return candidate
        n += 1
        candidate = f"{slug}-{n}"


async def create_personal_org(db: AsyncSession, user: User) -> Organization:
    """Create a personal workspace for a new user."""
    label = user.full_name or user.email.split("@")[0]
    org = Organization(
        id=uuid4(),
        name=f"{label} Workspace",
        slug=await _unique_slug(db, f"{label}-workspace"),
        is_personal=True,
    )
    db.add(org)
    await db.flush()
    db.add(
        OrganizationMember(
            organization_id=org.id,
            user_id=user.id,
            role=UserRole.ADMIN,
        )
    )
    await db.flush()
    return org


async def ensure_user_org(db: AsyncSession, user: User) -> Organization:
    """Return existing org or create personal workspace."""
    result = await db.execute(
        select(Organization)
        .join(OrganizationMember)
        .where(OrganizationMember.user_id == user.id)
        .order_by(Organization.created_at.asc())
        .limit(1)
    )
    org = result.scalar_one_or_none()
    if org:
        return org
    return await create_personal_org(db, user)


async def backfill_organizations(db: AsyncSession) -> int:
    """Ensure every user has an org and every project/pipeline has org_id."""
    updated = 0
    users = (await db.execute(select(User))).scalars().all()
    for user in users:
        org = await ensure_user_org(db, user)
        projects = (
            await db.execute(select(Project).where(Project.owner_id == user.id, Project.org_id.is_(None)))
        ).scalars().all()
        for project in projects:
            project.org_id = org.id
            updated += 1

    pipelines = (await db.execute(select(Pipeline).where(Pipeline.org_id.is_(None)))).scalars().all()
    for pipeline in pipelines:
        project = await db.get(Project, pipeline.project_id)
        if project and project.org_id:
            pipeline.org_id = project.org_id
            updated += 1

    return updated
