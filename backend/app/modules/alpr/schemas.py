from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.checkin.models import CheckInSource


class DetectionResponse(BaseModel):
    """Schema trả về thông tin lịch sử nhận diện cho Frontend"""

    id: UUID
    lane_id: UUID
    image_key: str
    raw_plate: str | None = None
    normalized_plate: str | None = None
    confidence: float | None = None

    # Các trường liên quan đến xác nhận (Confirmation)
    requires_confirmation: bool = False
    is_confirmed: bool = False
    confirmed_plate: str | None = None
    confirmed_by_id: UUID | None = None
    confirmed_at: datetime | None = None
    processing_time_ms: int | None = None
    model_version: str | None = None
    bbox_x1: int | None = None
    bbox_y1: int | None = None
    bbox_x2: int | None = None
    bbox_y2: int | None = None

    input_kind: str | None = None
    video_time_ms: int | None = None
    provider: str | None = None
    detector_confidence: float | None = None
    ocr_confidence: float | None = None
    combined_confidence: float | None = None
    quality_flags: list[str] | None = None
    actor_id: UUID | None = None
    lane_name: str | None = None
    direction: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DetectionConfirmRequest(BaseModel):
    """Schema nhận dữ liệu khi Operator bấm xác nhận sửa biển số"""

    confirmed_plate: str = Field(min_length=3, max_length=50)
    check_in: bool = False
    source: CheckInSource | None = None
    override_reason: str | None = Field(None, max_length=500)
