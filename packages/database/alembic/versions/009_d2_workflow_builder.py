"""D2 — custom org workflows on WorkflowDefinition.

Revision ID: 009
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return name in inspect(bind).get_table_names()


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    return column in {c["name"] for c in inspect(bind).get_columns(table)}


def upgrade() -> None:
    if not _table_exists("workflows"):
        return
    if not _column_exists("workflows", "slug"):
        op.add_column("workflows", sa.Column("slug", sa.String(80)))
    if not _column_exists("workflows", "org_id"):
        op.add_column("workflows", sa.Column("org_id", postgresql.UUID(as_uuid=True)))
        op.create_foreign_key(
            "fk_workflows_org_id",
            "workflows",
            "organizations",
            ["org_id"],
            ["id"],
            ondelete="CASCADE",
        )
    if not _column_exists("workflows", "is_builtin"):
        op.add_column("workflows", sa.Column("is_builtin", sa.Boolean(), server_default="false"))
    if not _column_exists("workflows", "created_by_user_id"):
        op.add_column("workflows", sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True)))
        op.create_foreign_key(
            "fk_workflows_created_by",
            "workflows",
            "users",
            ["created_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.execute("UPDATE workflows SET is_builtin = true WHERE org_id IS NULL")
    op.create_index("ix_workflows_org_slug", "workflows", ["org_id", "slug"], unique=True)


def downgrade() -> None:
    if not _table_exists("workflows"):
        return
    if _column_exists("workflows", "slug"):
        op.drop_index("ix_workflows_org_slug", table_name="workflows")
        op.drop_column("workflows", "slug")
    if _column_exists("workflows", "org_id"):
        op.drop_constraint("fk_workflows_org_id", "workflows", type_="foreignkey")
        op.drop_column("workflows", "org_id")
    if _column_exists("workflows", "is_builtin"):
        op.drop_column("workflows", "is_builtin")
    if _column_exists("workflows", "created_by_user_id"):
        op.drop_constraint("fk_workflows_created_by", "workflows", type_="foreignkey")
        op.drop_column("workflows", "created_by_user_id")
