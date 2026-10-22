"""Merge main and phase 3 migrations

Revision ID: b9c0f377213e
Revises: 20261007_0010, 7f694ec0b142
Create Date: 2026-10-07 23:06:20.665451
"""

from collections.abc import Sequence

revision: str = "b9c0f377213e"
down_revision: str | tuple[str, ...] | None = ("20261007_0010", "7f694ec0b142")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
