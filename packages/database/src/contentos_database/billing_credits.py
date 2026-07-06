"""Credit ledger operations (V3 Tier C3)."""

from __future__ import annotations

import os
from uuid import UUID

from contentos_database.models import CreditTransaction, OrganizationBilling
from sqlalchemy.ext.asyncio import AsyncSession


def pipeline_credit_cost() -> int:
    try:
        return max(1, int(os.getenv("BILLING_PIPELINE_CREDIT_COST", "1")))
    except ValueError:
        return 1


def billing_enforced() -> bool:
    return os.getenv("BILLING_ENFORCE_CREDITS", "true").lower() in ("1", "true", "yes")


class InsufficientCreditsError(Exception):
    def __init__(self, balance: int, required: int) -> None:
        self.balance = balance
        self.required = required
        super().__init__(f"Insufficient credits: have {balance}, need {required}")


async def grant_credits(
    db: AsyncSession,
    org_id: UUID,
    amount: int,
    *,
    reason: str,
    reference_id: str | None = None,
) -> CreditTransaction:
    if amount <= 0:
        raise ValueError("grant amount must be positive")
    billing = await db.get(OrganizationBilling, org_id)
    if not billing:
        raise ValueError(f"No billing row for org {org_id}")
    billing.credits_balance += amount
    tx = CreditTransaction(
        organization_id=org_id,
        amount=amount,
        balance_after=billing.credits_balance,
        reason=reason,
        reference_id=reference_id,
    )
    db.add(tx)
    await db.flush()
    return tx


async def consume_credits(
    db: AsyncSession,
    org_id: UUID,
    amount: int,
    *,
    reason: str,
    reference_id: str | None = None,
) -> CreditTransaction:
    if amount <= 0:
        raise ValueError("consume amount must be positive")
    billing = await db.get(OrganizationBilling, org_id)
    if not billing:
        raise InsufficientCreditsError(0, amount)
    if billing.credits_balance < amount:
        raise InsufficientCreditsError(billing.credits_balance, amount)
    billing.credits_balance -= amount
    tx = CreditTransaction(
        organization_id=org_id,
        amount=-amount,
        balance_after=billing.credits_balance,
        reason=reason,
        reference_id=reference_id,
    )
    db.add(tx)
    await db.flush()
    return tx
