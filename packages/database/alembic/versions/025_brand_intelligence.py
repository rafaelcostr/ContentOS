"""Brand intelligence columns on project_memory — Growth OS Fase 5.

Revision ID: 025
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "025"
down_revision: Union[str, None] = "024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    cols = {c["name"] for c in inspect(bind).get_columns(table)}
    return column in cols


def upgrade() -> None:
    columns = [
        ("mission", sa.Text()),
        ("objectives", postgresql.JSON()),
        ("values", postgresql.JSON()),
        ("target_audience", sa.String(500)),
        ("editorial_rules", postgresql.JSON()),
        ("color_palette", postgresql.JSON()),
    ]
    for name, col_type in columns:
        if not _column_exists("project_memory", name):
            op.add_column("project_memory", sa.Column(name, col_type, nullable=True))


def downgrade() -> None:
    for name in ("color_palette", "editorial_rules", "target_audience", "values", "objectives", "mission"):
        if _column_exists("project_memory", name):
            op.drop_column("project_memory", name)
