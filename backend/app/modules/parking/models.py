import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import String, Float, Text, Boolean, DateTime, ForeignKey, Uuid, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class TransactionStatus(str, enum.Enum):
    PARKED = "PARKED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class CheckInSource(str, enum.Enum):
    STATION_AUTO = "STATION_AUTO"
    OPERATOR_MANUAL = "OPERATOR_MANUAL"


class ParkingTransaction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "parking_transactions"

    license_plate: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    original_ai_plate: Mapped[str | None] = mapped_column(String(50), nullable=True)
    normalized_plate: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[TransactionStatus] = mapped_column(Enum(TransactionStatus), nullable=False, index=True, default=TransactionStatus.PARKED)

    lane_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("lanes.id", ondelete="RESTRICT"), nullable=False, index=True)
    lane_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    detection_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("detections.id", ondelete="SET NULL"), nullable=True, index=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    check_in_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    check_in_operator_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    source: Mapped[CheckInSource] = mapped_column(Enum(CheckInSource), nullable=False)
    is_manual_override: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    lane = relationship("Lane", lazy="joined")
