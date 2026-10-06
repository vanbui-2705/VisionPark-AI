"""Add parking transaction integrity constraints without rewriting existing data."""

from alembic import op

revision = "20261006_0006"
down_revision = "20261004_0005"
branch_labels = None
depends_on = None

CONSTRAINTS = {
    "ck_parking_transactions_status": "status IN ('PARKED', 'COMPLETED', 'CANCELLED')",
    "ck_parking_transactions_confidence": (
        "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)"
    ),
    "ck_parking_transactions_idempotency_key": "length(idempotency_key) BETWEEN 1 AND 255",
    "ck_parking_transactions_fingerprint": "length(request_fingerprint) = 64",
}


def upgrade() -> None:
    with op.batch_alter_table("parking_transactions") as batch:
        for name, condition in CONSTRAINTS.items():
            batch.create_check_constraint(name, condition)


def downgrade() -> None:
    with op.batch_alter_table("parking_transactions") as batch:
        for name in reversed(CONSTRAINTS):
            batch.drop_constraint(name, type_="check")
