from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.checkin.schemas import AvailabilityItem


class EmergencyExitRequest(BaseModel):
    session_id: UUID | None = None
    license_plate: str | None = None
    ticket_code: str | None = None
    reason: str = Field(
        default="PCCC_EMERGENCY",
        description="Lý do mở khẩn cấp (PCCC, sơ tán)",
    )
    note: str | None = Field(default=None, description="Ghi chú chi tiết sự cố")


class EmergencyExitResponse(BaseModel):
    lane_id: UUID
    barrier_status: str
    trigger_reason: str
    session_id: UUID | None = None
    license_plate: str | None = None
    status: str
    fee: float = 0.0
    requires_post_incident_audit: bool = True
    message: str


class CheckoutEmergencyRequest(BaseModel):
    lane_id: UUID
    session_id: UUID | None = None
    license_plate: str | None = None
    ticket_code: str | None = None
    reason: str = Field(
        default="PCCC_EMERGENCY",
        description="Lý do mở khẩn cấp (PCCC, sơ tán)",
    )
    note: str | None = Field(default=None, description="Ghi chú chi tiết sự cố")


__all__ = [
    "AvailabilityItem",
    "CheckoutEmergencyRequest",
    "EmergencyExitRequest",
    "EmergencyExitResponse",
]
