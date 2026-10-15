from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SessionLifecycleFilter(BaseModel):
    """Bộ lọc cho trang Vòng đời xe (BR-4.8)."""

    model_config = ConfigDict(extra="ignore")

    license_plate: str | None = None
    ticket_code: str | None = None
    from_time: datetime | None = None
    to_time: datetime | None = None
    vehicle_type: str | None = None
    ticket_kind: str | None = None
    status: str | None = None
    lane_id: UUID | None = None
    has_exception: bool | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=10000)


class SessionListItemResponse(BaseModel):
    """Một dòng trong bảng lượt (phân trang)."""

    id: UUID
    building_id: UUID
    license_plate: str | None = None
    normalized_plate: str | None = None
    ticket_code: str | None = None
    vehicle_type: str
    ticket_kind: str
    check_in_time: datetime
    exit_time: datetime | None = None
    duration_minutes: int
    fee: float
    status: str
    has_exception: bool
    in_lane_name: str | None = None
    exit_lane_name: str | None = None


class SessionListPaginatedResponse(BaseModel):
    """Kết quả phân trang danh sách lượt gửi xe."""

    items: list[SessionListItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class LifecycleTimelineEvent(BaseModel):
    """Một mắt xích sự kiện trong dòng thời gian của lượt xe (nhật ký vòng đời)."""

    id: UUID
    event_type: str
    occurred_at: datetime
    actor_type: str
    actor_id: UUID | None = None
    actor_name: str | None = None
    lane_id: UUID | None = None
    lane_name: str | None = None
    details: dict | None = None
    image_ref: str | None = None


class SessionDetailResponse(BaseModel):
    """Chi tiết một lượt gửi xe hoàn chỉnh (dòng thời gian, ảnh vào/ra, override)."""

    id: UUID
    building_id: UUID
    license_plate: str | None = None
    normalized_plate: str | None = None
    ticket_code: str | None = None
    vehicle_type: str
    ticket_kind: str
    check_in_time: datetime
    exit_time: datetime | None = None
    duration_minutes: int
    fee: float
    status: str
    has_exception: bool
    check_in_image_url: str | None = None
    exit_image_url: str | None = None
    check_in_operator_name: str | None = None
    exit_operator_name: str | None = None
    override_reason: str | None = None
    in_lane_name: str | None = None
    exit_lane_name: str | None = None
    timeline: list[LifecycleTimelineEvent] = Field(default_factory=list)
