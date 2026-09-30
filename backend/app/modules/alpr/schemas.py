from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


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

    created_at: datetime

    class Config:
        from_attributes = True


class DetectionConfirmRequest(BaseModel):
    """Schema nhận dữ liệu khi Operator bấm xác nhận sửa biển số"""

    confirmed_plate: str
