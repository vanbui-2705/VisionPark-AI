from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BarrierOpenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trigger_reason: str = Field(
        default="NORMAL",
        description="Lý do mở: NORMAL, OVERRIDE, EMERGENCY (BR-23)",
    )
    override_reason: str | None = Field(
        default=None,
        description="Bắt buộc khi trigger_reason=OVERRIDE (BR-08, BR-23)",
    )
    session_id: UUID | None = Field(
        default=None,
        description="ID phiên gửi xe liên quan (nếu có)",
    )
    timeout_seconds: int = Field(
        default=15,
        ge=1,
        le=300,
        description="Thời gian chờ xe qua trước khi tự đóng (giây)",
    )


class BarrierCloseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(
        default="VEHICLE_PASSED",
        description="Lý do đóng: VEHICLE_PASSED, TIMEOUT_AUTO_CLOSE, MANUAL_CLOSE",
    )
    session_id: UUID | None = Field(
        default=None,
        description="ID phiên gửi xe liên quan (nếu có)",
    )


class BarrierEmergencyOpenRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    session_id: UUID | None = Field(
        default=None,
        description="ID phiên gửi xe liên quan (nếu có)",
    )
    reason: str = Field(
        default="EMERGENCY",
        description="Lý do mở khẩn cấp (PCCC, sơ tán, sự cố)",
    )
    note: str | None = Field(
        default=None,
        description="Ghi chú chi tiết sự cố",
    )
    timeout_seconds: int = Field(
        default=60,
        ge=1,
        le=300,
        description="Thời gian mở khẩn cấp (giây)",
    )


class BarrierEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    building_id: UUID | None
    lane_id: UUID
    barrier_id: str | None
    action: str
    trigger_reason: str
    operator_id: UUID | None
    session_id: UUID | None
    status: str
    timeout_seconds: int
    details: dict | None
    created_at: datetime
