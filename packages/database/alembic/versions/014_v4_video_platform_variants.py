"""V4 Epic 2b — Video platform variants + Video.platform_variants column.

Revision ID: 014
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return name in inspect(bind).get_table_names()


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    return column in {c["name"] for c in inspect(bind).get_columns(table)}


def upgrade() -> None:
    if not _column_exists("videos", "platform_variants"):
        op.add_column("videos", sa.Column("platform_variants", sa.JSON(), nullable=True))

    if _table_exists("video_platform_variants"):
        return
    op.create_table(
        "video_platform_variants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pipeline_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("hashtags", sa.JSON(), nullable=True),
        sa.Column("crop_spec", sa.JSON(), nullable=True),
        sa.Column("render_ref", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("source", sa.String(30), nullable=False, server_default="heuristic"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_video_platform_variants_project_id", "video_platform_variants", ["project_id"])
    op.create_index("ix_video_platform_variants_pipeline_id", "video_platform_variants", ["pipeline_id"])
    op.create_index("ix_video_platform_variants_platform", "video_platform_variants", ["platform"])
    op.create_index("ix_video_platform_variants_created_at", "video_platform_variants", ["created_at"])


def downgrade() -> None:
    if _table_exists("video_platform_variants"):
        op.drop_table("video_platform_variants")
    if _column_exists("videos", "platform_variants"):
        op.drop_column("videos", "platform_variants")
