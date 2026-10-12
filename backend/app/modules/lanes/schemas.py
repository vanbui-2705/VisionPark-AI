from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .models import AllowedVehicleType, LaneDirection


# 1. DTO cho trường hợp TẠO MỚI
class LaneCreate(BaseModel):
    name: str = Field(..., description="Tên của làn xe, ví dụ: LANE_IN_01")
    direction: LaneDirection
    video_source: str = Field(..., description="Đường dẫn camera RTSP hoặc file video")
    is_active: bool | None = True
    allowed_vehicle_type: AllowedVehicleType | str = AllowedVehicleType.ALL
    camera_id: str | None = None
    barrier_id: str | None = None
    building_id: UUID | None = None


# 2. DTO cho trường hợp CẬP NHẬT
class LaneUpdate(BaseModel):
    name: str | None = None
    direction: LaneDirection | None = None
    video_source: str | None = None
    is_active: bool | None = None
    allowed_vehicle_type: AllowedVehicleType | str | None = None
    camera_id: str | None = None
    barrier_id: str | None = None
    building_id: UUID | None = None


# 3. DTO TRẢ VỀ
class LaneResponse(BaseModel):
    id: UUID
    name: str
    direction: LaneDirection
    video_source: str
    is_active: bool
    allowed_vehicle_type: str = "ALL"
    camera_id: str | None = None
    barrier_id: str | None = None
    building_id: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
