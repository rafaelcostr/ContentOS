"""C4 — plan quotas on billing_plans.

Revision ID: 007
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return name in inspect(bind).get_table_names()


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    return column in {c["name"] for c in inspect(bind).get_columns(table)}


def upgrade() -> None:
    if _table_exists("billing_plans"):
        if not _column_exists("billing_plans", "monthly_pipeline_quota"):
            op.add_column(
                "billing_plans",
                sa.Column("monthly_pipeline_quota", sa.Integer(), server_default="20", nullable=False),
            )
        if not _column_exists("billing_plans", "max_concurrent_pipelines"):
            op.add_column(
                "billing_plans",
                sa.Column("max_concurrent_pipelines", sa.Integer(), server_default="1", nullable=False),
            )
        op.execute(
            "UPDATE billing_plans SET monthly_pipeline_quota = 20, max_concurrent_pipelines = 1 WHERE slug = 'free'"
        )
        op.execute(
            "UPDATE billing_plans SET monthly_pipeline_quota = 500, max_concurrent_pipelines = 5 WHERE slug = 'pro'"
        )
        op.execute(
            "UPDATE billing_plans SET monthly_pipeline_quota = 0, max_concurrent_pipelines = 0 WHERE slug = 'enterprise'"
        )


def downgrade() -> None:
    if _table_exists("billing_plans"):
        if _column_exists("billing_plans", "max_concurrent_pipelines"):
            op.drop_column("billing_plans", "max_concurrent_pipelines")
        if _column_exists("billing_plans", "monthly_pipeline_quota"):
            op.drop_column("billing_plans", "monthly_pipeline_quota")
