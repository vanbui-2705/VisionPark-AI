import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UUIDPrimaryKeyMixin


class BarrierAction(enum.StrEnum):
    OPEN = "OPEN"
    CLOSE = "CLOSE"


class BarrierTriggerReason(enum.StrEnum):
    NORMAL = "NORMAL"
    OVERRIDE = "OVERRIDE"
    EMERGENCY = "EMERGENCY"
    VEHICLE_PASSED = "VEHICLE_PASSED"
    TIMEOUT_AUTO_CLOSE = "TIMEOUT_AUTO_CLOSE"
    MANUAL_CLOSE = "MANUAL_CLOSE"


class BarrierStatus(enum.StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CLOSED_TIMEOUT = "CLOSED_TIMEOUT"
    FAILED = "FAILED"


class BarrierEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "barrier_events"

    building_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("buildings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    lane_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("lanes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    barrier_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    trigger_reason: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    operator_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    session_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("parking_transactions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(
        Integer,
        default=15,
        server_default="15",
        nullable=False,
    )
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
