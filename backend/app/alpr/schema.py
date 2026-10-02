from pydantic import BaseModel, Field


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
    detector_confidence: float | None = Field(None, ge=0.0, le=1.0)
    ocr_confidence: float | None = Field(None, ge=0.0, le=1.0)
    combined_confidence: float | None = Field(None, ge=0.0, le=1.0)
    quality_flags: list[str] = Field(default_factory=list)
    provider: str = "unknown"
    provider_status: str = "ready"


class ALPRHTTPResponse(BaseModel):
    raw_plate: str | None = None
    normalized_plate: str | None = None
    bbox: list[int]
    confidence: float
    latency_ms: float
    model_version: str
    requires_confirmation: bool = True
    detection_id: str | None = None

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
