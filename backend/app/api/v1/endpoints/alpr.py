from typing import Annotated
from uuid import UUID

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.alpr.errors import ALPRNotReadyError, ALPRProcessingError
from app.alpr.schema import ALPRHTTPResponse
from app.alpr.service import ALPRApplicationService
from app.alpr.utils import normalize_plate
from app.api.v1.endpoints.health import liveness, readiness
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.di_container import get_alpr_service
from app.modules.auth.dependencies import require_roles
from app.modules.users.schemas import RoleName

router = APIRouter()


@router.post(
    "/detections",
    response_model=ALPRHTTPResponse,
    dependencies=[Depends(require_roles(RoleName.ADMIN, RoleName.OPERATOR))],
)
def create_detection(
    lane_id: Annotated[UUID, Form()],
    image: Annotated[UploadFile, File()],
    settings: Annotated[Settings, Depends(get_settings)],
    alpr_service: Annotated[ALPRApplicationService, Depends(get_alpr_service)],
):
    if image.content_type not in {"image/jpeg", "image/png"}:
        raise AppError("VALIDATION_ERROR", "Only JPEG and PNG are supported.", 422)
    image_bytes = image.file.read(settings.upload_max_bytes + 1)
    if len(image_bytes) > settings.upload_max_bytes:
        raise AppError("VALIDATION_ERROR", "Image exceeds UPLOAD_MAX_BYTES.", 422)
    try:
        matrix = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    except cv2.error:
        matrix = None
    if matrix is None:
        raise AppError("VALIDATION_ERROR", "Image cannot be decoded.", 422)
    try:
        result = alpr_service.process_detection(image_bytes, str(lane_id))
    except ValueError as exc:
        raise AppError("NOT_FOUND", "Lane does not exist or is inactive.", 404) from exc
    except (ALPRNotReadyError, ALPRProcessingError, TimeoutError) as exc:
        raise AppError("DEPENDENCY_UNAVAILABLE", "ALPR runtime is unavailable.", 503) from exc
    return ALPRHTTPResponse(
        raw_plate=result.plate_number,
        normalized_plate=normalize_plate(result.plate_number) if result.plate_number else None,
        bbox=list(result.bbox.as_tuple) if result.bbox else [0, 0, 0, 0],
        confidence=result.confidence,
        latency_ms=result.processing_time_ms,
        model_version=alpr_service.runtime.version,
    )


# Preserve the existing URLs while sharing the authoritative DB/runtime probe.
router.add_api_route("/health/live", liveness, methods=["GET"])
router.add_api_route("/health/ready", readiness, methods=["GET"])
