import enum

from sqlalchemy import Enum, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.buildings.models import BuildingOwnedMixin


class LaneDirection(enum.StrEnum):
    IN = "IN"
    OUT = "OUT"


class Lane(BuildingOwnedMixin, Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "lanes"
    __table_args__ = (Index("ix_lanes_building_name", "building_id", "name", unique=True),)

    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    direction: Mapped[LaneDirection] = mapped_column(Enum(LaneDirection), nullable=False)
    video_source: Mapped[str] = mapped_column(String(512), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
