"""Create lane tables.

Revision ID: 20260918_0002
Revises: 20260906_0001
Create Date: 2026-09-18
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260918_0002_create_lane_tables"
down_revision: str | None = "20260906_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lanes",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("direction", sa.String(length=10), nullable=False),
        sa.Column("video_source", sa.String(length=512), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lanes_name", "lanes", ["name"], unique=True)
    op.create_index("ix_lanes_direction", "lanes", ["direction"])


def downgrade() -> None:
    op.drop_index("ix_lanes_direction", table_name="lanes")
    op.drop_index("ix_lanes_name", table_name="lanes")
    op.drop_table("lanes")
