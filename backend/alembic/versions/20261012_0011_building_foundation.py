"""VAN-59: add buildings and backfill legacy operational ownership."""

from uuid import UUID, uuid4

import sqlalchemy as sa
from alembic import op

revision = "20261012_0011"
down_revision = "b9c0f377213e"
branch_labels = None
depends_on = None

DEFAULT_ID = UUID("00000000-0000-0000-0000-000000000001")
OWNED_TABLES = (
    "lanes",
    "detections",
    "parking_transactions",
    "audit_logs",
    "notifications",
    "error_events",
)


def identity_columns():
    return [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    ]


def upgrade():
    buildings = op.create_table(
        "buildings",
        *identity_columns(),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("address", sa.String(512), nullable=False, server_default=""),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="Asia/Ho_Chi_Minh"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    lots = op.create_table(
        "parking_lots",
        *identity_columns(),
        sa.Column(
            "building_id",
            sa.Uuid(),
            sa.ForeignKey("buildings.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column("settings", sa.JSON(), nullable=False, server_default="{}"),
    )
    memberships = op.create_table(
        "user_buildings",
        *identity_columns(),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "building_id",
            sa.Uuid(),
            sa.ForeignKey("buildings.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "building_id", name="uq_user_buildings_membership"),
    )
    for column in ("user_id", "building_id"):
        op.create_index(f"ix_user_buildings_{column}", "user_buildings", [column])
    connection = op.get_bind()
    connection.execute(
        buildings.insert().values(
            id=DEFAULT_ID,
            code="DEFAULT",
            name="Legacy parking building",
        )
    )
    connection.execute(lots.insert().values(id=uuid4(), building_id=DEFAULT_ID, settings={}))
    users = sa.table("users", sa.column("id", sa.Uuid()))
    for user_id in connection.execute(sa.select(users.c.id)).scalars():
        connection.execute(
            memberships.insert().values(
                id=uuid4(),
                user_id=user_id,
                building_id=DEFAULT_ID,
            )
        )

    # Expand nullable, backfill every legacy row, then enforce ownership.
    # A DB default also preserves writes from the previous application version.
    for name in OWNED_TABLES:
        op.add_column(
            name, sa.Column("building_id", sa.Uuid(), nullable=True, server_default=DEFAULT_ID.hex)
        )
        table = sa.table(name, sa.column("building_id", sa.Uuid()))
        connection.execute(
            table.update().where(table.c.building_id.is_(None)).values(building_id=DEFAULT_ID)
        )
        with op.batch_alter_table(name) as batch:
            batch.alter_column(
                "building_id",
                existing_type=sa.Uuid(),
                nullable=False,
                existing_server_default=DEFAULT_ID.hex,
            )
            batch.create_foreign_key(
                f"fk_{name}_building_id", "buildings", ["building_id"], ["id"], ondelete="RESTRICT"
            )
            batch.create_index(f"ix_{name}_building_id", ["building_id"])


def downgrade():
    # A legacy application cannot preserve tenant isolation for multiple buildings.
    buildings = sa.table("buildings", sa.column("id", sa.Uuid()))
    if op.get_bind().execute(sa.select(buildings.c.id).where(buildings.c.id != DEFAULT_ID)).first():
        raise RuntimeError("Refusing downgrade while non-default buildings exist")
    for name in reversed(OWNED_TABLES):
        with op.batch_alter_table(name) as batch:
            batch.drop_index(f"ix_{name}_building_id")
            batch.drop_constraint(f"fk_{name}_building_id", type_="foreignkey")
            batch.drop_column("building_id")
    op.drop_table("user_buildings")
    op.drop_table("parking_lots")
    op.drop_table("buildings")
