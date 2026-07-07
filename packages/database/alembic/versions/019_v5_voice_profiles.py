"""V5.1.1 — Voice profiles (speed, pitch, pause).

Revision ID: 019
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return name in inspect(bind).get_table_names()


def upgrade() -> None:
    if _table_exists("voice_profiles"):
        return
    op.create_table(
        "voice_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False, server_default="piper"),
        sa.Column("voice_id", sa.String(120), nullable=True),
        sa.Column("speed", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("pitch_semitones", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("pause_ms", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_voice_profiles_project_id", "voice_profiles", ["project_id"])
    op.create_index("ix_voice_profiles_slug", "voice_profiles", ["slug"])


def downgrade() -> None:
    if _table_exists("voice_profiles"):
        op.drop_index("ix_voice_profiles_slug", table_name="voice_profiles")
        op.drop_index("ix_voice_profiles_project_id", table_name="voice_profiles")
        op.drop_table("voice_profiles")
