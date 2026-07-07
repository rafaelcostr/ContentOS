"""V5.1.4 — Project DNA 2.0 columns on project_memory.

Revision ID: 021
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "021"
down_revision: Union[str, None] = "020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    cols = {c["name"] for c in inspect(bind).get_columns(table)}
    return column in cols


def upgrade() -> None:
    columns = [
        ("cinematic_preset", sa.String(40)),
        ("content_angle", sa.String(40)),
        ("brand_keywords", sa.JSON()),
        ("editing_preferences", sa.JSON()),
    ]
    for name, col_type in columns:
        if not _column_exists("project_memory", name):
            op.add_column("project_memory", sa.Column(name, col_type, nullable=True))


def downgrade() -> None:
    for name in ("editing_preferences", "brand_keywords", "content_angle", "cinematic_preset"):
        if _column_exists("project_memory", name):
            op.drop_column("project_memory", name)
