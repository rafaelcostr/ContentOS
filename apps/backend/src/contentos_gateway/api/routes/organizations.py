"""Organization API routes (V3 Tier C1)."""

from uuid import UUID

from contentos_database.models import Organization, OrganizationMember, User, UserRole
from contentos_database.org_seed import slugify
from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user, require_org_admin
from contentos_gateway.services.org_service import get_membership, list_user_organizations
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/organizations", tags=["Organizations"])


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    is_personal: bool
    role: UserRole


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class MemberAddRequest(BaseModel):
    user_id: UUID
    role: UserRole = UserRole.VIEWER


class MemberResponse(BaseModel):
    id: UUID
    user_id: UUID
    organization_id: UUID
    role: UserRole


@router.get("", response_model=list[OrganizationResponse])
async def list_organizations(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[OrganizationResponse]:
    orgs = await list_user_organizations(db, user.id)
    out: list[OrganizationResponse] = []
    for org in orgs:
        member = await get_membership(db, user.id, org.id)
        out.append(
            OrganizationResponse(
                id=org.id,
                name=org.name,
                slug=org.slug,
                is_personal=org.is_personal,
                role=member.role if member else user.role,
            )
        )
    return out


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    body: OrganizationCreate,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> OrganizationResponse:
    from contentos_database.org_seed import _unique_slug

    org = Organization(
        name=body.name.strip(),
        slug=await _unique_slug(db, slugify(body.name)),
        is_personal=False,
    )
    db.add(org)
    await db.flush()
    member = OrganizationMember(organization_id=org.id, user_id=user.id, role=UserRole.ADMIN)
    db.add(member)
    await db.flush()
    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        is_personal=org.is_personal,
        role=UserRole.ADMIN,
    )


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> OrganizationResponse:
    member = await get_membership(db, user.id, org_id)
    if not member:
        raise HTTPException(status_code=404, detail="Organization not found")
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        is_personal=org.is_personal,
        role=member.role,
    )


@router.get("/{org_id}/members", response_model=list[MemberResponse])
async def list_members(
    org_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[MemberResponse]:
    member = await get_membership(db, user.id, org_id)
    if not member:
        raise HTTPException(status_code=404, detail="Organization not found")
    result = await db.execute(select(OrganizationMember).where(OrganizationMember.organization_id == org_id))
    return [
        MemberResponse(
            id=m.id,
            user_id=m.user_id,
            organization_id=m.organization_id,
            role=m.role,
        )
        for m in result.scalars().all()
    ]


@router.post("/{org_id}/members", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
async def add_member(
    org_id: UUID,
    body: MemberAddRequest,
    db: AsyncSession = Depends(get_session),
    _admin: OrganizationMember = Depends(require_org_admin),
) -> MemberResponse:
    existing = await get_membership(db, body.user_id, org_id)
    if existing:
        raise HTTPException(status_code=400, detail="User is already a member")

    row = OrganizationMember(organization_id=org_id, user_id=body.user_id, role=body.role)
    db.add(row)
    await db.flush()
    return MemberResponse(
        id=row.id,
        user_id=row.user_id,
        organization_id=row.organization_id,
        role=row.role,
    )
