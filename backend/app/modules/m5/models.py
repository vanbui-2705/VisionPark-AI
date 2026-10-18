
"""M5 storage models; operational workflows are implemented separately."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.buildings.models import BuildingOwnedMixin


class DailyStat(BuildingOwnedMixin, UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "daily_stats"

    __table_args__ = (
        UniqueConstraint(
            "building_id",
            "stat_date",
            "vehicle_type",
            name="uq_daily_stats_building_date_type",
        ),
        CheckConstraint(
            "entries >= 0 AND exits >= 0 AND revenue >= 0 AND occupancy_peak >= 0",
            name="ck_daily_stats_nonnegative",
        ),
        Index("ix_daily_stats_date", "stat_date"),
    )

    stat_date: Mapped[date] = mapped_column(Date, nullable=False)
    vehicle_type: Mapped[str] = mapped_column(String(40), nullable=False)

    entries: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )

    exits: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )

    revenue: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=0,
        server_default="0",
        nullable=False,
    )

    occupancy_peak: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )


class Device(BuildingOwnedMixin, UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "devices"

    __table_args__ = (
        UniqueConstraint(
            "building_id",
            "code",
            name="uq_devices_building_code",
        ),
        CheckConstraint(
            "status IN ('UNKNOWN', 'ONLINE', 'DEGRADED', 'OFFLINE')",
            name="ck_devices_status",
        ),
    )

    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    device_type: Mapped[str] = mapped_column(String(40), nullable=False)

    status: Mapped[str] = mapped_column(
        String(20),
        default="UNKNOWN",
        server_default="UNKNOWN",
        nullable=False,
    )

    last_heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    metadata_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        server_default="{}",
        nullable=False,
    )
