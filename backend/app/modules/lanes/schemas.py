from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.lot_settings.schemas import VehicleType

from .models import LaneDirection


# 1. DTO cho trường hợp TẠO MỚI
class LaneCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., description="Tên của làn xe, ví dụ: LANE_IN_01")
    direction: LaneDirection
    video_source: str = Field(..., description="Đường dẫn camera RTSP hoặc file video")
    is_active: bool | None = True
    allowed_vehicle_types: list[VehicleType] = Field(
        default_factory=lambda: list(VehicleType), min_length=1
    )
    camera: str | None = Field(default=None, max_length=255)
    barrier: str | None = Field(default=None, max_length=255)


# 2. DTO cho trường hợp CẬP NHẬT
class LaneUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = None
    direction: LaneDirection | None = None
    video_source: str | None = None
    is_active: bool | None = None
    allowed_vehicle_types: list[VehicleType] | None = Field(default=None, min_length=1)
    camera: str | None = Field(default=None, max_length=255)
    barrier: str | None = Field(default=None, max_length=255)


# 3. DTO TRẢ VỀ
class LaneResponse(BaseModel):
    id: UUID
    name: str
    direction: LaneDirection
    video_source: str
    is_active: bool
    allowed_vehicle_types: list[VehicleType]
    camera: str | None
    barrier: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
