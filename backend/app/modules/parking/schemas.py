from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from typing import Generic, TypeVar

from .models import TransactionStatus, CheckInSource


class ParkingTransactionResponse(BaseModel):
    id: UUID
    license_plate: str
    original_ai_plate: str | None = None
    normalized_plate: str
    status: TransactionStatus
    lane_id: UUID
    lane_name: str | None = None
    detection_id: UUID | None = None
    confidence: float | None = None
    check_in_time: datetime
    check_in_operator_id: UUID | None = None
    check_in_operator_name: str | None = None
    source: CheckInSource
    is_manual_override: bool
    notes: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    pageSize: int
    totalPages: int


class CheckInRequest(BaseModel):
    lane_id: UUID
    license_plate: str = Field(..., min_length=3, max_length=50)
    detection_id: UUID | None = None
    confidence: float | None = Field(None, ge=0, le=1)
    source: CheckInSource = CheckInSource.OPERATOR_MANUAL
    override_reason: str | None = None
