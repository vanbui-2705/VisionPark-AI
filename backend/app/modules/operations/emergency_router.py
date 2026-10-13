from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.auth.dependencies import require_roles
from app.modules.checkin.counter_service import CounterService
from app.modules.users.models import User
from app.modules.users.schemas import RoleName

from .emergency_schemas import (
    AvailabilityItem,
    CheckoutEmergencyRequest,
    EmergencyExitRequest,
    EmergencyExitResponse,
)
from .emergency_service import EmergencyService

router = APIRouter(tags=["emergency-operations"])
Db = Annotated[Session, Depends(get_db)]
AllowedOperator = Annotated[
    User,
    Depends(
        require_roles(
            RoleName.OPERATOR,
            RoleName.BUILDING_ADMIN,
            RoleName.SYSTEM_ADMIN,
        )
    ),
]


@router.get("/availability", response_model=list[AvailabilityItem])
def get_availability(
    db: Db,
    building_id: UUID | None = None,
) -> list[AvailabilityItem]:
    """
    Lấy số chỗ trống theo loại xe cho màn hình cổng LED / Dashboard (chỉ đọc, BR-04, BR-13).
    """
    raw_items = CounterService.get_availability(db, building_id=building_id)
    return [AvailabilityItem(**item) for item in raw_items]


@router.post("/emergency/lanes/{lane_id}/open", response_model=EmergencyExitResponse)
def open_emergency_exit_lane(
    lane_id: UUID,
    request: EmergencyExitRequest,
    operator: AllowedOperator,
    db: Db,
) -> EmergencyExitResponse:
    """
    Chế độ khẩn cấp (PCCC / Sơ tán - dòng 476 nghiepvu.md, BR-23):
    Mở làn ra NGAY LẬP TỨC (không thu phí, không kiểm tra luồng tiền),
    bắt buộc ghi nhận vòng đời, trừ bộ đếm và đánh cờ để xử lý phí sau sự cố.
    """
    service = EmergencyService(db)
    return service.open_emergency_exit(lane_id=lane_id, request=request, operator=operator)


@router.post("/checkout/emergency", response_model=EmergencyExitResponse)
def checkout_emergency_exit(
    request: CheckoutEmergencyRequest,
    operator: AllowedOperator,
    db: Db,
) -> EmergencyExitResponse:
    """
    Alias endpoint cho quy trình check-out khẩn cấp qua cổng ra.
    """
    service = EmergencyService(db)
    exit_req = EmergencyExitRequest(
        session_id=request.session_id,
        license_plate=request.license_plate,
        ticket_code=request.ticket_code,
        reason=request.reason,
        note=request.note,
    )
    return service.open_emergency_exit(
        lane_id=request.lane_id,
        request=exit_req,
        operator=operator,
    )
