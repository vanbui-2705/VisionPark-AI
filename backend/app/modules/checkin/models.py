from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TransactionStatus(StrEnum):
    PARKED = "PARKED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class CheckInSource(StrEnum):
    AI_ACCEPTED = "AI_ACCEPTED"
    OPERATOR_CORRECTED = "OPERATOR_CORRECTED"
    MANUAL_ENTRY = "MANUAL_ENTRY"
    STATION_AUTO = "STATION_AUTO"
    OPERATOR_MANUAL = "OPERATOR_MANUAL"


class ParkingTransaction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "parking_transactions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PARKED', 'COMPLETED', 'CANCELLED')", name="ck_parking_transactions_status"
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_parking_transactions_confidence",
        ),
        CheckConstraint(
            "length(idempotency_key) BETWEEN 1 AND 255",
            name="ck_parking_transactions_idempotency_key",
        ),
        CheckConstraint(
            "length(request_fingerprint) = 64", name="ck_parking_transactions_fingerprint"
        ),
        Index(
            "uq_parking_transactions_active_plate",
            "normalized_plate",
            unique=True,
            sqlite_where=text("status = 'PARKED'"),
            postgresql_where=text("status = 'PARKED'"),
        ),
    )

    license_plate: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    normalized_plate: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    original_ai_plate: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=TransactionStatus.PARKED
    )
    lane_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("lanes.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    detection_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("detections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    check_in_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    check_in_operator_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    operator_snapshot_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lane_snapshot_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lane_snapshot_direction: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    lane_name_snapshot: Mapped[str | None] = mapped_column(String(120), nullable=True)
    operator_name_snapshot: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_manual_override: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)

    lane = relationship("Lane")
    detection = relationship("Detection")
    check_in_operator = relationship("User")
