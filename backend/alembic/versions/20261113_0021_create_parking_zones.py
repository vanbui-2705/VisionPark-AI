"""Create building-scoped parking zones for monthly subscriptions.

Revision ID: 20261113_0021
Revises: 20261111_0020
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261113_0021"
down_revision: str | None = "20261111_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "parking_zones",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "building_id",
            sa.Uuid(),
            sa.ForeignKey("buildings.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("building_id", "code", name="uq_parking_zones_building_code"),
    )
    op.create_index("ix_parking_zones_building_id", "parking_zones", ["building_id"])

    # Existing installations may already contain subscriptions with opaque zone UUIDs.
    # Preserve them by materialising one legacy zone per distinct building/zone pair.
    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT DISTINCT building_id, zone_id FROM subscriptions")
    ).fetchall()
    for index, row in enumerate(rows, start=1):
        connection.execute(
            sa.text(
                "INSERT INTO parking_zones "
                "(id, building_id, code, name, active) "
                "VALUES (:id, :building_id, :code, :name, :active)"
            ),
            {
                "id": row.zone_id,
                "building_id": row.building_id,
                "code": f"LEGACY-{index}",
                "name": f"Khu vực cũ {index}",
                "active": True,
            },
        )

    with op.batch_alter_table("subscriptions") as batch:
        batch.create_foreign_key(
            "fk_subscriptions_zone_id_parking_zones",
            "parking_zones",
            ["zone_id"],
            ["id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    with op.batch_alter_table("subscriptions") as batch:
        batch.drop_constraint("fk_subscriptions_zone_id_parking_zones", type_="foreignkey")
    op.drop_index("ix_parking_zones_building_id", table_name="parking_zones")
    op.drop_table("parking_zones")
