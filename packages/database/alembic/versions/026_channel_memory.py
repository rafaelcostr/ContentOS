"""Channel memory table — Growth OS Fase 6.

Revision ID: 026
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "026"
down_revision: Union[str, None] = "025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table: str) -> bool:
    return table in inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if not _table_exists("channel_memory"):
        op.create_table(
            "channel_memory",
            sa.Column("channel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("channels.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("winning_videos", postgresql.JSON(), nullable=True),
            sa.Column("losing_videos", postgresql.JSON(), nullable=True),
            sa.Column("top_hooks", postgresql.JSON(), nullable=True),
            sa.Column("top_ctas", postgresql.JSON(), nullable=True),
            sa.Column("top_themes", postgresql.JSON(), nullable=True),
            sa.Column("top_hashtags", postgresql.JSON(), nullable=True),
            sa.Column("best_posting_hours", postgresql.JSON(), nullable=True),
            sa.Column("insights", postgresql.JSON(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_channel_memory_project_id", "channel_memory", ["project_id"])


def downgrade() -> None:
    if _table_exists("channel_memory"):
        op.drop_index("ix_channel_memory_project_id", table_name="channel_memory")
        op.drop_table("channel_memory")
