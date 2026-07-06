"""V4 Epic 6 — A/B variant persistence table.

Revision ID: 012
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return name in inspect(bind).get_table_names()


def upgrade() -> None:
    if _table_exists("ab_variants"):
        return
    op.create_table(
        "ab_variants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pipeline_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dimension", sa.String(50), nullable=False),
        sa.Column("variants", sa.JSON(), nullable=False),
        sa.Column("winner_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("winner", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_ab_variants_project_id", "ab_variants", ["project_id"])
    op.create_index("ix_ab_variants_pipeline_id", "ab_variants", ["pipeline_id"])
    op.create_index("ix_ab_variants_dimension", "ab_variants", ["dimension"])
    op.create_index("ix_ab_variants_created_at", "ab_variants", ["created_at"])


def downgrade() -> None:
    if _table_exists("ab_variants"):
        op.drop_table("ab_variants")
