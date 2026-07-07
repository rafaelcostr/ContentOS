"""Pipeline context_json column — workflow engine state.

Revision ID: 023
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "023"
down_revision: Union[str, None] = "022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    cols = [c["name"] for c in inspect(bind).get_columns(table)]
    return column in cols


def upgrade() -> None:
    if not _column_exists("pipelines", "context_json"):
        op.add_column("pipelines", sa.Column("context_json", postgresql.JSON(), nullable=True))


def downgrade() -> None:
    if _column_exists("pipelines", "context_json"):
        op.drop_column("pipelines", "context_json")
