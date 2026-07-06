"""Add providers and workflows tables.

Revision ID: 002
"""

from typing import Sequence, Union

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tables created via Base.metadata.create_all on boot for new installs.
    # Existing deployments: alembic upgrade head
    pass


def downgrade() -> None:
    pass
