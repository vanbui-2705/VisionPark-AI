from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class DetectionResponse(BaseModel):
    """Schema trả về thông tin lịch sử nhận diện cho Frontend"""
    id: UUID
    lane_id: str
    image_key: str
    raw_plate: Optional[str] = None
    normalized_plate: Optional[str] = None
    confidence: Optional[float] = None
    
    # Các trường liên quan đến xác nhận (Confirmation)
    requires_confirmation: bool
    is_confirmed: bool
    confirmed_plate: Optional[str] = None
    
    created_at: datetime

    class Config:
        from_attributes = True


class DetectionConfirmRequest(BaseModel):
    """Schema nhận dữ liệu khi Operator bấm xác nhận sửa biển số"""
    confirmed_plate: str