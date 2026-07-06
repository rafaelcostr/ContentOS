"""Unified marketplace API (V3 Tier D3)."""

from uuid import UUID

from contentos_database.models import User, WorkflowDefinition
from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user
from contentos_gateway.services.org_service import ORG_HEADER, resolve_org_id
from contentos_shared.unified_marketplace import build_unified_catalog, catalog_summary
from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/marketplace", tags=["Marketplace"])


class MarketplaceItemResponse(BaseModel):
    id: str
    type: str
    name: str
    description: str
    version: str
    author: str
    category: str
    source: str
    installed: bool | None = None
    enabled: bool | None = None
    platform: str | None = None
    hooks: list[str] | None = None
    builtin: bool | None = None
    queue: str | None = None
    tier: str | None = None
    steps: list[str] | None = None
    step_count: int | None = None
    slug: str | None = None
    org_id: str | None = None
    is_default: bool | None = None
    metadata: dict | None = None


class MarketplaceCatalogResponse(BaseModel):
    summary: dict[str, int]
    items: list[MarketplaceItemResponse]
    remote_configured: bool


@router.get("", response_model=MarketplaceCatalogResponse)
async def unified_catalog(
    type: str | None = Query(None, alias="type", description="Filter: plugin, agent, workflow"),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
    x_organization_id: str | None = Header(None, alias=ORG_HEADER),
) -> MarketplaceCatalogResponse:
    from contentos_shared.unified_marketplace import marketplace_remote_url

    org_id = await resolve_org_id(db, user, x_organization_id)
    custom_rows = await _org_custom_workflows(db, org_id)
    items = build_unified_catalog(custom_workflows=custom_rows, item_type=type)
    return MarketplaceCatalogResponse(
        summary=catalog_summary(items),
        items=[MarketplaceItemResponse(**item) for item in items],
        remote_configured=bool(marketplace_remote_url()),
    )


async def _org_custom_workflows(db: AsyncSession, org_id: UUID) -> list[dict]:
    result = await db.execute(
        select(WorkflowDefinition).where(
            WorkflowDefinition.org_id == org_id,
            WorkflowDefinition.is_builtin.is_(False),
        )
    )
    return [
        {
            "name": w.name,
            "slug": w.slug,
            "org_id": w.org_id,
            "description": w.description,
            "steps": list(w.steps),
        }
        for w in result.scalars().all()
    ]
