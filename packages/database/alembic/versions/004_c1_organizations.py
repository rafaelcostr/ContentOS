"""C1 multi-tenant — organizations, membership, org_id on projects/pipelines.

Revision ID: 004
"""

from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return name in inspect(bind).get_table_names()


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    cols = [c["name"] for c in inspect(bind).get_columns(table)]
    return column in cols


def upgrade() -> None:
    if not _table_exists("organizations"):
        op.create_table(
            "organizations",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("slug", sa.String(80), nullable=False),
            sa.Column("is_personal", sa.Boolean(), server_default="false"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)

    if not _table_exists("organization_members"):
        op.create_table(
            "organization_members",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "organization_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("organizations.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("role", sa.Enum("admin", "editor", "viewer", name="userrole", create_type=False), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("organization_id", "user_id", name="uq_org_member"),
        )
        op.create_index("ix_organization_members_organization_id", "organization_members", ["organization_id"])
        op.create_index("ix_organization_members_user_id", "organization_members", ["user_id"])

    if not _column_exists("projects", "org_id"):
        op.add_column(
            "projects",
            sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        )
        op.create_index("ix_projects_org_id", "projects", ["org_id"])

    if not _column_exists("pipelines", "org_id"):
        op.add_column(
            "pipelines",
            sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        )
        op.create_index("ix_pipelines_org_id", "pipelines", ["org_id"])

    _backfill_orgs()


def _backfill_orgs() -> None:
    """Create personal org per user and assign existing projects/pipelines."""
    conn = op.get_bind()
    if not _table_exists("users"):
        return

    users = conn.execute(text("SELECT id, email, full_name FROM users")).fetchall()
    for row in users:
        user_id, email, full_name = row[0], row[1], row[2]
        existing = conn.execute(
            text("SELECT organization_id FROM organization_members WHERE user_id = :uid LIMIT 1"),
            {"uid": user_id},
        ).fetchone()
        if existing:
            org_id = existing[0]
        else:
            org_id = uuid4()
            label = full_name or (email.split("@")[0] if email else "user")
            slug = _unique_slug(conn, f"{label}-workspace")
            conn.execute(
                text(
                    "INSERT INTO organizations (id, name, slug, is_personal, created_at, updated_at) "
                    "VALUES (:id, :name, :slug, true, NOW(), NOW())"
                ),
                {"id": org_id, "name": f"{label} Workspace", "slug": slug},
            )
            conn.execute(
                text(
                    "INSERT INTO organization_members (id, organization_id, user_id, role, created_at) "
                    "VALUES (:id, :org_id, :uid, 'admin', NOW())"
                ),
                {"id": uuid4(), "org_id": org_id, "uid": user_id},
            )

        conn.execute(
            text("UPDATE projects SET org_id = :org_id WHERE owner_id = :uid AND org_id IS NULL"),
            {"org_id": org_id, "uid": user_id},
        )

    conn.execute(
        text(
            "UPDATE pipelines p SET org_id = pr.org_id "
            "FROM projects pr WHERE p.project_id = pr.id AND p.org_id IS NULL AND pr.org_id IS NOT NULL"
        )
    )


def _unique_slug(conn, base: str) -> str:
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")[:50] or "org"
    candidate = slug
    n = 0
    while conn.execute(text("SELECT 1 FROM organizations WHERE slug = :s"), {"s": candidate}).fetchone():
        n += 1
        candidate = f"{slug}-{n}"
    return candidate


def downgrade() -> None:
    if _column_exists("pipelines", "org_id"):
        op.drop_index("ix_pipelines_org_id", table_name="pipelines")
        op.drop_column("pipelines", "org_id")
    if _column_exists("projects", "org_id"):
        op.drop_index("ix_projects_org_id", table_name="projects")
        op.drop_column("projects", "org_id")
    if _table_exists("organization_members"):
        op.drop_table("organization_members")
    if _table_exists("organizations"):
        op.drop_table("organizations")
