from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.database.session import get_db
from app.modules.auth.dependencies import require_roles
from app.modules.checkin.models import TransactionStatus
from app.modules.checkin.repository import DatabaseCheckInRepository
from app.modules.checkin.schemas import (
    AccessCheckRequest,
    AccessCheckResponse,
    AdjustCounterRequest,
    AdjustCounterResponse,
    AvailabilityItem,
    CheckInRequest,
    CheckInResponse,
    CompensatorySessionRequest,
    CompensatorySessionResponse,
    CounterDiscrepancyItem,
    PaginatedParkingTransactions,
    ParkingTransactionResponse,
    ReconcileRequest,
    ReconciliationReportResponse,
)
from app.modules.checkin.service import CheckInService
from app.modules.users.models import User
from app.modules.users.schemas import RoleName

router = APIRouter(prefix="/parking", tags=["parking"])


def get_checkin_service(db: Annotated[Session, Depends(get_db)]) -> CheckInService:
    return CheckInService(DatabaseCheckInRepository(db), session=db)


@router.post("/check-in", response_model=CheckInResponse, status_code=201)
def create_check_in(
    request: CheckInRequest,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    service: CheckInService = Depends(get_checkin_service),
    current_user: User = Depends(
        require_roles(RoleName.OPERATOR, RoleName.ADMIN, RoleName.TECHNICIAN)
    ),
) -> CheckInResponse:
    return service.process_check_in(
        request,
        operator=current_user,
        idempotency_key=idempotency_key,
    )


@router.post("/access-check", response_model=AccessCheckResponse)
def check_access_endpoint(
    request: AccessCheckRequest,
    service: CheckInService = Depends(get_checkin_service),
    current_user: User = Depends(
        require_roles(RoleName.OPERATOR, RoleName.ADMIN, RoleName.TECHNICIAN)
    ),
) -> AccessCheckResponse:
    return service.check_access(request, operator=current_user)


@router.get("/availability", response_model=list[AvailabilityItem])
def get_parking_availability(
    db: Annotated[Session, Depends(get_db)],
    building_id: UUID | None = None,
) -> list[AvailabilityItem]:
    """Lấy số chỗ trống theo loại xe cho màn hình cổng / dashboard (mục 4.4 nghiepvu.md)."""
    from app.modules.checkin.counter_service import CounterService

    return [
        AvailabilityItem(**item)
        for item in CounterService.get_availability(db, building_id=building_id)
    ]


@router.post("/counters/adjust", response_model=AdjustCounterResponse)
def adjust_parking_counter(
    request: AdjustCounterRequest,
    db: Annotated[Session, Depends(get_db)],
    building_id: UUID | None = None,
    current_user: User = Depends(require_roles(RoleName.OPERATOR, RoleName.ADMIN)),
) -> AdjustCounterResponse:
    """Hiệu chỉnh bộ đếm thủ công có lý do (mục 4.4 nghiepvu.md)."""
    from app.modules.audit_logs.service import log_action
    from app.modules.checkin.counter_service import CounterService

    counter = CounterService.adjust_counter(
        db=db,
        building_id=building_id,
        vehicle_type=request.vehicle_type,
        delta=request.delta,
        reason=request.reason,
        actor_type="OPERATOR",
        actor_id=current_user.id,
        note=request.note,
    )
    log_action(
        db=db,
        user_id=current_user.id,
        action="ADJUST_COUNTER",
        entity_type="ParkingCounter",
        entity_id=str(counter.id),
        new_value={
            "vehicle_type": request.vehicle_type,
            "delta": request.delta,
            "new_occupied": counter.occupied,
            "reason": request.reason,
            "note": request.note,
        },
    )
    db.commit()
    db.refresh(counter)
    return AdjustCounterResponse(
        id=counter.id,
        building_id=counter.building_id,
        vehicle_type=counter.vehicle_type,
        occupied=counter.occupied,
        delta=request.delta,
        reason=request.reason,
        updated_at=counter.updated_at,
    )


@router.get("/counters/discrepancies", response_model=list[CounterDiscrepancyItem])
def get_counter_discrepancies(
    db: Annotated[Session, Depends(get_db)],
    building_id: UUID | None = None,
    current_user: User = Depends(require_roles(RoleName.OPERATOR, RoleName.ADMIN)),
) -> list[CounterDiscrepancyItem]:
    """Kiểm tra sai lệch giữa số phiên PARKED thực tế và bộ đếm (mục 4.4 nghiepvu.md)."""
    del current_user
    from app.modules.checkin.counter_reconciliation import CounterReconciliationService

    discrepancies = CounterReconciliationService.check_discrepancies(db, building_id=building_id)
    return [
        CounterDiscrepancyItem(
            vehicle_type=d.vehicle_type,
            counter_occupied=d.counter_occupied,
            active_sessions=d.active_sessions,
            drift=d.drift,
        )
        for d in discrepancies
    ]


