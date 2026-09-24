"""Persist a detection with the request session used to validate its lane."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.alpr.ports.detection_recorder import DetectionRecorder
from app.alpr.schema import ALPRResult
from app.alpr.utils import normalize_plate
from app.modules.alpr.models import Detection


class DatabaseDetectionRecorder(DetectionRecorder):
    def __init__(self, session: Session):
        self.session = session

    def record_detection(self, lane_id: str, image_key: str, result: ALPRResult) -> str:
        bbox = result.bbox.as_tuple if result.bbox else (None, None, None, None)
        detection = Detection(
            lane_id=UUID(lane_id),
            image_key=image_key,
            raw_plate=result.plate_number,
            normalized_plate=normalize_plate(result.plate_number) if result.plate_number else None,
            bbox_x1=bbox[0],
            bbox_y1=bbox[1],
            bbox_x2=bbox[2],
            bbox_y2=bbox[3],
            confidence=result.confidence,
            processing_time_ms=result.processing_time_ms,
        )
        self.session.add(detection)
        self.session.commit()
        return str(detection.id)
