from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.modules.parking.models import ParkingTransaction, TransactionStatus, CheckInSource
from app.modules.parking.repository import get_transaction
from app.modules.users.models import User
from sqlalchemy import select
from app.modules.lanes.models import Lane


def create_check_in(db: Session, *, lane_id: UUID, license_plate: str, operator: User, source: CheckInSource = CheckInSource.OPERATOR_MANUAL, detection_id: UUID | None = None, confidence: float | None = None, override_reason: str | None = None) -> ParkingTransaction:
    lane = db.scalar(select(Lane).where(Lane.id == lane_id))
    if not lane:
        raise AppError(status_code=404, code="NOT_FOUND", message="Lane not found")
    normalized = license_plate.replace("-", "").replace(".", "").replace(" ", "").strip().upper()
    tx = ParkingTransaction(
        license_plate=license_plate.strip().upper(),
        original_ai_plate=license_plate if source == CheckInSource.OPERATOR_MANUAL else None,
        normalized_plate=normalized,
        status=TransactionStatus.PARKED,
        lane_id=lane.id,
        lane_name=lane.name,
        detection_id=detection_id,
        confidence=confidence,
        check_in_time=datetime.now(timezone.utc),
        check_in_operator_id=operator.id,
        source=source,
        is_manual_override=source == CheckInSource.OPERATOR_MANUAL,
        notes=override_reason,
    )
    db.add(tx)
    db.flush()
    return tx
