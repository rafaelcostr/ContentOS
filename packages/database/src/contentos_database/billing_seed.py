"""Seed billing plans and bootstrap org billing rows (V3 Tier C3)."""

from __future__ import annotations

import os
from uuid import UUID

from contentos_database.models import BillingPlan, Organization, OrganizationBilling, SubscriptionStatus
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

BUILTIN_PLANS: list[dict] = [
    {
        "slug": "free",
        "name": "Free",
        "monthly_credits": 50,
        "monthly_pipeline_quota": 20,
        "max_concurrent_pipelines": 1,
        "price_usd_cents": 0,
        "stripe_price_id": None,
    },
    {
        "slug": "pro",
        "name": "Pro",
        "monthly_credits": 500,
        "monthly_pipeline_quota": 500,
        "max_concurrent_pipelines": 5,
        "price_usd_cents": 2900,
        "stripe_price_id": os.getenv("STRIPE_PRICE_PRO") or None,
    },
    {
        "slug": "enterprise",
        "name": "Enterprise",
        "monthly_credits": 5000,
        "monthly_pipeline_quota": 0,
        "max_concurrent_pipelines": 0,
        "price_usd_cents": None,
        "stripe_price_id": os.getenv("STRIPE_PRICE_ENTERPRISE") or None,
    },
]


async def ensure_billing_plans(db: AsyncSession) -> int:
    created = 0
    for row in BUILTIN_PLANS:
        existing = await db.get(BillingPlan, row["slug"])
        if existing:
            existing.name = row["name"]
            existing.monthly_credits = row["monthly_credits"]
            existing.monthly_pipeline_quota = row["monthly_pipeline_quota"]
            existing.max_concurrent_pipelines = row["max_concurrent_pipelines"]
            existing.price_usd_cents = row["price_usd_cents"]
            if row["stripe_price_id"]:
                existing.stripe_price_id = row["stripe_price_id"]
            existing.is_active = True
            continue
        db.add(BillingPlan(**row))
        created += 1
    return created


async def ensure_org_billing(db: AsyncSession, org_id: UUID, *, grant_initial: bool = True) -> OrganizationBilling:
    from contentos_database.billing_credits import grant_credits

    billing = await db.get(OrganizationBilling, org_id)
    if billing:
        return billing

    plan = await db.get(BillingPlan, "free")
    credits = plan.monthly_credits if plan else 50
    billing = OrganizationBilling(
        organization_id=org_id,
        plan_slug="free",
        subscription_status=SubscriptionStatus.NONE,
        credits_balance=0,
    )
    db.add(billing)
    await db.flush()
    if grant_initial and credits > 0:
        await grant_credits(db, org_id, credits, reason="free_grant", reference_id="bootstrap")
    return billing


async def backfill_org_billing(db: AsyncSession) -> int:
    result = await db.execute(select(Organization.id))
    org_ids = list(result.scalars().all())
    created = 0
    for org_id in org_ids:
        existing = await db.get(OrganizationBilling, org_id)
        if not existing:
            await ensure_org_billing(db, org_id)
            created += 1
    return created
