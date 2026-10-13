from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.pricing.domain import TicketKind

from .models import CheckInSource, TransactionStatus


class CheckInRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    lane_id: UUID
    ticket_kind: TicketKind | None = None
    customer_class_id: UUID | None = None
    zone_id: UUID | None = None
    license_plate: str | None = Field(None, min_length=3, pattern=r"^[A-Za-z0-9\-\.\s]+$")
    ticket_code: str | None = Field(None, min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    # Backwards-compatible body name used by the first check-in prototype.
    plate_number: str | None = Field(None, min_length=3, pattern=r"^[A-Za-z0-9\-\.\s]+$")
    vehicle_type: str = "CAR"
    customer_class: str = "VISITOR"
    detection_id: UUID | None = None
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    original_ai_plate: str | None = Field(None, max_length=50)
    source: CheckInSource | None = None
    override_reason: str | None = Field(None, max_length=500)
    idempotency_key: str | None = Field(None, min_length=1, max_length=255)

    @model_validator(mode="after")
    def validate_identification(self) -> "CheckInRequest":
        if self.vehicle_type == "BICYCLE":
            # BR-20: Xe đạp không bắt buộc biển số nhưng phải có ticket_code
            if not self.ticket_code and not (self.license_plate or self.plate_number):
                raise ValueError("ticket_code or license_plate is required for bicycles (BR-20)")
        else:
            if not (self.license_plate or self.plate_number or self.ticket_code):
                raise ValueError("license_plate or ticket_code is required")
        return self

    @property
    def requested_plate(self) -> str | None:
        return self.license_plate or self.plate_number or self.ticket_code


class AccessCheckRequest(BaseModel):
    lane_id: UUID
    vehicle_type: str = "CAR"
    customer_class: str = "VISITOR"
    license_plate: str | None = Field(None, pattern=r"^[A-Za-z0-9\-\.\s]+$")
    ticket_code: str | None = None
    override_reason: str | None = None


class AccessCheckResponse(BaseModel):
    decision: str  # ALLOW, DENY, REVIEW
    reason: str
    details: dict | None = None


class ParkingTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    license_plate: str | None = None
    original_ai_plate: str | None = None
    normalized_plate: str | None = None
    ticket_code: str | None = None
    vehicle_type: str = "CAR"
    status: TransactionStatus
    lane_id: UUID
    exit_lane_id: UUID | None = None
    building_id: UUID | None = None
    lane_name: str | None = Field(default=None, validation_alias="lane_snapshot_name")
    lane_direction: str | None = Field(default=None, validation_alias="lane_snapshot_direction")
    detection_id: UUID | None = None
    image_url: str | None = None
    confidence: float | None = None
    check_in_time: datetime
    exit_time: datetime | None = None
    fee: float | None = None
    ticket_product_id: UUID | None = None
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


class AdjustCounterRequest(BaseModel):
    vehicle_type: str = "CAR"
    delta: int = Field(..., description="Số lượng xe thay đổi (+ hoặc -)")
    reason: str = Field(..., min_length=3, max_length=64, description="Lý do điều chỉnh")
    note: str | None = Field(None, max_length=500)


class AdjustCounterResponse(BaseModel):
    id: UUID
    building_id: UUID | None = None
    vehicle_type: str
    occupied: int
    delta: int
    reason: str
    updated_at: datetime


class AvailabilityItem(BaseModel):
    vehicle_type: str
    occupied: int
    safe_capacity: int
    physical_capacity: int
    available: int
    available_for_visitor: int
    resident_quota: int
    staff_quota: int
    status: str


class CounterDiscrepancyItem(BaseModel):
    vehicle_type: str
    counter_occupied: int
    active_sessions: int
    drift: int


class ReconcileRequest(BaseModel):
    auto_correct: bool = True
    reason: str = "PERIODIC_RECONCILIATION"


class ReconciliationReportResponse(BaseModel):
    building_id: UUID | None = None
    has_discrepancy: bool
    adjusted: bool
    discrepancies: list[CounterDiscrepancyItem]


class CompensatorySessionRequest(BaseModel):
    vehicle_type: str = "CAR"
    session_id: UUID | None = None
    reason: str = "NETWORK_OFFLINE_COMPENSATION"
    note: str | None = Field(None, max_length=500)


class CompensatorySessionResponse(BaseModel):
    id: UUID
    building_id: UUID | None = None
    vehicle_type: str
    occupied: int
    delta: int = 1
    reason: str
    updated_at: datetime
