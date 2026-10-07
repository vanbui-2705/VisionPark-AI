"""Preserve model version and confirmation time for detection history."""

import sqlalchemy as sa

from alembic import op

revision = "20261007_0007"
down_revision = "20261006_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("detections") as batch:
        batch.add_column(sa.Column("model_version", sa.String(120), nullable=True))
        batch.add_column(sa.Column("capture_fingerprint", sa.String(64), nullable=True))
        batch.add_column(sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("detections") as batch:
        batch.drop_column("confirmed_at")
        batch.drop_column("capture_fingerprint")
        batch.drop_column("model_version")
