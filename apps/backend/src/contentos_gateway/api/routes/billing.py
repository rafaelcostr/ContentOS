"""Billing API routes (V3 Tier C3)."""

from datetime import datetime
from uuid import UUID

from contentos_database.models import OrganizationMember, User
from contentos_database.quota_service import get_quota_status
from contentos_database.session import get_session
from contentos_gateway.api.deps import get_current_user, require_org_admin
from contentos_gateway.services.billing_service import (
    create_checkout_session,
    create_portal_session,
    get_org_billing,
    list_plans,
    stripe_enabled,
)
from contentos_gateway.services.org_service import get_membership
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["Billing"])


class PlanResponse(BaseModel):
    slug: str
    name: str
    monthly_credits: int
    monthly_pipeline_quota: int
    max_concurrent_pipelines: int
    price_usd_cents: int | None
    stripe_available: bool


class BillingResponse(BaseModel):
    organization_id: UUID
    plan_slug: str
    plan_name: str
    monthly_credits: int
    credits_balance: int
    subscription_status: str
    stripe_enabled: bool
    has_stripe_customer: bool
    credits_period_start: datetime | None
    monthly_pipeline_quota: int
    monthly_pipelines_used: int
    max_concurrent_pipelines: int
    concurrent_pipelines_active: int


class CheckoutRequest(BaseModel):
    plan_slug: str = Field(min_length=1, max_length=40)


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


class PortalResponse(BaseModel):
    portal_url: str


@router.get("/billing/plans", response_model=list[PlanResponse])
async def get_plans(
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> list[PlanResponse]:
    plans = await list_plans(db)
    return [
        PlanResponse(
            slug=p.slug,
            name=p.name,
            monthly_credits=p.monthly_credits,
            monthly_pipeline_quota=p.monthly_pipeline_quota,
            max_concurrent_pipelines=p.max_concurrent_pipelines,
            price_usd_cents=p.price_usd_cents,
            stripe_available=bool(p.stripe_price_id and stripe_enabled()),
        )
        for p in plans
    ]


@router.get("/organizations/{org_id}/billing", response_model=BillingResponse)
async def get_billing(
    org_id: UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> BillingResponse:
    if not await get_membership(db, user.id, org_id):
        raise HTTPException(status_code=404, detail="Organization not found")
    billing = await get_org_billing(db, org_id)
    plan = billing.plan
    quotas = await get_quota_status(db, org_id)
    return BillingResponse(
        organization_id=billing.organization_id,
        plan_slug=billing.plan_slug,
        plan_name=plan.name if plan else billing.plan_slug,
        monthly_credits=plan.monthly_credits if plan else 0,
        credits_balance=billing.credits_balance,
        subscription_status=billing.subscription_status.value,
        stripe_enabled=stripe_enabled(),
        has_stripe_customer=bool(billing.stripe_customer_id),
        credits_period_start=billing.credits_period_start,
        monthly_pipeline_quota=quotas.monthly_pipeline_quota,
        monthly_pipelines_used=quotas.monthly_pipelines_used,
        max_concurrent_pipelines=quotas.max_concurrent_pipelines,
        concurrent_pipelines_active=quotas.concurrent_pipelines_active,
    )


@router.post("/organizations/{org_id}/billing/checkout", response_model=CheckoutResponse)
async def start_checkout(
    org_id: UUID,
    body: CheckoutRequest,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_org_admin),
) -> CheckoutResponse:
    data = await create_checkout_session(db, org_id, body.plan_slug, user.email)
    return CheckoutResponse(**data)


@router.post("/organizations/{org_id}/billing/portal", response_model=PortalResponse)
async def billing_portal(
    org_id: UUID,
    db: AsyncSession = Depends(get_session),
    _admin: OrganizationMember = Depends(require_org_admin),
) -> PortalResponse:
    data = await create_portal_session(db, org_id)
    return PortalResponse(**data)


@router.post("/billing/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_session),
    stripe_signature: str | None = Header(None, alias="Stripe-Signature"),
) -> dict:
    from contentos_gateway.services.billing_service import handle_stripe_webhook

    payload = await request.body()
    return await handle_stripe_webhook(db, payload, stripe_signature)
