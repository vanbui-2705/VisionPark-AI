"""Create parking_counters and counter_events tables.

Revision ID: 20261012_0014
Revises: 20261012_0013
Create Date: 2026-10-12 14:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261012_0017"
down_revision: str | tuple[str, ...] | None = "20261012_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "parking_counters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("building_id", sa.Uuid(), nullable=True),
        sa.Column("vehicle_type", sa.String(length=32), nullable=False),
        sa.Column("occupied", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "building_id", "vehicle_type", name="uq_parking_counters_building_vehicle"
        ),
    )
    op.create_index("ix_parking_counters_building_id", "parking_counters", ["building_id"])
    op.create_index("ix_parking_counters_vehicle_type", "parking_counters", ["vehicle_type"])

    op.create_table(
        "counter_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("building_id", sa.Uuid(), nullable=True),
        sa.Column("counter_id", sa.Uuid(), nullable=True),
        sa.Column("vehicle_type", sa.String(length=32), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column("actor_type", sa.String(length=32), server_default="SYSTEM", nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_counter_events_building_id", "counter_events", ["building_id"])
    op.create_index("ix_counter_events_counter_id", "counter_events", ["counter_id"])
    op.create_index("ix_counter_events_vehicle_type", "counter_events", ["vehicle_type"])
    op.create_index("ix_counter_events_session_id", "counter_events", ["session_id"])
    op.create_index("ix_counter_events_occurred_at", "counter_events", ["occurred_at"])
    op.create_index(
        "ix_counter_events_building_occurred",
        "counter_events",
        ["building_id", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_counter_events_building_occurred", table_name="counter_events")
    op.drop_index("ix_counter_events_occurred_at", table_name="counter_events")
    op.drop_index("ix_counter_events_session_id", table_name="counter_events")
    op.drop_index("ix_counter_events_vehicle_type", table_name="counter_events")
    op.drop_index("ix_counter_events_counter_id", table_name="counter_events")
    op.drop_index("ix_counter_events_building_id", table_name="counter_events")
    op.drop_table("counter_events")

    op.drop_index("ix_parking_counters_vehicle_type", table_name="parking_counters")
    op.drop_index("ix_parking_counters_building_id", table_name="parking_counters")
    op.drop_table("parking_counters")
