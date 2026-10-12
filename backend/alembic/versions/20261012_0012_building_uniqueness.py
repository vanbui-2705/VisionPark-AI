"""VAN-60: scope lane names and parking uniqueness to each building."""

import sqlalchemy as sa
from alembic import op

revision = "20261012_0012"
down_revision = "20261012_0011"
branch_labels = None
depends_on = None


def active_plate_index(columns):
    op.create_index(
        "uq_parking_transactions_active_plate",
        "parking_transactions",
        columns,
        unique=True,
        sqlite_where=sa.text("status = 'PARKED'"),
        postgresql_where=sa.text("status = 'PARKED'"),
    )


def old_key_constraint():
    constraints = sa.inspect(op.get_bind()).get_unique_constraints("parking_transactions")
    return next(item["name"] for item in constraints if item["column_names"] == ["idempotency_key"])


def upgrade():
    op.drop_index("ix_lanes_name", table_name="lanes")
    op.create_index("ix_lanes_name", "lanes", ["name"])
    op.create_index("ix_lanes_building_name", "lanes", ["building_id", "name"], unique=True)
    op.drop_index("uq_parking_transactions_active_plate", table_name="parking_transactions")
    naming = {"uq": "uq_%(table_name)s_%(column_0_name)s"}
    name = old_key_constraint() or "uq_parking_transactions_idempotency_key"
    with op.batch_alter_table("parking_transactions", naming_convention=naming) as batch:
        batch.drop_constraint(name, type_="unique")
        batch.create_unique_constraint(
            "uq_parking_building_key", ["building_id", "idempotency_key"]
        )
    active_plate_index(["building_id", "normalized_plate"])


def downgrade():
    connection = op.get_bind()
    for table_name, column_name, parked_only in (
        ("lanes", "name", False),
        ("parking_transactions", "idempotency_key", False),
        ("parking_transactions", "normalized_plate", True),
    ):
        table = sa.table(table_name, sa.column(column_name), sa.column("status"))
        statement = sa.select(table.c[column_name]).group_by(table.c[column_name])
        if parked_only:
            statement = statement.where(table.c.status == "PARKED")
        if connection.execute(statement.having(sa.func.count() > 1)).first():
            raise RuntimeError(
                "Refusing downgrade: building-scoped values collide in legacy schema"
            )
    op.drop_index("ix_lanes_building_name", table_name="lanes")
    op.drop_index("ix_lanes_name", table_name="lanes")
    op.create_index("ix_lanes_name", "lanes", ["name"], unique=True)
    op.drop_index("uq_parking_transactions_active_plate", table_name="parking_transactions")
    with op.batch_alter_table("parking_transactions") as batch:
        batch.drop_constraint("uq_parking_building_key", type_="unique")
        batch.create_unique_constraint(
            "uq_parking_transactions_idempotency_key", ["idempotency_key"]
        )
    active_plate_index(["normalized_plate"])
