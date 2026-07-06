"""V4 Epic 2a — Multi content text artifacts table.

Revision ID: 013
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return name in inspect(bind).get_table_names()


def upgrade() -> None:
    if _table_exists("multi_content_artifacts"):
        return
    op.create_table(
        "multi_content_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pipeline_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("format", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False, server_default=""),
        sa.Column("content_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("source", sa.String(30), nullable=False, server_default="heuristic"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_multi_content_artifacts_project_id", "multi_content_artifacts", ["project_id"])
    op.create_index("ix_multi_content_artifacts_pipeline_id", "multi_content_artifacts", ["pipeline_id"])
    op.create_index("ix_multi_content_artifacts_format", "multi_content_artifacts", ["format"])
    op.create_index("ix_multi_content_artifacts_created_at", "multi_content_artifacts", ["created_at"])


def downgrade() -> None:
    if _table_exists("multi_content_artifacts"):
        op.drop_table("multi_content_artifacts")
