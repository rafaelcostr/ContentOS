"""V4 Epic 8 — Project DNA columns on project_memory.

Revision ID: 010
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    return column in {c["name"] for c in inspect(bind).get_columns(table)}


def upgrade() -> None:
    columns = [
        ("humor_level", sa.Float(), None),
        ("pace", sa.String(20), None),
        ("visual_style", sa.JSON(), None),
        ("narrator_persona", sa.String(255), None),
        ("preferred_formats", sa.JSON(), None),
        ("hook_patterns", sa.JSON(), None),
        ("cta_style", sa.String(255), None),
    ]
    for name, col_type, server_default in columns:
        if not _column_exists("project_memory", name):
            op.add_column("project_memory", sa.Column(name, col_type, nullable=True, server_default=server_default))


def downgrade() -> None:
    for name in (
        "cta_style",
        "hook_patterns",
        "preferred_formats",
        "narrator_persona",
        "visual_style",
        "pace",
        "humor_level",
    ):
        if _column_exists("project_memory", name):
            op.drop_column("project_memory", name)
