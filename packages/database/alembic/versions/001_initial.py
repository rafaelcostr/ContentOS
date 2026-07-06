"""Initial schema

Revision ID: 001
"""

from typing import Sequence, Union

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tables created via Base.metadata.create_all on first boot.
    # Use autogenerate for future migrations: alembic revision --autogenerate -m "description"
    pass


def downgrade() -> None:
    pass
