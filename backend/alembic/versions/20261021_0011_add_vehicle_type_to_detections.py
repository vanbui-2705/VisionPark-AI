"""Add vehicle type, vehicle bbox, detector version, and building_id to detections (SPEC-AI-02)."""

import sqlalchemy as sa
from alembic import op

revision = "20261021_0011"
down_revision = "20261007_0010"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "detections",
        sa.Column("vehicle_type", sa.String(length=20), nullable=True, server_default="UNKNOWN"),
    )
    op.add_column("detections", sa.Column("vehicle_confidence", sa.Float(), nullable=True))
    op.add_column("detections", sa.Column("vehicle_bbox_x1", sa.Integer(), nullable=True))
    op.add_column("detections", sa.Column("vehicle_bbox_y1", sa.Integer(), nullable=True))
    op.add_column("detections", sa.Column("vehicle_bbox_x2", sa.Integer(), nullable=True))
    op.add_column("detections", sa.Column("vehicle_bbox_y2", sa.Integer(), nullable=True))
    op.add_column(
        "detections", sa.Column("model_version_detector", sa.String(length=120), nullable=True)
    )
    op.add_column("detections", sa.Column("building_id", sa.String(length=50), nullable=True))

    op.create_index(
        "ix_detections_vehicle_type", "detections", ["vehicle_type"], unique=False
    )
    op.create_index("ix_detections_building_id", "detections", ["building_id"], unique=False)


def downgrade():
    op.drop_index("ix_detections_building_id", table_name="detections")
    op.drop_index("ix_detections_vehicle_type", table_name="detections")
    op.drop_column("detections", "building_id")
    op.drop_column("detections", "model_version_detector")
    op.drop_column("detections", "vehicle_bbox_y2")
    op.drop_column("detections", "vehicle_bbox_x2")
    op.drop_column("detections", "vehicle_bbox_y1")
    op.drop_column("detections", "vehicle_bbox_x1")
    op.drop_column("detections", "vehicle_confidence")
    op.drop_column("detections", "vehicle_type")
