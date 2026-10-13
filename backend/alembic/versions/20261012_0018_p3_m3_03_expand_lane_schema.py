"""Add P3-M3-03 lane columns: allowed_vehicle_type, camera_id, barrier_id.

Revision ID: 20261012_0018
Revises: 20261012_0017
Create Date: 2026-10-13 10:55:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261012_0018"
down_revision: str | tuple[str, ...] | None = "20261012_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("lanes") as batch:
        batch.add_column(
            sa.Column(
                "allowed_vehicle_type",
                sa.String(length=20),
                nullable=True,
                server_default="ALL",
            )
        )
        batch.add_column(sa.Column("camera_id", sa.String(length=100), nullable=True))
        batch.add_column(sa.Column("barrier_id", sa.String(length=100), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("lanes") as batch:
        batch.drop_column("barrier_id")
        batch.drop_column("camera_id")
        batch.drop_column("allowed_vehicle_type")

