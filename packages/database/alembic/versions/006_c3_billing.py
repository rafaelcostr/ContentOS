"""C3 — billing plans and organization billing.

Revision ID: 006
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return name in inspect(bind).get_table_names()


def upgrade() -> None:
    if not _table_exists("billing_plans"):
        op.create_table(
            "billing_plans",
            sa.Column("slug", sa.String(40), primary_key=True),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("monthly_credits", sa.Integer(), server_default="50"),
            sa.Column("price_usd_cents", sa.Integer()),
            sa.Column("stripe_price_id", sa.String(120)),
            sa.Column("is_active", sa.Boolean(), server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    if not _table_exists("organization_billing"):
        op.create_table(
            "organization_billing",
            sa.Column(
                "organization_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("organizations.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column(
                "plan_slug",
                sa.String(40),
                sa.ForeignKey("billing_plans.slug"),
                server_default="free",
            ),
            sa.Column("stripe_customer_id", sa.String(120)),
            sa.Column("stripe_subscription_id", sa.String(120)),
            sa.Column(
                "subscription_status",
                sa.Enum("none", "active", "trialing", "past_due", "canceled", name="subscriptionstatus"),
                server_default="none",
            ),
            sa.Column("credits_balance", sa.Integer(), server_default="0"),
            sa.Column("credits_period_start", sa.DateTime(timezone=True)),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_organization_billing_stripe_customer_id", "organization_billing", ["stripe_customer_id"])
        op.create_index(
            "ix_organization_billing_stripe_subscription_id", "organization_billing", ["stripe_subscription_id"]
        )

    if not _table_exists("credit_transactions"):
        op.create_table(
            "credit_transactions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "organization_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("organizations.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("amount", sa.Integer(), nullable=False),
            sa.Column("balance_after", sa.Integer(), nullable=False),
            sa.Column("reason", sa.String(80), nullable=False),
            sa.Column("reference_id", sa.String(120)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_credit_transactions_organization_id", "credit_transactions", ["organization_id"])


def downgrade() -> None:
    if _table_exists("credit_transactions"):
        op.drop_table("credit_transactions")
    if _table_exists("organization_billing"):
        op.drop_table("organization_billing")
    if _table_exists("billing_plans"):
        op.drop_table("billing_plans")
