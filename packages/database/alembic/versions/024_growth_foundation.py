"""Growth AI foundation tables.

Revision ID: 024
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "024"
down_revision: Union[str, None] = "023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table: str) -> bool:
    return table in inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if not _table_exists("growth_channel_profiles"):
        op.create_table(
            "growth_channel_profiles",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("channel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
            sa.Column("score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("profile_data", postgresql.JSON(), nullable=True),
            sa.Column("report", postgresql.JSON(), nullable=True),
            sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_growth_channel_profiles_project_id", "growth_channel_profiles", ["project_id"])
        op.create_index("ix_growth_channel_profiles_channel_id", "growth_channel_profiles", ["channel_id"], unique=True)

    if not _table_exists("growth_competitors"):
        op.create_table(
            "growth_competitors",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("platform", sa.String(50), nullable=False),
            sa.Column("handle", sa.String(255), nullable=False),
            sa.Column("display_name", sa.String(255), nullable=False),
            sa.Column("url", sa.String(1000), nullable=True),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("metrics", postgresql.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_growth_competitors_project_id", "growth_competitors", ["project_id"])
        op.create_index("ix_growth_competitors_platform", "growth_competitors", ["platform"])
        op.create_index("ix_growth_competitors_handle", "growth_competitors", ["handle"])
        op.create_index("ix_growth_competitors_created_at", "growth_competitors", ["created_at"])

    if not _table_exists("growth_reports"):
        op.create_table(
            "growth_reports",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("channel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("channels.id", ondelete="SET NULL"), nullable=True),
            sa.Column("score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("summary", sa.Text(), nullable=False, server_default=""),
            sa.Column("report", postgresql.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_growth_reports_project_id", "growth_reports", ["project_id"])
        op.create_index("ix_growth_reports_channel_id", "growth_reports", ["channel_id"])
        op.create_index("ix_growth_reports_created_at", "growth_reports", ["created_at"])

    if not _table_exists("growth_strategies"):
        op.create_table(
            "growth_strategies",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("channel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("channels.id", ondelete="SET NULL"), nullable=True),
            sa.Column("status", sa.String(40), nullable=False, server_default="draft"),
            sa.Column("goals", postgresql.JSON(), nullable=True),
            sa.Column("kpis", postgresql.JSON(), nullable=True),
            sa.Column("cadence", postgresql.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_growth_strategies_project_id", "growth_strategies", ["project_id"])
        op.create_index("ix_growth_strategies_channel_id", "growth_strategies", ["channel_id"])
        op.create_index("ix_growth_strategies_status", "growth_strategies", ["status"])
        op.create_index("ix_growth_strategies_created_at", "growth_strategies", ["created_at"])

    if not _table_exists("growth_recommendations"):
        op.create_table(
            "growth_recommendations",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("channel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("channels.id", ondelete="SET NULL"), nullable=True),
            sa.Column("kind", sa.String(80), nullable=False),
            sa.Column("title", sa.String(300), nullable=False),
            sa.Column("detail", sa.Text(), nullable=False, server_default=""),
            sa.Column("priority", sa.String(30), nullable=False, server_default="medium"),
            sa.Column("source", sa.String(80), nullable=False, server_default="growth"),
            sa.Column("status", sa.String(40), nullable=False, server_default="open"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_growth_recommendations_project_id", "growth_recommendations", ["project_id"])
        op.create_index("ix_growth_recommendations_channel_id", "growth_recommendations", ["channel_id"])
        op.create_index("ix_growth_recommendations_kind", "growth_recommendations", ["kind"])
        op.create_index("ix_growth_recommendations_priority", "growth_recommendations", ["priority"])
        op.create_index("ix_growth_recommendations_source", "growth_recommendations", ["source"])
        op.create_index("ix_growth_recommendations_status", "growth_recommendations", ["status"])
        op.create_index("ix_growth_recommendations_created_at", "growth_recommendations", ["created_at"])

    if not _table_exists("growth_asset_performance"):
        op.create_table(
            "growth_asset_performance",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("channel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("channels.id", ondelete="SET NULL"), nullable=True),
            sa.Column("asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True),
            sa.Column("uses", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("ctr", sa.Float(), nullable=True),
            sa.Column("retention_pct", sa.Float(), nullable=True),
            sa.Column("watch_time_seconds", sa.Float(), nullable=True),
            sa.Column("engagement_rate", sa.Float(), nullable=True),
            sa.Column("ai_score", sa.Float(), nullable=True),
            sa.Column("metadata_", postgresql.JSON(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_growth_asset_performance_project_id", "growth_asset_performance", ["project_id"])
        op.create_index("ix_growth_asset_performance_channel_id", "growth_asset_performance", ["channel_id"])
        op.create_index("ix_growth_asset_performance_asset_id", "growth_asset_performance", ["asset_id"])
        op.create_index("ix_growth_asset_performance_updated_at", "growth_asset_performance", ["updated_at"])

    if not _table_exists("growth_content_calendar"):
        op.create_table(
            "growth_content_calendar",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("channel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("channels.id", ondelete="SET NULL"), nullable=True),
            sa.Column("title", sa.String(300), nullable=False),
            sa.Column("topic", sa.String(500), nullable=False, server_default=""),
            sa.Column("planned_for", sa.DateTime(timezone=True), nullable=True),
            sa.Column("status", sa.String(40), nullable=False, server_default="planned"),
            sa.Column("metadata_", postgresql.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_growth_content_calendar_project_id", "growth_content_calendar", ["project_id"])
        op.create_index("ix_growth_content_calendar_channel_id", "growth_content_calendar", ["channel_id"])
        op.create_index("ix_growth_content_calendar_planned_for", "growth_content_calendar", ["planned_for"])
        op.create_index("ix_growth_content_calendar_status", "growth_content_calendar", ["status"])
        op.create_index("ix_growth_content_calendar_created_at", "growth_content_calendar", ["created_at"])


def downgrade() -> None:
    for table in (
        "growth_content_calendar",
        "growth_asset_performance",
        "growth_recommendations",
        "growth_strategies",
        "growth_reports",
        "growth_competitors",
        "growth_channel_profiles",
    ):
        if _table_exists(table):
            op.drop_table(table)
