"""D1 — pipeline schedules.

Revision ID: 008
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return name in inspect(bind).get_table_names()


def upgrade() -> None:
    if _table_exists("pipeline_schedules"):
        return
    op.create_table(
        "pipeline_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("topic", sa.String(500), nullable=False),
        sa.Column("workflow_name", sa.String(80)),
        sa.Column("cron_expression", sa.String(120), nullable=False),
        sa.Column("timezone", sa.String(64), server_default="UTC"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("next_run_at", sa.DateTime(timezone=True)),
        sa.Column("last_pipeline_id", postgresql.UUID(as_uuid=True)),
        sa.Column("last_error", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_pipeline_schedules_project_id", "pipeline_schedules", ["project_id"])
    op.create_index("ix_pipeline_schedules_next_run_at", "pipeline_schedules", ["next_run_at"])


def downgrade() -> None:
    if _table_exists("pipeline_schedules"):
        op.drop_table("pipeline_schedules")
