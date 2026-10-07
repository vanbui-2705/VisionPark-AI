from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.alpr.utils import normalize_plate
from app.core.errors import AppError
from app.modules.alpr.models import Detection
from app.modules.alpr.schemas import DetectionConfirmRequest
from app.modules.audit_logs.service import log_action
from app.modules.checkin.models import ParkingTransaction
from app.modules.checkin.repository import DatabaseCheckInRepository
from app.modules.checkin.schemas import CheckInRequest
from app.modules.checkin.service import CheckInService
from app.modules.users.models import User


def confirm_detection(
    db: Session,
    detection: Detection,
    payload: DetectionConfirmRequest,
    operator: User,
    idempotency_key: str | None,
):
    plate = normalize_plate(payload.confirmed_plate)
    if not 3 <= len(plate) <= 50:
        raise AppError(status_code=422, code="INVALID_PLATE", message="Invalid normalized plate.")
    if payload.check_in:
        return CheckInService(DatabaseCheckInRepository(db), session=db).process_check_in(
            CheckInRequest(
                lane_id=detection.lane_id,
                license_plate=plate,
                detection_id=detection.id,
                source=payload.source,
                override_reason=payload.override_reason,
            ),
            operator=operator,
            idempotency_key=idempotency_key,
            confirm_detection=True,
        )
    if detection.is_confirmed and detection.confirmed_plate == plate:
        return detection
    linked = db.scalar(
        select(ParkingTransaction).where(ParkingTransaction.detection_id == detection.id)
    )
    if linked is not None:
        raise AppError(
            status_code=409,
            code="DETECTION_ALREADY_CHECKED_IN",
            message="A checked-in detection cannot be changed independently of its transaction.",
        )
    old_plate = detection.confirmed_plate or detection.raw_plate
    detection.is_confirmed = True
    detection.requires_confirmation = False
    detection.confirmed_plate = plate
    detection.confirmed_by_id = operator.id
    detection.confirmed_at = datetime.now(UTC)
    log_action(
        db=db,
        user_id=operator.id,
        action="CONFIRM_PLATE",
        entity_type="Detection",
        entity_id=str(detection.id),
        old_value={"plate": old_plate},
        new_value={"plate": plate},
    )
    db.commit()
    db.refresh(detection)
    return detection
