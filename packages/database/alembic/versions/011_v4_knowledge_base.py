"""V4 Epic 3 — Knowledge Base entries table.

Revision ID: 011
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return name in inspect(bind).get_table_names()


def upgrade() -> None:
    if _table_exists("knowledge_entries"):
        return
    op.create_table(
        "knowledge_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("pipeline_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pipelines.id", ondelete="SET NULL"), nullable=True),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(500), nullable=False, server_default=""),
        sa.Column("content_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("snippet", sa.String(1000), nullable=False, server_default=""),
        sa.Column("embedding", sa.JSON(), nullable=True),
        sa.Column("embedding_model", sa.String(120), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "parent_entry_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_entries.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_knowledge_entries_project_id", "knowledge_entries", ["project_id"])
    op.create_index("ix_knowledge_entries_resource_type", "knowledge_entries", ["resource_type"])
    op.create_index("ix_knowledge_entries_resource_id", "knowledge_entries", ["resource_id"])
    op.create_index("ix_knowledge_entries_pipeline_id", "knowledge_entries", ["pipeline_id"])
    op.create_index("ix_knowledge_entries_created_at", "knowledge_entries", ["created_at"])


def downgrade() -> None:
    if _table_exists("knowledge_entries"):
        op.drop_table("knowledge_entries")
