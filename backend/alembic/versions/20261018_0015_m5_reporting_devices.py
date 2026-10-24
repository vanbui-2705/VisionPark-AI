"""M5 daily statistics, device monitoring and device storage."""
import sqlalchemy as sa
from alembic import op

revision = "20261018_0015"
down_revision = "20261012_0014"
branch_labels = None
depends_on = None


def _base():
    return [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("building_id", sa.Uuid(), sa.ForeignKey("buildings.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade():
    op.create_table("daily_stats", *_base(),
        sa.Column("stat_date", sa.Date(), nullable=False),
        sa.Column("vehicle_type", sa.String(40), nullable=False),
        sa.Column("entries", sa.Integer(), server_default="0", nullable=False),
        sa.Column("exits", sa.Integer(), server_default="0", nullable=False),
        sa.Column("revenue", sa.Numeric(18, 2), server_default="0", nullable=False),
        sa.Column("occupancy_peak", sa.Integer(), server_default="0", nullable=False),
        sa.UniqueConstraint("building_id", "stat_date", "vehicle_type", name="uq_daily_stats_building_date_type"),
        sa.CheckConstraint("entries >= 0 AND exits >= 0 AND revenue >= 0 AND occupancy_peak >= 0", name="ck_daily_stats_nonnegative"))
    op.create_index("ix_daily_stats_date", "daily_stats", ["stat_date"])
    op.create_index("ix_daily_stats_building_id", "daily_stats", ["building_id"])
    op.create_table("devices", *_base(),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("device_type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(20), server_default="UNKNOWN", nullable=False),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True)),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.UniqueConstraint("building_id", "code", name="uq_devices_building_code"),
        sa.CheckConstraint("status IN ('UNKNOWN', 'ONLINE', 'DEGRADED', 'OFFLINE')", name="ck_devices_status"))
    op.create_index("ix_devices_building_id", "devices", ["building_id"])


def downgrade():
    op.drop_table("devices")
    op.drop_table("daily_stats")
