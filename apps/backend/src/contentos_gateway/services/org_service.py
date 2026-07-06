"""Organization access helpers (V3 Tier C1)."""

from __future__ import annotations

from uuid import UUID

from contentos_database.models import Organization, OrganizationMember, Pipeline, Project, User, UserRole
from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

ORG_HEADER = "X-Organization-Id"

ROLE_RANK: dict[str, int] = {
    UserRole.VIEWER.value: 1,
    UserRole.EDITOR.value: 2,
    UserRole.ADMIN.value: 3,
}


async def get_membership(
    db: AsyncSession, user_id: UUID, org_id: UUID
) -> OrganizationMember | None:
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.user_id == user_id,
            OrganizationMember.organization_id == org_id,
        )
    )
    return result.scalar_one_or_none()


async def list_user_organizations(db: AsyncSession, user_id: UUID) -> list[Organization]:
    result = await db.execute(
        select(Organization)
        .join(OrganizationMember)
        .where(OrganizationMember.user_id == user_id)
        .order_by(Organization.is_personal.desc(), Organization.created_at.asc())
    )
    return list(result.scalars().all())


async def resolve_org_id(db: AsyncSession, user: User, org_id_raw: str | None) -> UUID:
    if org_id_raw:
        try:
            org_id = UUID(org_id_raw)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid organization id") from exc
        if not await get_membership(db, user.id, org_id):
            raise HTTPException(status_code=403, detail="Not a member of this organization")
        return org_id

    orgs = await list_user_organizations(db, user.id)
    if not orgs:
        raise HTTPException(status_code=403, detail="No organization available")
    return orgs[0].id


def effective_role(user: User, member: OrganizationMember | None) -> str:
    """Membership role wins when present (C2)."""
    if member:
        return member.role.value
    return user.role.value


def member_has_min_role(member: OrganizationMember | None, user: User, min_role: str) -> bool:
    role = effective_role(user, member)
    return ROLE_RANK.get(role, 0) >= ROLE_RANK.get(min_role, 99)


def project_access_clause(user_id: UUID):
    """SQL filter: user can access project via org membership or legacy ownership."""
    member_orgs = (
        select(OrganizationMember.organization_id)
        .where(OrganizationMember.user_id == user_id)
        .scalar_subquery()
    )
    return or_(Project.org_id.in_(member_orgs), Project.owner_id == user_id)


async def get_accessible_project(
    db: AsyncSession, project_id: UUID, user_id: UUID
) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, project_access_clause(user_id))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def get_accessible_pipeline(
    db: AsyncSession, pipeline_id: UUID, user_id: UUID
) -> Pipeline:
    result = await db.execute(
        select(Pipeline)
        .join(Project)
        .where(Pipeline.id == pipeline_id, project_access_clause(user_id))
    )
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return pipeline


async def require_org_editor(
    db: AsyncSession, user: User, org_id: UUID
) -> OrganizationMember:
    member = await get_membership(db, user.id, org_id)
    if not member_has_min_role(member, user, UserRole.EDITOR.value):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Editor role required")
    return member
