"""Preserve transaction context when lane or operator names change."""

import sqlalchemy as sa

from alembic import op

revision = "20261007_0010"
down_revision = "20261007_0009"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("parking_transactions", sa.Column("lane_name_snapshot", sa.String(120)))
    op.add_column("parking_transactions", sa.Column("operator_name_snapshot", sa.String(120)))


def downgrade():
    count = op.get_bind().execute(sa.text("SELECT COUNT(*) FROM parking_transactions")).scalar()
    if count:
        raise RuntimeError("Refusing downgrade: persistent transaction context would be lost.")
    op.drop_column("parking_transactions", "operator_name_snapshot")
    op.drop_column("parking_transactions", "lane_name_snapshot")
