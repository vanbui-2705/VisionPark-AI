from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    event,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UUIDPrimaryKeyMixin
from app.modules.checkin.lifecycle_models import AppendOnlyModelError


class ParkingCounter(Base, UUIDPrimaryKeyMixin):
    """Bộ đếm số xe đang đỗ trong bãi theo từng loại xe (mục 4.4 nghiepvu.md)."""

    __tablename__ = "parking_counters"
    __table_args__ = (
        UniqueConstraint(
            "building_id", "vehicle_type", name="uq_parking_counters_building_vehicle"
        ),
    )

    building_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    vehicle_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    occupied: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class CounterEvent(Base, UUIDPrimaryKeyMixin):
    """Nhật ký thay đổi bộ đếm append-only (mục 4.4 & 4.10 nghiepvu.md)."""

    __tablename__ = "counter_events"
    __table_args__ = (Index("ix_counter_events_building_occurred", "building_id", "occurred_at"),)

    building_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    counter_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    vehicle_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    session_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    reason: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(32), default="SYSTEM", nullable=False)
    actor_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


@event.listens_for(CounterEvent, "before_update")
def _prevent_counter_event_update(mapper, connection, target):
    raise AppendOnlyModelError("CounterEvent is append-only: updates are strictly forbidden.")


@event.listens_for(CounterEvent, "before_delete")
def _prevent_counter_event_delete(mapper, connection, target):
    raise AppendOnlyModelError("CounterEvent is append-only: deletions are strictly forbidden.")
