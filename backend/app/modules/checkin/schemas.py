from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CheckInRequest(BaseModel):
    lane_id: UUID
    plate_number: str = Field(
        ..., min_length=3, description="Biển số xe đã được nhận diện hoặc nhập tay"
    )
    idempotency_key: str = Field(..., description="Mã chống request lặp (double-click)")
    detection_id: UUID | None = None  # ID từ ALPR nếu có


class CheckInResponse(BaseModel):
    transaction_id: UUID
    plate_number: str
    lane_id: UUID
    check_in_time: datetime
    status: str = "PARKED"
