"""Organization API key management (V3 Tier C5)."""

from datetime import datetime, timezone
from uuid import UUID

from contentos_database.models import ApiKeyScope, OrganizationApiKey, OrganizationMember
from contentos_database.session import get_session
from contentos_gateway.api.deps import require_org_admin
from contentos_gateway.services.api_key_service import default_rate_limit, generate_api_key_material
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/organizations/{org_id}/api-keys", tags=["API Keys"])


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    scope: ApiKeyScope = ApiKeyScope.READ
    rate_limit_per_minute: int | None = Field(default=None, ge=1, le=10_000)


class ApiKeyResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    key_prefix: str
    scope: ApiKeyScope
    rate_limit_per_minute: int
    is_active: bool
    last_used_at: datetime | None
    created_at: datetime


class ApiKeyCreatedResponse(ApiKeyResponse):
    api_key: str


@router.get("", response_model=list[ApiKeyResponse])
async def list_api_keys(
    org_id: UUID,
    db: AsyncSession = Depends(get_session),
    _admin: OrganizationMember = Depends(require_org_admin),
) -> list[ApiKeyResponse]:
    result = await db.execute(
        select(OrganizationApiKey)
        .where(
            OrganizationApiKey.organization_id == org_id,
            OrganizationApiKey.is_active.is_(True),
        )
        .order_by(OrganizationApiKey.created_at.desc())
    )
    return [
        ApiKeyResponse(
            id=row.id,
            organization_id=row.organization_id,
            name=row.name,
            key_prefix=row.key_prefix,
            scope=row.scope,
            rate_limit_per_minute=row.rate_limit_per_minute,
            is_active=row.is_active,
            last_used_at=row.last_used_at,
            created_at=row.created_at,
        )
        for row in result.scalars().all()
    ]


@router.post("", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    org_id: UUID,
    body: ApiKeyCreate,
    db: AsyncSession = Depends(get_session),
    admin: OrganizationMember = Depends(require_org_admin),
) -> ApiKeyCreatedResponse:
    raw_key, prefix, key_hash = generate_api_key_material()
    row = OrganizationApiKey(
        organization_id=org_id,
        name=body.name.strip(),
        key_prefix=prefix,
        key_hash=key_hash,
        scope=body.scope,
        rate_limit_per_minute=body.rate_limit_per_minute or default_rate_limit(),
        created_by_user_id=admin.user_id,
    )
    db.add(row)
    await db.flush()
    return ApiKeyCreatedResponse(
        id=row.id,
        organization_id=row.organization_id,
        name=row.name,
        key_prefix=row.key_prefix,
        scope=row.scope,
        rate_limit_per_minute=row.rate_limit_per_minute,
        is_active=row.is_active,
        last_used_at=row.last_used_at,
        created_at=row.created_at,
        api_key=raw_key,
    )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    org_id: UUID,
    key_id: UUID,
    db: AsyncSession = Depends(get_session),
    _admin: OrganizationMember = Depends(require_org_admin),
) -> None:
    row = await db.get(OrganizationApiKey, key_id)
    if not row or row.organization_id != org_id or not row.is_active:
        raise HTTPException(status_code=404, detail="API key not found")
    row.is_active = False
    row.revoked_at = datetime.now(timezone.utc)
    await db.flush()
