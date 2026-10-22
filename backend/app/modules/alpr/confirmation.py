import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

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


def save_hard_sample(
    detection: Detection,
    confirmed_plate: str,
    confirmed_vehicle_type: str | None,
    operator: User,
    reason: str | None,
) -> None:
    """SPEC-AI-06: Chu trình lưu mẫu khó (Hard Sample Mining Loop) để cải thiện model."""
    try:
        today_str = datetime.now(UTC).strftime("%Y-%m-%d")
        hard_samples_dir = Path("var/hard_samples") / today_str / str(detection.id)
        hard_samples_dir.mkdir(parents=True, exist_ok=True)

        if detection.image_key and detection.lane_id:
            src_image = Path("var/media") / str(detection.lane_id) / detection.image_key
            if not src_image.exists():
                src_image = Path("var/media") / detection.image_key
            if src_image.exists():
                shutil.copy2(src_image, hard_samples_dir / f"image{src_image.suffix}")

        metadata = {
            "detection_id": str(detection.id),
            "lane_id": str(detection.lane_id),
            "original_prediction": {
                "raw_plate": detection.raw_plate,
                "normalized_plate": detection.normalized_plate,
                "confidence": detection.confidence,
                "vehicle_type": detection.vehicle_type,
                "vehicle_confidence": detection.vehicle_confidence,
                "model_version": detection.model_version,
            },
            "operator_correction": {
                "confirmed_plate": confirmed_plate,
                "confirmed_vehicle_type": confirmed_vehicle_type or detection.vehicle_type,
                "operator_id": str(operator.id),
                "confirmed_at": datetime.now(UTC).isoformat(),
                "override_reason": reason,
            },
        }
        with open(hard_samples_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    except Exception:
        # Hard sample mining is best-effort and must not fail the user transaction
        pass


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
    old_vtype = detection.vehicle_type
    new_vtype = payload.confirmed_vehicle_type or old_vtype

    detection.is_confirmed = True
    detection.requires_confirmation = False
    detection.confirmed_plate = plate
    if payload.confirmed_vehicle_type:
        detection.vehicle_type = payload.confirmed_vehicle_type
    detection.confirmed_by_id = operator.id
    detection.confirmed_at = datetime.now(UTC)

    # Trigger hard sample mining when human corrects prediction
    if old_plate != plate or (payload.confirmed_vehicle_type and payload.confirmed_vehicle_type != old_vtype):
        save_hard_sample(
            detection,
            plate,
            payload.confirmed_vehicle_type,
            operator,
            payload.override_reason,
        )

    log_action(
        db=db,
        user_id=operator.id,
        action="CONFIRM_PLATE",
        entity_type="Detection",
        entity_id=str(detection.id),
        old_value={"plate": old_plate, "vehicle_type": old_vtype},
        new_value={"plate": plate, "vehicle_type": new_vtype},
    )
    db.commit()
    db.refresh(detection)
    return detection
