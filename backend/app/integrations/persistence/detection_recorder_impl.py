"""Persist a detection with the request session used to validate its lane."""

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.alpr.ports.detection_recorder import DetectionRecorder
from app.alpr.schema import ALPRResult, BoundingBox
from app.alpr.utils import normalize_plate
from app.core.errors import AppError
from app.modules.alpr.models import Detection
from app.modules.lanes.models import Lane


class DatabaseDetectionRecorder(DetectionRecorder):
    def __init__(self, session: Session):
        self.session = session

    def get_capture(self, capture_id: str, fingerprint: str) -> ALPRResult | None:
        detection = self.session.get(Detection, UUID(capture_id))
        if detection is None:
            return None
        if detection.capture_fingerprint != fingerprint:
            raise AppError(
                status_code=409,
                code="CAPTURE_ID_REUSED",
                message="Capture ID was used for a different image or lane.",
            )
        bbox = None
        if detection.bbox_x1 is not None:
            bbox = BoundingBox(
                x1=detection.bbox_x1,
                y1=detection.bbox_y1,
                x2=detection.bbox_x2,
                y2=detection.bbox_y2,
            )
        return ALPRResult(
            detection_id=str(detection.id),
            plate_number=detection.raw_plate,
            raw_plate=detection.raw_plate,
            normalized_plate=detection.normalized_plate,
            bbox=bbox,
            confidence=detection.confidence or 0,
            processing_time_ms=detection.processing_time_ms or 0,
            model_version=detection.model_version or "unknown",
            requires_confirmation=detection.requires_confirmation,
            input_kind=detection.input_kind,
            video_time_ms=detection.video_time_ms,
            actor_id=str(detection.actor_id) if detection.actor_id else None,
            image_size_bytes=detection.image_size_bytes,
            provider=detection.provider or "unknown",
            detector_confidence=detection.detector_confidence,
            ocr_confidence=detection.ocr_confidence,
            combined_confidence=detection.combined_confidence,
            quality_flags=detection.quality_flags or [],
            detector_latency_ms=detection.detector_latency_ms,
            ocr_latency_ms=detection.ocr_latency_ms,
        )

    def record_detection(
        self,
        lane_id: str,
        image_key: str,
        result: ALPRResult,
        *,
        capture_id: str | None = None,
        capture_fingerprint: str | None = None,
    ) -> str:
        bbox = result.bbox.as_tuple if result.bbox else (None, None, None, None)
        lane = self.session.get(Lane, UUID(lane_id))
        detection = Detection(
            **({"id": UUID(capture_id)} if capture_id else {}),
            lane_id=UUID(lane_id),
            image_key=image_key,
            image_content_type="image/png" if image_key.endswith(".png") else "image/jpeg",
            image_size_bytes=result.image_size_bytes,
            raw_plate=result.raw_plate or result.plate_number,
            normalized_plate=(
                result.normalized_plate or normalize_plate(result.raw_plate or result.plate_number)
                if result.raw_plate or result.plate_number
                else None
            ),
            bbox_x1=bbox[0],
            bbox_y1=bbox[1],
            bbox_x2=bbox[2],
            bbox_y2=bbox[3],
            confidence=result.confidence,
            processing_time_ms=result.processing_time_ms,
            model_version=result.model_version,
            capture_fingerprint=capture_fingerprint,
            requires_confirmation=result.requires_confirmation,
            input_kind=result.input_kind,
            video_time_ms=result.video_time_ms,
            actor_id=UUID(result.actor_id) if result.actor_id else None,
            provider=result.provider,
            detector_confidence=result.detector_confidence,
            ocr_confidence=result.ocr_confidence,
            combined_confidence=result.combined_confidence,
            quality_flags=result.quality_flags,
            detector_latency_ms=result.detector_latency_ms,
            ocr_latency_ms=result.ocr_latency_ms,
            lane_name_snapshot=lane.name,
            direction_snapshot=lane.direction.value,
        )
        self.session.add(detection)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            if capture_id and self.get_capture(capture_id, capture_fingerprint):
                # The losing request must remove its own redundant stored image.
                raise AppError(
                    status_code=409,
                    code="CAPTURE_RETRY",
                    message="Capture already exists; retry the same request.",
                ) from None
            raise
        return str(detection.id)
