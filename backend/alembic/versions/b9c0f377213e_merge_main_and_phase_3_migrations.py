"""Merge main and phase 3 migrations

Revision ID: b9c0f377213e
Revises: 20261007_0010, 7f694ec0b142
Create Date: 2026-10-07 23:06:20.665451
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b9c0f377213e'
down_revision: Union[str, None] = ('20261007_0010', '7f694ec0b142')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
