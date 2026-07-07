"""Platform publication audit table — phase 6.

Revision ID: 022
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "022"
down_revision: Union[str, None] = "021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return name in inspect(bind).get_table_names()


def upgrade() -> None:
    if _table_exists("platform_publications"):
        return
    op.create_table(
        "platform_publications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pipeline_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pipelines.id", ondelete="SET NULL"), nullable=True),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("publish_mode", sa.String(30), nullable=False, server_default="dry_run"),
        sa.Column("status", sa.String(40), nullable=False, server_default="ready"),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("external_id", sa.String(200), nullable=True),
        sa.Column("publish_url", sa.String(1000), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_platform_publications_project_id", "platform_publications", ["project_id"])
    op.create_index("ix_platform_publications_pipeline_id", "platform_publications", ["pipeline_id"])
    op.create_index("ix_platform_publications_platform", "platform_publications", ["platform"])
    op.create_index("ix_platform_publications_publish_mode", "platform_publications", ["publish_mode"])
    op.create_index("ix_platform_publications_status", "platform_publications", ["status"])
    op.create_index("ix_platform_publications_external_id", "platform_publications", ["external_id"])
    op.create_index("ix_platform_publications_created_at", "platform_publications", ["created_at"])


def downgrade() -> None:
    if _table_exists("platform_publications"):
        op.drop_table("platform_publications")
