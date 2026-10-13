import enum

from sqlalchemy import JSON, Enum, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.buildings.models import BuildingOwnedMixin


class LaneDirection(enum.StrEnum):
    IN = "IN"
    OUT = "OUT"


class AllowedVehicleType(enum.StrEnum):
    ALL = "ALL"
    CAR = "CAR"
    MOTORBIKE = "MOTORBIKE"
    BICYCLE = "BICYCLE"


class Lane(BuildingOwnedMixin, Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "lanes"
    __table_args__ = (Index("ix_lanes_building_name", "building_id", "name", unique=True),)

    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    direction: Mapped[LaneDirection] = mapped_column(Enum(LaneDirection), nullable=False)
    video_source: Mapped[str] = mapped_column(String(512), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    allowed_vehicle_types: Mapped[list[str]] = mapped_column(
        JSON,
        default=lambda: ["CAR", "MOTORBIKE", "BICYCLE"],
        server_default='["CAR", "MOTORBIKE", "BICYCLE"]',
        nullable=False,
    )
    camera: Mapped[str | None] = mapped_column(String(255), nullable=True)
    barrier: Mapped[str | None] = mapped_column(String(255), nullable=True)
