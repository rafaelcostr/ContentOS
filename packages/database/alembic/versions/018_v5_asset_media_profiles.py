"""V5.0.3 — Asset media profiles (vision analysis + embeddings).

Revision ID: 018
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return name in inspect(bind).get_table_names()


def upgrade() -> None:
    if _table_exists("asset_media_profiles"):
        return
    op.create_table(
        "asset_media_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "asset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assets.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("pipeline_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pipelines.id", ondelete="SET NULL"), nullable=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("analysis", sa.JSON(), nullable=True),
        sa.Column("embedding", sa.JSON(), nullable=True),
        sa.Column("embedding_model", sa.String(120), nullable=True),
        sa.Column("vision_model", sa.String(120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_asset_media_profiles_asset_id", "asset_media_profiles", ["asset_id"])


def downgrade() -> None:
    if _table_exists("asset_media_profiles"):
        op.drop_index("ix_asset_media_profiles_asset_id", table_name="asset_media_profiles")
        op.drop_table("asset_media_profiles")
