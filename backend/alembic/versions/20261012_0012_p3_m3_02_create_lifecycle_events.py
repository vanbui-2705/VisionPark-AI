"""Create lifecycle_events table for phase 3.

Revision ID: 20261012_0012
Revises: 20261012_0011
Create Date: 2026-10-12 11:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261012_0012"
down_revision: str | tuple[str, ...] | None = "20261012_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lifecycle_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("building_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("lane_id", sa.Uuid(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("image_ref", sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(["lane_id"], ["lanes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["parking_transactions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lifecycle_events_session_id", "lifecycle_events", ["session_id"])
    op.create_index("ix_lifecycle_events_building_id", "lifecycle_events", ["building_id"])
    op.create_index("ix_lifecycle_events_event_type", "lifecycle_events", ["event_type"])
    op.create_index(
        "ix_lifecycle_events_building_occurred",
        "lifecycle_events",
        ["building_id", "occurred_at"],
    )
    op.create_index(
        "ix_lifecycle_events_session_occurred",
        "lifecycle_events",
        ["session_id", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_lifecycle_events_session_occurred", table_name="lifecycle_events")
    op.drop_index("ix_lifecycle_events_building_occurred", table_name="lifecycle_events")
    op.drop_index("ix_lifecycle_events_event_type", table_name="lifecycle_events")
    op.drop_index("ix_lifecycle_events_building_id", table_name="lifecycle_events")
    op.drop_index("ix_lifecycle_events_session_id", table_name="lifecycle_events")
    op.drop_table("lifecycle_events")
