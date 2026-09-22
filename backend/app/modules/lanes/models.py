import enum

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class LaneDirection(enum.StrEnum):
    IN = "IN"
    OUT = "OUT"


class Lane(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "lanes"

    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    direction: Mapped[LaneDirection] = mapped_column(Enum(LaneDirection), nullable=False)
    video_source: Mapped[str] = mapped_column(String(512), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
