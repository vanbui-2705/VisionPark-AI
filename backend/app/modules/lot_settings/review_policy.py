from uuid import UUID

from app.alpr.utils import normalize_plate
from app.core.errors import AppError
from app.modules.lanes.models import Lane
from app.modules.lot_settings.service import configuration, load_lot


def apply_plate_review_policy(db, lane_id, result):
    lane = db.get(Lane, UUID(lane_id))
    if lane is None:
        raise AppError(status_code=404, code="NOT_FOUND", message="Lane not found.")
    building, lot = load_lot(db, lane.building_id)
    threshold = configuration(building, lot).ai.plate_confidence
    plate = normalize_plate(
        result.normalized_plate or result.raw_plate or result.plate_number or ""
    )
    confidence = (
        result.combined_confidence if result.combined_confidence is not None else result.confidence
    )
    review = (
        threshold is None
        or confidence < threshold
        or not 3 <= len(plate) <= 50
        or result.bbox is None
        or bool(result.quality_flags)
    )
    return result.model_copy(update={"requires_confirmation": review})
