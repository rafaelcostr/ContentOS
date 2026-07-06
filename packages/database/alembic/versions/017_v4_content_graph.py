"""V4 Epic 11 — Content relation graph.

Revision ID: 017
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return name in inspect(bind).get_table_names()


def upgrade() -> None:
    if _table_exists("content_relations"):
        return
    op.create_table(
        "content_relations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("pipeline_id", sa.UUID(), nullable=True),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.String(length=120), nullable=False),
        sa.Column("relation_type", sa.String(length=50), nullable=False),
        sa.Column("label_source", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("label_target", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["pipeline_id"], ["pipelines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_content_relations_project_id", "content_relations", ["project_id"])
    op.create_index("ix_content_relations_pipeline_id", "content_relations", ["pipeline_id"])
    op.create_index("ix_content_relations_source", "content_relations", ["source_type", "source_id"])
    op.create_index("ix_content_relations_target", "content_relations", ["target_type", "target_id"])
    op.create_index("ix_content_relations_relation_type", "content_relations", ["relation_type"])
    op.create_index("ix_content_relations_created_at", "content_relations", ["created_at"])
    op.create_index(
        "uq_content_relations_edge",
        "content_relations",
        ["project_id", "source_type", "source_id", "target_type", "target_id", "relation_type"],
        unique=True,
    )


def downgrade() -> None:
    if _table_exists("content_relations"):
        op.drop_table("content_relations")
