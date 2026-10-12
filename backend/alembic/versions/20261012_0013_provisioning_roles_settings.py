"""Map the four existing roles and add provisioning/Setting metadata.

Revision ID: 20261012_0013
Revises: 20261012_0012
"""

import sqlalchemy as sa
from alembic import op

revision = "20261012_0013"
down_revision = "20261012_0012"
branch_labels = None
depends_on = None


def upgrade():
    roles = sa.table("roles", sa.column("name", sa.String()))
    op.execute(roles.update().where(roles.c.name == "ADMIN").values(name="SYSTEM_ADMIN"))
    op.execute(roles.update().where(roles.c.name == "TECHNICIAN").values(name="BUILDING_ADMIN"))
    with op.batch_alter_table("users") as batch:
        batch.add_column(
            sa.Column(
                "must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()
            )
        )
    with op.batch_alter_table("parking_lots") as batch:
        batch.add_column(
            sa.Column("settings_revision", sa.Integer(), nullable=False, server_default="0")
        )
    with op.batch_alter_table("lanes") as batch:
        batch.add_column(
            sa.Column(
                "allowed_vehicle_types",
                sa.JSON(),
                nullable=False,
                server_default='["CAR", "MOTORBIKE", "BICYCLE"]',
            )
        )
        batch.add_column(sa.Column("camera", sa.String(255), nullable=True))
        batch.add_column(sa.Column("barrier", sa.String(255), nullable=True))


def downgrade():
    with op.batch_alter_table("lanes") as batch:
        batch.drop_column("barrier")
        batch.drop_column("camera")
        batch.drop_column("allowed_vehicle_types")
    with op.batch_alter_table("parking_lots") as batch:
        batch.drop_column("settings_revision")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("must_change_password")
    roles = sa.table("roles", sa.column("name", sa.String()))
    op.execute(roles.update().where(roles.c.name == "SYSTEM_ADMIN").values(name="ADMIN"))
    op.execute(roles.update().where(roles.c.name == "BUILDING_ADMIN").values(name="TECHNICIAN"))