@router.post("/counters/reconcile", response_model=ReconciliationReportResponse)
def reconcile_parking_counters(
    request: ReconcileRequest,
    db: Annotated[Session, Depends(get_db)],
    building_id: UUID | None = None,
    current_user: User = Depends(require_roles(RoleName.OPERATOR, RoleName.ADMIN)),
) -> ReconciliationReportResponse:
    """Job đối soát định kỳ và hiệu chỉnh qua counter_events có audit (mục 4.4 nghiepvu.md)."""
    from app.modules.checkin.counter_reconciliation import CounterReconciliationService

    discrepancies, adjusted = CounterReconciliationService.reconcile_and_adjust(
        db=db,
        building_id=building_id,
        auto_correct=request.auto_correct,
        actor_type="OPERATOR",
        actor_id=current_user.id,
        reason=request.reason,
    )
    return ReconciliationReportResponse(
        building_id=building_id,
        has_discrepancy=len(discrepancies) > 0,
        adjusted=adjusted,
        discrepancies=[
            CounterDiscrepancyItem(
                vehicle_type=d.vehicle_type,
                counter_occupied=d.counter_occupied,
                active_sessions=d.active_sessions,
                drift=d.drift,
            )
            for d in discrepancies
        ],
    )


@router.post("/counters/compensate", response_model=CompensatorySessionResponse)
def compensate_offline_session_endpoint(
    request: CompensatorySessionRequest,
    db: Annotated[Session, Depends(get_db)],
    building_id: UUID | None = None,
    current_user: User = Depends(require_roles(RoleName.OPERATOR, RoleName.ADMIN)),
) -> CompensatorySessionResponse:
    """Tạo phiên bù khi mạng lỗi: tăng bộ đếm qua counter_events (mục 4.4 nghiepvu.md)."""
    from app.modules.checkin.counter_reconciliation import CounterReconciliationService

    counter = CounterReconciliationService.compensate_offline_session(
        db=db,
        building_id=building_id,
        vehicle_type=request.vehicle_type,
        actor_id=current_user.id,
        session_id=request.session_id,
        reason=request.reason,
        note=request.note,
    )
    return CompensatorySessionResponse(
        id=counter.id,
        building_id=counter.building_id,
        vehicle_type=counter.vehicle_type,
        occupied=counter.occupied,
        delta=1,
        reason=request.reason,
        updated_at=counter.updated_at,
    )


@router.get(
    "/transactions",
    response_model=dict | PaginatedParkingTransactions | list[ParkingTransactionResponse],
)
def list_parking_transactions(
    request: Request,
    q: str | None = None,
    lane_id: UUID | None = None,
    status: TransactionStatus | None = None,
    from_time: Annotated[datetime | None, Query(alias="from")] = None,
    to_time: Annotated[datetime | None, Query(alias="to")] = None,
    page: int | None = Query(None, ge=0),
    pageSize: int | None = Query(None, ge=1, le=100),
    limit: int | None = Query(None, ge=1, le=200),
    skip: int | None = Query(None, ge=0),
    paginated: bool = False,
    service: CheckInService = Depends(get_checkin_service),
    current_user: User = Depends(
        require_roles(RoleName.OPERATOR, RoleName.ADMIN, RoleName.ACCOUNTANT)
    ),
):
    del current_user
    is_paginated = (
        paginated
        or ("page" in request.query_params)
        or ("pageSize" in request.query_params)
        or (request.query_params.get("format") == "paginated")
    )
    eff_page_size = pageSize if pageSize is not None else (limit if limit is not None else 20)
    eff_skip = (page * eff_page_size) if page is not None else (skip if skip is not None else 0)
    eff_page = page if page is not None else (eff_skip // max(1, eff_page_size))

    if eff_page < 0 or eff_page_size < 1 or eff_page_size > 100:
        raise AppError(status_code=422, code="VALIDATION_ERROR", message="Invalid page/pageSize")

    paginated_result = service.list_transactions(
        query=q,
        lane_id=lane_id,
        status=status,
        from_time=from_time,
        to_time=to_time,
        limit=eff_page_size,
        offset=eff_skip,
    )
    if is_paginated:
        return {
            "items": [row.model_dump(mode="json") for row in paginated_result.data],
            "data": paginated_result.data,
            "total": paginated_result.total,
            "page": paginated_result.page,
            "pageSize": eff_page_size,
            "totalPages": max(1, (paginated_result.total + eff_page_size - 1) // eff_page_size),
            "limit": eff_page_size,
            "offset": eff_skip,
        }
    return paginated_result.data


@router.get("/summary", response_model=dict[str, int])
def get_parking_summary(
    db: Annotated[Session, Depends(get_db)],
    current_user: User = Depends(
        require_roles(RoleName.OPERATOR, RoleName.ADMIN, RoleName.ACCOUNTANT)
    ),
) -> dict[str, int]:
    del current_user
    return DatabaseCheckInRepository(db).summary()


@router.get("/transactions/{transaction_id}", response_model=ParkingTransactionResponse)
def get_parking_transaction(
    transaction_id: UUID,
    service: CheckInService = Depends(get_checkin_service),
    current_user: User = Depends(
        require_roles(RoleName.OPERATOR, RoleName.ADMIN, RoleName.ACCOUNTANT)
    ),
) -> ParkingTransactionResponse:
    del current_user
    return service.get_transaction(transaction_id)
