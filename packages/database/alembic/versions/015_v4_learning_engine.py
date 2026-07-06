"""V4 Epic 7 — Learning Engine insights table.

Revision ID: 015
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return name in inspect(bind).get_table_names()


def upgrade() -> None:
    if _table_exists("learning_insights"):
        return
    op.create_table(
        "learning_insights",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("pipeline_id", sa.UUID(), nullable=False),
        sa.Column("topic", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("content_score", sa.Float(), nullable=True),
        sa.Column("viral_score", sa.Float(), nullable=True),
        sa.Column("specialist_id", sa.String(length=100), nullable=True),
        sa.Column("hook_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("cta_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("signals", sa.JSON(), nullable=True),
        sa.Column("memory_applied", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("memory_updates", sa.JSON(), nullable=True),
        sa.Column("kb_indexed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["pipeline_id"], ["pipelines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pipeline_id"),
    )
    op.create_index("ix_learning_insights_project_id", "learning_insights", ["project_id"])
    op.create_index("ix_learning_insights_pipeline_id", "learning_insights", ["pipeline_id"])
    op.create_index("ix_learning_insights_created_at", "learning_insights", ["created_at"])


def downgrade() -> None:
    if _table_exists("learning_insights"):
        op.drop_table("learning_insights")
