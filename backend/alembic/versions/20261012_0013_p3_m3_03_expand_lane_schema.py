"""Expand lanes schema with vehicle type, devices and building.

Revision ID: 20261012_0013
Revises: 20261012_0012
Create Date: 2026-10-12 11:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261012_0013"
down_revision: str | tuple[str, ...] | None = "20261012_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("lanes") as batch:
        batch.add_column(
            sa.Column(
                "allowed_vehicle_type",
                sa.String(length=20),
                nullable=False,
                server_default="ALL",
            )
        )
        batch.add_column(sa.Column("camera_id", sa.String(length=100), nullable=True))
        batch.add_column(sa.Column("barrier_id", sa.String(length=100), nullable=True))
        batch.add_column(sa.Column("building_id", sa.Uuid(), nullable=True))
        batch.create_index("ix_lanes_building_id", ["building_id"])


def downgrade() -> None:
    with op.batch_alter_table("lanes") as batch:
        batch.drop_index("ix_lanes_building_id")
        batch.drop_column("building_id")
        batch.drop_column("barrier_id")
        batch.drop_column("camera_id")
        batch.drop_column("allowed_vehicle_type")
