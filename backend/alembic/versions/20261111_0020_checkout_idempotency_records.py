"""Add dedicated idempotency_records table for checkout and payment operations (BUILD-01).

Revision ID: 20261111_0020
Revises: 74b01c7c04ec
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261111_0020"
down_revision: str | None = "74b01c7c04ec"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "building_id",
            sa.Uuid(),
            sa.ForeignKey("buildings.id", ondelete="RESTRICT"),
            nullable=False,
            server_default="00000000000000000000000000000001",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("operation", sa.String(40), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column(
            "transaction_id",
            sa.Uuid(),
            sa.ForeignKey("parking_transactions.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("response_payload", sa.JSON(), nullable=True),
        sa.UniqueConstraint(
            "building_id",
            "operation",
            "key",
            name="uq_idempotency_records_building_op_key",
        ),
        sa.CheckConstraint(
            "length(key) BETWEEN 1 AND 255",
            name="ck_idempotency_records_key",
        ),
        sa.CheckConstraint(
            "length(request_fingerprint) = 64",
            name="ck_idempotency_records_fingerprint",
        ),
        sa.CheckConstraint(
            "operation IN ('CHECKOUT', 'RECORD_PAYMENT')",
            name="ck_idempotency_records_operation",
        ),
    )
    op.create_index("ix_idempotency_records_building_id", "idempotency_records", ["building_id"])
    op.create_index(
        "ix_idempotency_records_transaction_id", "idempotency_records", ["transaction_id"]
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT COUNT(*) FROM idempotency_records")).scalar():
        raise RuntimeError("Refusing downgrade: idempotency_records would be lost")
    op.drop_index("ix_idempotency_records_transaction_id", table_name="idempotency_records")
    op.drop_index("ix_idempotency_records_building_id", table_name="idempotency_records")
    op.drop_table("idempotency_records")
