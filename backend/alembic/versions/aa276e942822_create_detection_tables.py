"""Create detection tables

Revision ID: aa276e942822
Revises: 20260918_0002_create_lane_tables
Create Date: 2026-09-18 22:28:25.334341
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "aa276e942822"
down_revision: str | None = "20260918_0002_create_lane_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    postgres = op.get_bind().dialect.name == "postgresql"
    lane_type = sa.Uuid() if postgres else sa.String(length=50)
    direction_type = sa.Enum("IN", "OUT", name="lanedirection")
    if postgres:
        direction_type.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "detections",
        sa.Column("lane_id", lane_type, nullable=False),
        sa.Column(
            "image_key",
            sa.String(length=255),
            nullable=False,
            comment="Storage key do ImageStorage trả về",
        ),
        sa.Column("raw_plate", sa.String(length=50), nullable=True),
        sa.Column("normalized_plate", sa.String(length=50), nullable=True),
        sa.Column("bbox_x1", sa.Integer(), nullable=True),
        sa.Column("bbox_y1", sa.Integer(), nullable=True),
        sa.Column("bbox_x2", sa.Integer(), nullable=True),
        sa.Column("bbox_y2", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["lane_id"], ["lanes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("detections", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_detections_image_key"), ["image_key"], unique=False)
        batch_op.create_index(batch_op.f("ix_detections_lane_id"), ["lane_id"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_detections_normalized_plate"), ["normalized_plate"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_detections_raw_plate"), ["raw_plate"], unique=False)

    with op.batch_alter_table("lanes", schema=None) as batch_op:
        batch_op.alter_column(
            "direction",
            existing_type=sa.VARCHAR(length=10),
            type_=direction_type,
            postgresql_using="direction::lanedirection",
            existing_nullable=False,
        )
        batch_op.drop_index(batch_op.f("ix_lanes_direction"))

    # ### end Alembic commands ###


def downgrade() -> None:
    postgres = op.get_bind().dialect.name == "postgresql"
    with op.batch_alter_table("lanes", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_lanes_direction"), ["direction"], unique=False)
        batch_op.alter_column(
            "direction",
            existing_type=sa.Enum("IN", "OUT", name="lanedirection"),
            type_=sa.VARCHAR(length=10),
            postgresql_using="direction::text",
            existing_nullable=False,
        )

    with op.batch_alter_table("detections", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_detections_raw_plate"))
        batch_op.drop_index(batch_op.f("ix_detections_normalized_plate"))
        batch_op.drop_index(batch_op.f("ix_detections_lane_id"))
        batch_op.drop_index(batch_op.f("ix_detections_image_key"))

    op.drop_table("detections")
    if postgres:
        sa.Enum(name="lanedirection").drop(op.get_bind(), checkfirst=True)
    # ### end Alembic commands ###
