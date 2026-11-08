"""merge M5 and main migration heads

Revision ID: 74b01c7c04ec
Revises: 20261018_0015, 20261021_0011
Create Date: 2026-10-22 23:30:01.100671
"""

from collections.abc import Sequence

revision: str = "74b01c7c04ec"
down_revision: str | None = ("20261018_0015", "20261021_0011")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
