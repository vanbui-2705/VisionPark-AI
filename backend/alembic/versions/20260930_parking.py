"""Create parking_transactions

Revision ID: 20260930_parking
Revises: 20260921_0003
"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "20260930_parking"
down_revision: str = "20260921_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    postgres = op.get_bind().dialect.name == "postgresql"
    tx_status = sa.Enum("PARKED", "COMPLETED", "CANCELLED", name="transactionstatus")
    tx_source = sa.Enum("STATION_AUTO", "OPERATOR_MANUAL", name="checkinsource")
    if postgres:
        tx_status.create(op.get_bind(), checkfirst=True)
        tx_source.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "parking_transactions",
        sa.Column("license_plate", sa.String(length=50), nullable=False),
        sa.Column("original_ai_plate", sa.String(length=50), nullable=True),
        sa.Column("normalized_plate", sa.String(length=50), nullable=False),
        sa.Column("status", tx_status, nullable=False),
        sa.Column("lane_id", sa.Uuid(), nullable=False),
        sa.Column("lane_name", sa.String(length=255), nullable=True),
        sa.Column("detection_id", sa.Uuid(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("check_in_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("check_in_operator_id", sa.Uuid(), nullable=True),
        sa.Column("source", tx_source, nullable=False),
        sa.Column("is_manual_override", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["lane_id"], ["lanes.id"], name="fk_parking_transactions_lane_id", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["detection_id"], ["detections.id"], name="fk_parking_transactions_detection_id", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["check_in_operator_id"], ["users.id"], name="fk_parking_transactions_operator_id", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("parking_transactions", schema=None) as batch_op:
        batch_op.create_index("ix_parking_transactions_lane_id", ["lane_id"], unique=False)
        batch_op.create_index("ix_parking_transactions_license_plate", ["license_plate"], unique=False)
        batch_op.create_index("ix_parking_transactions_status", ["status"], unique=False)
        batch_op.create_index("ix_parking_transactions_check_in_time", ["check_in_time"], unique=False)
        batch_op.create_index("ix_parking_transactions_normalized_plate", ["normalized_plate"], unique=False)
        batch_op.create_index("ix_parking_transactions_detection_id", ["detection_id"], unique=False)
        batch_op.create_index("ix_parking_transactions_check_in_operator_id", ["check_in_operator_id"], unique=False)


def downgrade() -> None:
    op.drop_table("parking_transactions")
    postgres = op.get_bind().dialect.name == "postgresql"
    if postgres:
        sa.Enum(name="checkinsource").drop(op.get_bind(), checkfirst=True)
        sa.Enum(name="transactionstatus").drop(op.get_bind(), checkfirst=True)
