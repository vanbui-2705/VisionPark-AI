"""Create parking transactions for check-in domain."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261002_0004"
down_revision: str | None = "073d8145270a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "parking_transactions",
        sa.Column("license_plate", sa.String(length=50), nullable=False),
        sa.Column("normalized_plate", sa.String(length=50), nullable=False),
        sa.Column("original_ai_plate", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PARKED"),
        sa.Column("lane_id", sa.Uuid(), nullable=False),
        sa.Column("detection_id", sa.Uuid(), nullable=True),
        sa.Column("image_url", sa.String(length=512), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column(
            "check_in_time",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("check_in_operator_id", sa.Uuid(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("is_manual_override", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["lane_id"], ["lanes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["detection_id"], ["detections.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["check_in_operator_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index(
        "ix_parking_transactions_license_plate", "parking_transactions", ["license_plate"]
    )
    op.create_index(
        "ix_parking_transactions_normalized_plate", "parking_transactions", ["normalized_plate"]
    )
    op.create_index("ix_parking_transactions_lane_id", "parking_transactions", ["lane_id"])
    op.create_index(
        "ix_parking_transactions_detection_id", "parking_transactions", ["detection_id"]
    )
    op.create_index(
        "ix_parking_transactions_check_in_operator_id",
        "parking_transactions",
        ["check_in_operator_id"],
    )
    op.create_index(
        "uq_parking_transactions_active_plate",
        "parking_transactions",
        ["normalized_plate"],
        unique=True,
        postgresql_where=sa.text("status = 'PARKED'"),
        sqlite_where=sa.text("status = 'PARKED'"),
    )


def downgrade() -> None:
    op.drop_index("uq_parking_transactions_active_plate", table_name="parking_transactions")
    for name in (
        "ix_parking_transactions_check_in_operator_id",
        "ix_parking_transactions_detection_id",
        "ix_parking_transactions_lane_id",
        "ix_parking_transactions_normalized_plate",
        "ix_parking_transactions_license_plate",
    ):
        op.drop_index(name, table_name="parking_transactions")
    op.drop_table("parking_transactions")
