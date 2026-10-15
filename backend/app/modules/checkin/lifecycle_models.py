from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    String,
    Uuid,
    event,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDPrimaryKeyMixin


class LifecycleEventType(StrEnum):
    GATE_IN_DETECTED = "GATE_IN_DETECTED"
    PLATE_READ = "PLATE_READ"
    VEHICLE_TYPE_CLASSIFIED = "VEHICLE_TYPE_CLASSIFIED"
    OPERATOR_CORRECTED = "OPERATOR_CORRECTED"
    ACCESS_DECIDED = "ACCESS_DECIDED"
    TICKET_ISSUED = "TICKET_ISSUED"
    BARRIER_OPENED_IN = "BARRIER_OPENED_IN"
    CHECKED_IN = "CHECKED_IN"
    OVERTIME_FLAGGED = "OVERTIME_FLAGGED"
    INCIDENT_NOTIFIED = "INCIDENT_NOTIFIED"
    GATE_OUT_DETECTED = "GATE_OUT_DETECTED"
    SESSION_MATCHED = "SESSION_MATCHED"
    FEE_CALCULATED = "FEE_CALCULATED"
    INVOICE_CREATED = "INVOICE_CREATED"
    PAYMENT_RECEIVED = "PAYMENT_RECEIVED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    BARRIER_OPENED_OUT = "BARRIER_OPENED_OUT"
    EXIT_CONFIRMED = "EXIT_CONFIRMED"
    COMPLETED = "COMPLETED"
    OVERRIDE_APPLIED = "OVERRIDE_APPLIED"
    MANUAL_SESSION_CREATED = "MANUAL_SESSION_CREATED"
    SESSION_REOPENED = "SESSION_REOPENED"
    CANCELLED = "CANCELLED"
    COUNTER_ADJUSTED = "COUNTER_ADJUSTED"


class ActorType(StrEnum):
    AI = "AI"
    OPERATOR = "OPERATOR"
    SYSTEM = "SYSTEM"
    CUSTOMER = "CUSTOMER"


class LifecycleEvent(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "lifecycle_events"
    __table_args__ = (
        Index("ix_lifecycle_events_building_occurred", "building_id", "occurred_at"),
        Index("ix_lifecycle_events_session_occurred", "session_id", "occurred_at"),
    )

    session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("parking_transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # TODO: Chờ module M1 tạo bảng buildings để bổ sung ForeignKey("buildings.id")
    building_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    lane_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("lanes.id", ondelete="SET NULL"), nullable=True
    )
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    image_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)

    session = relationship("ParkingTransaction", foreign_keys=[session_id])
    lane = relationship("Lane", foreign_keys=[lane_id])


class AppendOnlyModelError(Exception):
    """Raised when an update or delete operation is attempted on an append-only model."""


@event.listens_for(LifecycleEvent, "before_update")
def _prevent_lifecycle_update(mapper, connection, target):
    raise AppendOnlyModelError("LifecycleEvent is append-only: updates are strictly forbidden.")


@event.listens_for(LifecycleEvent, "before_delete")
def _prevent_lifecycle_delete(mapper, connection, target):
    raise AppendOnlyModelError("LifecycleEvent is append-only: deletions are strictly forbidden.")
