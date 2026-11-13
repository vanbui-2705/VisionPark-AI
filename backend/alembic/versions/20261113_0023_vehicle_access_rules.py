"""Replace hard-coded blacklist entries with building-scoped access rules.

Revision ID: 20261113_0023
Revises: 20261113_0022
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261113_0023"
down_revision: str | None = "20261113_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vehicle_access_rules",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "building_id",
            sa.Uuid(),
            sa.ForeignKey("buildings.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("normalized_plate", sa.String(50), nullable=True),
        sa.Column("ticket_code", sa.String(80), nullable=True),
        sa.Column("decision", sa.String(10), nullable=False),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "normalized_plate IS NOT NULL OR ticket_code IS NOT NULL",
            name="ck_vehicle_access_rules_identifier",
        ),
        sa.CheckConstraint(
            "decision IN ('ALLOW', 'DENY')", name="ck_vehicle_access_rules_decision"
        ),
        sa.UniqueConstraint(
            "building_id", "normalized_plate", name="uq_vehicle_access_rules_building_plate"
        ),
        sa.UniqueConstraint(
            "building_id", "ticket_code", name="uq_vehicle_access_rules_building_ticket"
        ),
    )
    op.create_index("ix_vehicle_access_rules_building_id", "vehicle_access_rules", ["building_id"])


def downgrade() -> None:
    op.drop_index("ix_vehicle_access_rules_building_id", table_name="vehicle_access_rules")
    op.drop_table("vehicle_access_rules")
