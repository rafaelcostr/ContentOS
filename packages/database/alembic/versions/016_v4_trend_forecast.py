"""V4 Epic 10 — Trend forecast persistence.

Revision ID: 016
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return name in inspect(bind).get_table_names()


def upgrade() -> None:
    if _table_exists("trend_forecasts"):
        return
    op.create_table(
        "trend_forecasts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("pipeline_id", sa.UUID(), nullable=False),
        sa.Column("topic", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("niche", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("trend_score", sa.Float(), nullable=False, server_default="50"),
        sa.Column("expected_growth", sa.String(length=30), nullable=False, server_default="moderate"),
        sa.Column("production_recommendation", sa.Text(), nullable=False, server_default=""),
        sa.Column("report", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["pipeline_id"], ["pipelines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pipeline_id"),
    )
    op.create_index("ix_trend_forecasts_project_id", "trend_forecasts", ["project_id"])
    op.create_index("ix_trend_forecasts_pipeline_id", "trend_forecasts", ["pipeline_id"])
    op.create_index("ix_trend_forecasts_created_at", "trend_forecasts", ["created_at"])


def downgrade() -> None:
    if _table_exists("trend_forecasts"):
        op.drop_table("trend_forecasts")
