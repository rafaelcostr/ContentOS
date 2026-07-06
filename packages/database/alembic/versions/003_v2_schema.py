"""V2 schema — additive migration for existing PostgreSQL deployments.

Revision ID: 003
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
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
    if not _column_exists("pipelines", "workflow_name"):
        op.add_column("pipelines", sa.Column("workflow_name", sa.String(80), nullable=True))
        op.create_index("ix_pipelines_workflow_name", "pipelines", ["workflow_name"])

    for col, col_type in (
        ("sha256", sa.String(64)),
        ("tags", postgresql.JSON()),
        ("version", sa.Integer()),
        ("parent_asset_id", postgresql.UUID(as_uuid=True)),
    ):
        if not _column_exists("assets", col):
            if col == "version":
                op.add_column("assets", sa.Column(col, col_type, server_default="1"))
            else:
                op.add_column("assets", sa.Column(col, col_type, nullable=True))

    if _column_exists("assets", "sha256"):
        try:
            op.create_index("ix_assets_sha256", "assets", ["sha256"], unique=False)
        except Exception:
            pass

    if not _table_exists("agent_model_configs"):
        op.create_table(
            "agent_model_configs",
            sa.Column("agent", sa.String(50), primary_key=True),
            sa.Column("provider_type", sa.String(20), nullable=False),
            sa.Column("provider", sa.String(50), nullable=False),
            sa.Column("model", sa.String(120), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )

    if not _table_exists("project_memory"):
        op.create_table(
            "project_memory",
            sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("tone", sa.String(255)),
            sa.Column("vocabulary", postgresql.JSON()),
            sa.Column("cta", sa.String(500)),
            sa.Column("avg_duration", sa.Float()),
            sa.Column("hook_style", sa.String(255)),
            sa.Column("niche", sa.String(255)),
            sa.Column("goal", sa.String(500)),
            sa.Column("style", postgresql.JSON()),
            sa.Column("history", postgresql.JSON()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )

    if not _table_exists("cost_entries"):
        op.create_table(
            "cost_entries",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("pipeline_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pipelines.id", ondelete="SET NULL")),
            sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="SET NULL")),
            sa.Column("agent", sa.String(50), nullable=False),
            sa.Column("provider", sa.String(50), nullable=False),
            sa.Column("model", sa.String(120), nullable=False),
            sa.Column("operation", sa.String(50), server_default="text_chat"),
            sa.Column("tokens_input", sa.Integer(), server_default="0"),
            sa.Column("tokens_output", sa.Integer(), server_default="0"),
            sa.Column("duration_ms", sa.Integer(), server_default="0"),
            sa.Column("estimated_cost_usd", sa.Float(), server_default="0"),
            sa.Column("from_cache", sa.Boolean(), server_default="false"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    if not _table_exists("domain_events"):
        op.create_table(
            "domain_events",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("event_type", sa.String(80), nullable=False),
            sa.Column("pipeline_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pipelines.id", ondelete="SET NULL")),
            sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="SET NULL")),
            sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="SET NULL")),
            sa.Column("agent", sa.String(50)),
            sa.Column("step", sa.String(50)),
            sa.Column("status", sa.String(30)),
            sa.Column("payload", postgresql.JSON()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    if not _table_exists("analytics_insights"):
        op.create_table(
            "analytics_insights",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("pipeline_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False),
            sa.Column("video_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("videos.id", ondelete="SET NULL")),
            sa.Column("metrics", postgresql.JSON()),
            sa.Column("analysis", postgresql.JSON()),
            sa.Column("models_used", postgresql.JSON()),
            sa.Column("prompts_used", postgresql.JSON()),
            sa.Column("applied_to_memory", sa.Boolean(), server_default="false"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    if not _table_exists("installed_plugins"):
        op.create_table(
            "installed_plugins",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(80), nullable=False, unique=True),
            sa.Column("version", sa.String(30), server_default="1.0.0"),
            sa.Column("enabled", sa.Boolean(), server_default="false"),
            sa.Column("source", sa.String(30), server_default="marketplace"),
            sa.Column("manifest", postgresql.JSON()),
            sa.Column("installed_at", sa.DateTime(timezone=True), nullable=False),
        )

    if not _table_exists("pipeline_asset_collections"):
        op.create_table(
            "pipeline_asset_collections",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("pipeline_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("candidates", postgresql.JSON()),
            sa.Column("assets", postgresql.JSON()),
            sa.Column("status", sa.String(30), server_default="pending"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )

    if not _table_exists("workflows"):
        op.create_table(
            "workflows",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(255), nullable=False, unique=True),
            sa.Column("description", sa.Text()),
            sa.Column("steps", postgresql.JSON(), nullable=False),
            sa.Column("config", postgresql.JSON()),
            sa.Column("is_default", sa.Boolean(), server_default="false"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    for table in (
        "workflows",
        "pipeline_asset_collections",
        "installed_plugins",
        "analytics_insights",
        "domain_events",
        "cost_entries",
        "project_memory",
        "agent_model_configs",
    ):
        if _table_exists(table):
            op.drop_table(table)

    if _column_exists("pipelines", "workflow_name"):
        op.drop_index("ix_pipelines_workflow_name", table_name="pipelines")
        op.drop_column("pipelines", "workflow_name")

    for col in ("parent_asset_id", "version", "tags", "sha256"):
        if _column_exists("assets", col):
            op.drop_column("assets", col)
