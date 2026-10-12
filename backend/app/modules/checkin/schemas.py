from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.pricing.domain import TicketKind

from .models import CheckInSource, TransactionStatus


class CheckInRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    lane_id: UUID
    vehicle_type: str | None = Field(None, min_length=1, max_length=40)
    ticket_kind: TicketKind | None = None
    customer_class_id: UUID | None = None
    zone_id: UUID | None = None
    license_plate: str | None = Field(None, min_length=3, pattern=r"^[A-Za-z0-9\-\.\s]+$")
    ticket_code: str | None = Field(None, min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_-]+$")
    # Backwards-compatible body name used by the first check-in prototype.
    plate_number: str | None = Field(None, min_length=3, pattern=r"^[A-Za-z0-9\-\.\s]+$")
    detection_id: UUID | None = None
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    original_ai_plate: str | None = Field(None, max_length=50)
    source: CheckInSource | None = None
    override_reason: str | None = Field(None, max_length=500)
    idempotency_key: str | None = Field(None, min_length=1, max_length=255)

    @model_validator(mode="after")
    def require_plate(self) -> "CheckInRequest":
        if not (self.license_plate or self.plate_number or self.ticket_code):
            raise ValueError("license_plate or ticket_code is required")
        if self.ticket_code and (self.license_plate or self.plate_number):
            raise ValueError("Send either a plate or a ticket code")
        return self

    @property
    def requested_plate(self) -> str:
        return self.license_plate or self.plate_number or self.ticket_code or ""


class ParkingTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    license_plate: str
    original_ai_plate: str | None = None
    normalized_plate: str
    status: TransactionStatus
    lane_id: UUID
    building_id: UUID | None = None
    lane_name: str | None = Field(default=None, validation_alias="lane_snapshot_name")
    lane_direction: str | None = Field(default=None, validation_alias="lane_snapshot_direction")
    detection_id: UUID | None = None
    image_url: str | None = None
    confidence: float | None = None
    check_in_time: datetime
    check_in_operator_id: UUID | None = None
    check_in_operator_name: str | None = Field(
        default=None, validation_alias="operator_snapshot_name"
    )
    source: str
    is_manual_override: bool
    notes: str | None = None
    created_at: datetime


class PaginatedParkingTransactions(BaseModel):
    data: list[ParkingTransactionResponse]
    total: int
    page: int
    limit: int


class CheckInResponse(BaseModel):
    transaction: ParkingTransactionResponse
    message: str


class AuditLogResponse(BaseModel):
    id: UUID
    time: datetime
    actor: str | None = None
    action: str
    resource: str
    resource_id: str
    source: str | None = None
    before: object | None = None
    after: object | None = None
    correlation_id: str | None = None


class PaginatedAuditLogs(BaseModel):
    data: list[AuditLogResponse]
    total: int
    page: int
    limit: int
