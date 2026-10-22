from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.users.models import User

from .schemas import (
    BarrierCloseRequest,
    BarrierEmergencyOpenRequest,
    BarrierEventResponse,
    BarrierOpenRequest,
)
from .service import BarrierService

router = APIRouter(tags=["barriers"])


def get_barrier_service(db: Annotated[Session, Depends(get_db)]) -> BarrierService:
    return BarrierService(db)


@router.post("/gates/{lane_id}/open", response_model=BarrierEventResponse)
def open_barrier_gate(
    lane_id: UUID,
    request: BarrierOpenRequest,
    service: BarrierService = Depends(get_barrier_service),
    current_user: User = Depends(get_current_user),
) -> BarrierEventResponse:
    """Mở barrier mô phỏng theo quyền (BR-08) và ghi lý do kích hoạt (BR-23)."""
    return service.open_barrier(lane_id=lane_id, request=request, operator=current_user)


@router.post("/gates/{lane_id}/emergency-open", response_model=BarrierEventResponse)
def emergency_open_barrier_gate(
    lane_id: UUID,
    request: BarrierEmergencyOpenRequest | None = Body(None),
    service: BarrierService = Depends(get_barrier_service),
    current_user: User = Depends(get_current_user),
) -> BarrierEventResponse:
    """Mở barrier khẩn cấp ngay lập tức (PCCC / Sơ tán), ghi sự kiện (BR-23)."""
    return service.emergency_open_barrier(lane_id=lane_id, operator=current_user, request=request)


@router.post("/gates/{lane_id}/close", response_model=BarrierEventResponse)
def close_barrier_gate(
    lane_id: UUID,
    request: BarrierCloseRequest,
    service: BarrierService = Depends(get_barrier_service),
    current_user: User = Depends(get_current_user),
) -> BarrierEventResponse:
    """Đóng barrier mô phỏng (xe qua hoặc hết thời gian chờ tự động đóng)."""
    return service.close_barrier(lane_id=lane_id, request=request, operator=current_user)


@router.get("/barriers/events", response_model=list[BarrierEventResponse])
def list_barrier_events(
    lane_id: UUID | None = None,
    building_id: UUID | None = None,
    trigger_reason: str | None = None,
    session_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    service: BarrierService = Depends(get_barrier_service),
    current_user: User = Depends(get_current_user),
) -> list[BarrierEventResponse]:
    """Truy vấn lịch sử sự kiện barrier phục vụ audit và giám sát vận hành."""
    return service.list_events(
        lane_id=lane_id,
        building_id=building_id,
        trigger_reason=trigger_reason,
        session_id=session_id,
        limit=limit,
        offset=offset,
    )
