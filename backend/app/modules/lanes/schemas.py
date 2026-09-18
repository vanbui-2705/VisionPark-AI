from uuid import UUID
from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from .models import LaneDirection


# 1. DTO cho trường hợp TẠO MỚI
class LaneCreate(BaseModel):
    name: str = Field(..., description="Tên của làn xe, ví dụ: LANE_IN_01")
    direction: LaneDirection
    video_source: str = Field(..., description="Đường dẫn camera RTSP hoặc file video")
    is_active: Optional[bool] = True


# 2. DTO cho trường hợp CẬP NHẬT
class LaneUpdate(BaseModel):
    name: Optional[str] = None
    direction: Optional[LaneDirection] = None
    video_source: Optional[str] = None
    is_active: Optional[bool] = None


# 3. DTO TRẢ VỀ
class LaneResponse(BaseModel):
    id: UUID
    name: str
    direction: LaneDirection
    video_source: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True