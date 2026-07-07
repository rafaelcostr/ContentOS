"""Organization quota checks by billing plan (V3 Tier C4)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from contentos_database.models import BillingPlan, OrganizationBilling, Pipeline, PipelineStatus
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class QuotaExceededError(Exception):
    def __init__(self, kind: str, limit: int, current: int) -> None:
        self.kind = kind
        self.limit = limit
        self.current = current
        super().__init__(f"Quota exceeded ({kind}): {current}/{limit}")


@dataclass
class QuotaStatus:
    plan_slug: str
    monthly_pipeline_quota: int
    monthly_pipelines_used: int
    max_concurrent_pipelines: int
    concurrent_pipelines_active: int


def quotas_enforced() -> bool:
    return os.getenv("QUOTAS_ENFORCE", "true").lower() in ("1", "true", "yes")


def is_unlimited(limit: int) -> bool:
    return limit <= 0


def month_start_utc() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def count_pipelines_this_month(db: AsyncSession, org_id: UUID) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(Pipeline)
        .where(Pipeline.org_id == org_id, Pipeline.created_at >= month_start_utc())
    )
    return int(result.scalar_one())


async def count_active_pipelines(db: AsyncSession, org_id: UUID) -> int:
    active = (PipelineStatus.PENDING, PipelineStatus.RUNNING)
    result = await db.execute(
        select(func.count())
        .select_from(Pipeline)
        .where(Pipeline.org_id == org_id, Pipeline.status.in_(active))
    )
    return int(result.scalar_one())


async def get_org_plan(db: AsyncSession, org_id: UUID) -> BillingPlan:
    result = await db.execute(
        select(OrganizationBilling)
        .options(selectinload(OrganizationBilling.plan))
        .where(OrganizationBilling.organization_id == org_id)
    )
    billing = result.scalar_one_or_none()
    if billing and billing.plan:
        return billing.plan
    plan = await db.get(BillingPlan, billing.plan_slug if billing else "free")
    if plan:
        return plan
    return BillingPlan(
        slug="free",
        name="Free",
        monthly_credits=50,
        monthly_pipeline_quota=20,
        max_concurrent_pipelines=1,
    )


async def get_quota_status(db: AsyncSession, org_id: UUID) -> QuotaStatus:
    plan = await get_org_plan(db, org_id)
    used = await count_pipelines_this_month(db, org_id)
    active = await count_active_pipelines(db, org_id)
    return QuotaStatus(
        plan_slug=plan.slug,
        monthly_pipeline_quota=plan.monthly_pipeline_quota,
        monthly_pipelines_used=used,
        max_concurrent_pipelines=plan.max_concurrent_pipelines,
        concurrent_pipelines_active=active,
    )


async def assert_can_start_pipeline(db: AsyncSession, org_id: UUID) -> None:
    await assert_can_start_batch(db, org_id, 1)


async def assert_can_start_batch(db: AsyncSession, org_id: UUID, count: int) -> None:
    """Validate monthly and concurrent quotas for N pipelines (V5.3.3)."""
    if not quotas_enforced():
        return
    quantity = max(1, int(count))
    plan = await get_org_plan(db, org_id)
    monthly_used = await count_pipelines_this_month(db, org_id)
    if not is_unlimited(plan.monthly_pipeline_quota) and monthly_used + quantity > plan.monthly_pipeline_quota:
        raise QuotaExceededError("monthly_pipelines", plan.monthly_pipeline_quota, monthly_used)

    active = await count_active_pipelines(db, org_id)
    if not is_unlimited(plan.max_concurrent_pipelines) and active + quantity > plan.max_concurrent_pipelines:
        raise QuotaExceededError("concurrent_pipelines", plan.max_concurrent_pipelines, active)
