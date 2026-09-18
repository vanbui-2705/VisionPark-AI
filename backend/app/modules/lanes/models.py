from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import String, Enum
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class LaneDirection(str, enum.Enum):
    IN = "IN"
    OUT = "OUT"


class Lane(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "lanes"

    name: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    direction: Mapped[LaneDirection] = mapped_column(Enum(LaneDirection), nullable=False)
    video_source: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)