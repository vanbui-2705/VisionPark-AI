"""Expand parking_transactions schema for phase 3.

Revision ID: 20261012_0011
Revises: b9c0f377213e
Create Date: 2026-10-12 11:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261012_0015"
down_revision: str | tuple[str, ...] | None = "20261012_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_STATUS_CONSTRAINT = "status IN ('PARKED', 'COMPLETED', 'CANCELLED')"
NEW_STATUS_CONSTRAINT = (
    "status IN ('CREATED', 'ENTERED', 'PARKED', 'PAYMENT_PENDING', "
    "'PAID', 'EXITED', 'COMPLETED', 'CANCELLED', 'EXCEPTION')"
)


def upgrade() -> None:
    with op.batch_alter_table("parking_transactions") as batch:
        batch.alter_column("license_plate", existing_type=sa.String(50), nullable=True)
        batch.alter_column("normalized_plate", existing_type=sa.String(50), nullable=True)
        batch.add_column(sa.Column("ticket_code", sa.String(length=64), nullable=True))
        batch.add_column(
            sa.Column("vehicle_type", sa.String(length=20), nullable=False, server_default="CAR")
        )
        batch.add_column(sa.Column("exit_time", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("exit_lane_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("fee", sa.Float(), nullable=True, server_default=sa.text("0.0")))
        batch.add_column(sa.Column("ticket_product_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key(
            "fk_parking_transactions_exit_lane_id",
            "lanes",
            ["exit_lane_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.drop_constraint("ck_parking_transactions_status", type_="check")
        batch.create_check_constraint("ck_parking_transactions_status", NEW_STATUS_CONSTRAINT)
        batch.drop_index("uq_parking_transactions_active_plate")
        batch.create_index(
            "ix_parking_transactions_ticket_code",
            ["ticket_code"],
        )
        batch.create_index(
            "ix_parking_transactions_exit_lane_id",
            ["exit_lane_id"],
        )
        batch.create_index(
            "ix_parking_transactions_ticket_product_id",
            ["ticket_product_id"],
        )
        batch.create_index(
            "uq_parking_transactions_active_plate",
            ["building_id", "normalized_plate"],
            unique=True,
            postgresql_where=sa.text(
                "status IN ('PARKED', 'ENTERED', 'PAYMENT_PENDING', 'PAID') "
                "AND normalized_plate IS NOT NULL"
            ),
            sqlite_where=sa.text(
                "status IN ('PARKED', 'ENTERED', 'PAYMENT_PENDING', 'PAID') "
                "AND normalized_plate IS NOT NULL"
            ),
        )
        batch.create_index(
            "uq_parking_transactions_active_ticket",
            ["ticket_code"],
            unique=True,
            postgresql_where=sa.text(
                "status IN ('PARKED', 'ENTERED', 'PAYMENT_PENDING', 'PAID') "
                "AND ticket_code IS NOT NULL"
            ),
            sqlite_where=sa.text(
                "status IN ('PARKED', 'ENTERED', 'PAYMENT_PENDING', 'PAID') "
                "AND ticket_code IS NOT NULL"
            ),
        )


def downgrade() -> None:
    with op.batch_alter_table("parking_transactions") as batch:
        batch.drop_index("uq_parking_transactions_active_ticket")
        batch.drop_index("uq_parking_transactions_active_plate")
        batch.drop_index("ix_parking_transactions_ticket_product_id")
        batch.drop_index("ix_parking_transactions_exit_lane_id")
        batch.drop_index("ix_parking_transactions_ticket_code")
        batch.create_index(
            "uq_parking_transactions_active_plate",
            ["building_id", "normalized_plate"],
            unique=True,
            postgresql_where=sa.text("status = 'PARKED'"),
            sqlite_where=sa.text("status = 'PARKED'"),
        )
        batch.drop_constraint("ck_parking_transactions_status", type_="check")
        batch.create_check_constraint("ck_parking_transactions_status", OLD_STATUS_CONSTRAINT)
        batch.drop_constraint("fk_parking_transactions_exit_lane_id", type_="foreignkey")
        batch.drop_column("ticket_product_id")
        batch.drop_column("fee")
        batch.drop_column("exit_lane_id")
        batch.drop_column("exit_time")
        batch.drop_column("vehicle_type")
        batch.drop_column("ticket_code")
        batch.alter_column("normalized_plate", existing_type=sa.String(50), nullable=False)
        batch.alter_column("license_plate", existing_type=sa.String(50), nullable=False)
