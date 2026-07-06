"""Stripe billing integration (V3 Tier C3)."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import UUID

from contentos_database.billing_credits import consume_credits, grant_credits, pipeline_credit_cost
from contentos_database.billing_seed import ensure_org_billing
from contentos_database.models import BillingPlan, OrganizationBilling, SubscriptionStatus
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

STRIPE_STATUS_MAP = {
    "active": SubscriptionStatus.ACTIVE,
    "trialing": SubscriptionStatus.TRIALING,
    "past_due": SubscriptionStatus.PAST_DUE,
    "canceled": SubscriptionStatus.CANCELED,
    "unpaid": SubscriptionStatus.PAST_DUE,
    "incomplete": SubscriptionStatus.NONE,
    "incomplete_expired": SubscriptionStatus.CANCELED,
}


def stripe_enabled() -> bool:
    return bool(os.getenv("STRIPE_SECRET_KEY", "").strip())


def _stripe():
    if not stripe_enabled():
        raise HTTPException(status_code=503, detail="Stripe is not configured")
    import stripe

    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    return stripe


def _success_url() -> str:
    return os.getenv("STRIPE_SUCCESS_URL", "http://localhost:3000/settings?billing=success")


def _cancel_url() -> str:
    return os.getenv("STRIPE_CANCEL_URL", "http://localhost:3000/settings?billing=cancel")


async def list_plans(db: AsyncSession) -> list[BillingPlan]:
    result = await db.execute(
        select(BillingPlan).where(BillingPlan.is_active.is_(True)).order_by(BillingPlan.monthly_credits.asc())
    )
    return list(result.scalars().all())


async def get_org_billing(db: AsyncSession, org_id: UUID) -> OrganizationBilling:
    result = await db.execute(
        select(OrganizationBilling)
        .options(selectinload(OrganizationBilling.plan))
        .where(OrganizationBilling.organization_id == org_id)
    )
    billing = result.scalar_one_or_none()
    if not billing:
        billing = await ensure_org_billing(db, org_id)
        await db.refresh(billing, attribute_names=["plan"])
    return billing


async def resolve_plan_for_price(db: AsyncSession, stripe_price_id: str) -> BillingPlan | None:
    result = await db.execute(select(BillingPlan).where(BillingPlan.stripe_price_id == stripe_price_id))
    return result.scalar_one_or_none()


async def create_checkout_session(
    db: AsyncSession,
    org_id: UUID,
    plan_slug: str,
    customer_email: str | None,
) -> dict:
    plan = await db.get(BillingPlan, plan_slug)
    if not plan or not plan.is_active:
        raise HTTPException(status_code=404, detail="Plan not found")
    if not plan.stripe_price_id:
        raise HTTPException(status_code=400, detail="Plan is not available for Stripe checkout")

    billing = await get_org_billing(db, org_id)
    stripe = _stripe()

    customer_id = billing.stripe_customer_id
    if not customer_id:
        customer = stripe.Customer.create(
            email=customer_email,
            metadata={"organization_id": str(org_id)},
        )
        customer_id = customer["id"]
        billing.stripe_customer_id = customer_id
        await db.flush()

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
        success_url=_success_url(),
        cancel_url=_cancel_url(),
        metadata={"organization_id": str(org_id), "plan_slug": plan_slug},
        subscription_data={"metadata": {"organization_id": str(org_id), "plan_slug": plan_slug}},
    )
    return {"checkout_url": session["url"], "session_id": session["id"]}


async def create_portal_session(db: AsyncSession, org_id: UUID) -> dict:
    billing = await get_org_billing(db, org_id)
    if not billing.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No Stripe customer for this organization")
    stripe = _stripe()
    session = stripe.billing_portal.Session.create(
        customer=billing.stripe_customer_id,
        return_url=_success_url(),
    )
    return {"portal_url": session["url"]}


async def apply_subscription(
    db: AsyncSession,
    org_id: UUID,
    *,
    plan_slug: str,
    stripe_customer_id: str | None,
    stripe_subscription_id: str | None,
    status: str,
) -> OrganizationBilling:
    billing = await get_org_billing(db, org_id)
    billing.plan_slug = plan_slug
    if stripe_customer_id:
        billing.stripe_customer_id = stripe_customer_id
    if stripe_subscription_id:
        billing.stripe_subscription_id = stripe_subscription_id
    billing.subscription_status = STRIPE_STATUS_MAP.get(status, SubscriptionStatus.NONE)
    billing.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return billing


async def grant_plan_credits(
    db: AsyncSession,
    org_id: UUID,
    plan_slug: str,
    *,
    reference_id: str | None = None,
) -> None:
    plan = await db.get(BillingPlan, plan_slug)
    if not plan or plan.monthly_credits <= 0:
        return
    billing = await get_org_billing(db, org_id)
    billing.credits_period_start = datetime.now(timezone.utc)
    await grant_credits(
        db,
        org_id,
        plan.monthly_credits,
        reason="subscription_grant",
        reference_id=reference_id,
    )


async def consume_pipeline_credit(db: AsyncSession, org_id: UUID, pipeline_id: UUID) -> None:
    await consume_credits(
        db,
        org_id,
        pipeline_credit_cost(),
        reason="pipeline",
        reference_id=str(pipeline_id),
    )


async def handle_stripe_webhook(db: AsyncSession, payload: bytes, signature: str | None) -> dict:
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
    if not secret:
        raise HTTPException(status_code=503, detail="Stripe webhooks not configured")

    stripe = _stripe()
    try:
        event = stripe.Webhook.construct_event(payload, signature or "", secret)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid webhook: {exc}") from exc

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        org_id = _metadata_org_id(data.get("metadata"))
        plan_slug = data.get("metadata", {}).get("plan_slug", "pro")
        sub_id = data.get("subscription")
        customer_id = data.get("customer")
        if org_id:
            await apply_subscription(
                db,
                org_id,
                plan_slug=plan_slug,
                stripe_customer_id=customer_id,
                stripe_subscription_id=sub_id,
                status="active",
            )
            await grant_plan_credits(db, org_id, plan_slug, reference_id=event["id"])

    elif event_type in ("customer.subscription.updated", "customer.subscription.created"):
        org_id = _metadata_org_id(data.get("metadata"))
        if org_id:
            price_id = _subscription_price_id(data)
            plan = await resolve_plan_for_price(db, price_id) if price_id else None
            plan_slug = plan.slug if plan else "pro"
            await apply_subscription(
                db,
                org_id,
                plan_slug=plan_slug,
                stripe_customer_id=data.get("customer"),
                stripe_subscription_id=data.get("id"),
                status=data.get("status", "active"),
            )

    elif event_type == "customer.subscription.deleted":
        org_id = _metadata_org_id(data.get("metadata"))
        if org_id:
            await apply_subscription(
                db,
                org_id,
                plan_slug="free",
                stripe_customer_id=data.get("customer"),
                stripe_subscription_id=None,
                status="canceled",
            )

    elif event_type == "invoice.paid":
        sub_id = data.get("subscription")
        customer_id = data.get("customer")
        billing = await _billing_by_stripe(db, customer_id=customer_id, subscription_id=sub_id)
        if billing and billing.subscription_status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING):
            await grant_plan_credits(db, billing.organization_id, billing.plan_slug, reference_id=event["id"])

    return {"received": True, "type": event_type}


def _metadata_org_id(metadata: dict | None) -> UUID | None:
    if not metadata:
        return None
    raw = metadata.get("organization_id")
    if not raw:
        return None
    try:
        return UUID(str(raw))
    except ValueError:
        return None


def _subscription_price_id(subscription: dict) -> str | None:
    items = subscription.get("items", {}).get("data", [])
    if not items:
        return None
    price = items[0].get("price") or {}
    return price.get("id")


async def _billing_by_stripe(
    db: AsyncSession,
    *,
    customer_id: str | None,
    subscription_id: str | None,
) -> OrganizationBilling | None:
    if subscription_id:
        result = await db.execute(
            select(OrganizationBilling).where(OrganizationBilling.stripe_subscription_id == subscription_id)
        )
        row = result.scalar_one_or_none()
        if row:
            return row
    if customer_id:
        result = await db.execute(
            select(OrganizationBilling).where(OrganizationBilling.stripe_customer_id == customer_id)
        )
        return result.scalar_one_or_none()
    return None
