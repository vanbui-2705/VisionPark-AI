from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class VehicleType(str, Enum):
    CAR = "CAR"
    MOTORBIKE = "MOTORBIKE"
    BICYCLE = "BICYCLE"
    UNKNOWN = "UNKNOWN"


class BoundingBox(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def as_tuple(self) -> tuple[int, int, int, int]:
        return (self.x1, self.y1, self.x2, self.y2)


class ALPRResult(BaseModel):
    # ``plate_number`` and ``confidence`` remain for compatibility with the
    # existing service and frontend contracts.
    plate_number: str | None = None
    raw_plate: str | None = None
    normalized_plate: str | None = None
    bbox: BoundingBox | None = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    processing_time_ms: int
    requires_confirmation: bool
    model_version: str = "unknown"
    detection_id: str | None = None
    input_kind: str | None = None
    video_time_ms: int | None = None
    actor_id: str | None = None
    image_size_bytes: int | None = None
    detector_confidence: float | None = Field(None, ge=0.0, le=1.0)
    ocr_confidence: float | None = Field(None, ge=0.0, le=1.0)
    combined_confidence: float | None = Field(None, ge=0.0, le=1.0)
    quality_flags: list[str] = Field(default_factory=list)
    provider: str = "unknown"
    provider_status: str = "ready"
    detector_latency_ms: float | None = None
    ocr_latency_ms: float | None = None

    # Vehicle classification fields (SPEC-AI-01 / SPEC-AI-04)
    vehicle_type: str = VehicleType.UNKNOWN.value
    vehicle_confidence: float | None = Field(None, ge=0.0, le=1.0)
    bbox_vehicle: BoundingBox | None = None
    building_id: str | None = None


class ALPRHTTPResponse(BaseModel):
    raw_plate: str | None = None
    normalized_plate: str | None = None
    bbox: list[int]
    confidence: float
    latency_ms: float
    model_version: str
    requires_confirmation: bool = True
    detection_id: str | None = None
    input_kind: str | None = None
    video_time_ms: int | None = None
    actor_id: str | None = None

    # Compatibility fields used by the Station capture flow.
    raw_plate_number: str | None = None
    normalized_plate_number: str | None = None
    processing_time_ms: int | None = None
    detector_confidence: float | None = None
    ocr_confidence: float | None = None
    combined_confidence: float | None = None
    quality_flags: list[str] = Field(default_factory=list)
    provider: str = "unknown"
    provider_status: str = "ready"
    detector_latency_ms: float | None = None
    ocr_latency_ms: float | None = None

    # Vehicle classification fields (SPEC-AI-01 / SPEC-AI-04)
    vehicle_type: str = VehicleType.UNKNOWN.value
    vehicle_confidence: float | None = None
    bbox_vehicle: list[int] | None = None
    building_id: str | None = None


class FireSignalEvent(BaseModel):
    """Event schema representing a verified or candidate fire/smoke detection."""
    building_id: str | None = None
    camera_id: str
    zone_code: str | None = None
    event_type: str  # "FIRE" or "SMOKE"
    confidence: float = Field(..., ge=0.0, le=1.0)
    confirmed_frame_count: int = 1
    bbox: list[int]  # [x1, y1, x2, y2]
    evidence_image_path: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "DETECTED"  # "DETECTED", "VERIFYING", "CONFIRMED"
