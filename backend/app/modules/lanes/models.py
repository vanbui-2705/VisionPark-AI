import enum
from uuid import UUID

from sqlalchemy import Enum, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class LaneDirection(enum.StrEnum):
    IN = "IN"
    OUT = "OUT"


class AllowedVehicleType(enum.StrEnum):
    ALL = "ALL"
    CAR = "CAR"
    MOTORBIKE = "MOTORBIKE"
    BICYCLE = "BICYCLE"


class Lane(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "lanes"

    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    direction: Mapped[LaneDirection] = mapped_column(Enum(LaneDirection), nullable=False)
    video_source: Mapped[str] = mapped_column(String(512), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)

    allowed_vehicle_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=AllowedVehicleType.ALL
    )

    # TODO: Chờ module M5 tạo bảng devices để liên kết ForeignKey("devices.id")
    camera_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    barrier_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # TODO: Chờ module M1 tạo bảng buildings để bổ sung ForeignKey("buildings.id")
    building_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True, index=True
    )
