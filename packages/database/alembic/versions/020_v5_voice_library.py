"""V5.1.2 — Project voice library default builtin.

Revision ID: 020
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    cols = {c["name"] for c in inspect(bind).get_columns(table)}
    return column in cols


def upgrade() -> None:
    if not _column_exists("project_memory", "default_voice_builtin"):
        op.add_column("project_memory", sa.Column("default_voice_builtin", sa.String(80), nullable=True))


def downgrade() -> None:
    if _column_exists("project_memory", "default_voice_builtin"):
        op.drop_column("project_memory", "default_voice_builtin")
