"""Pipeline schedule context_json — Growth OS Fase 13."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "027"
down_revision: Union[str, None] = "026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    cols = [c["name"] for c in inspect(bind).get_columns(table)]
    return column in cols


def upgrade() -> None:
    if not _column_exists("pipeline_schedules", "context_json"):
        op.add_column("pipeline_schedules", sa.Column("context_json", postgresql.JSON(), nullable=True))


def downgrade() -> None:
    if _column_exists("pipeline_schedules", "context_json"):
        op.drop_column("pipeline_schedules", "context_json")
