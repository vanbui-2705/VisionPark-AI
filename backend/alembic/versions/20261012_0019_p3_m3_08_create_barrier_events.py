"""Create barrier_events table (BR-08, BR-23).

Revision ID: 20261012_0019
Revises: 20261012_0018
Create Date: 2026-10-13 20:15:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261012_0019"
down_revision: str | tuple[str, ...] | None = "20261012_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "barrier_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("building_id", sa.Uuid(), nullable=True),
        sa.Column("lane_id", sa.Uuid(), nullable=False),
        sa.Column("barrier_id", sa.String(length=100), nullable=True),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("trigger_reason", sa.String(length=50), nullable=False),
        sa.Column("operator_id", sa.Uuid(), nullable=True),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), server_default="15", nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["building_id"], ["buildings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lane_id"], ["lanes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["operator_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["parking_transactions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_barrier_events_building_id", "barrier_events", ["building_id"])
    op.create_index("ix_barrier_events_lane_id", "barrier_events", ["lane_id"])
    op.create_index("ix_barrier_events_session_id", "barrier_events", ["session_id"])
    op.create_index("ix_barrier_events_trigger_reason", "barrier_events", ["trigger_reason"])
    op.create_index("ix_barrier_events_created_at", "barrier_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_barrier_events_created_at", table_name="barrier_events")
    op.drop_index("ix_barrier_events_trigger_reason", table_name="barrier_events")
    op.drop_index("ix_barrier_events_session_id", table_name="barrier_events")
    op.drop_index("ix_barrier_events_lane_id", table_name="barrier_events")
    op.drop_index("ix_barrier_events_building_id", table_name="barrier_events")
    op.drop_table("barrier_events")
