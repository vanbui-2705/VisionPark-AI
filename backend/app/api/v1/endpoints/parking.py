from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy import func as _func
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.database.session import get_db
from app.modules.auth.dependencies import require_roles
from app.modules.checkin.models import ParkingTransaction, TransactionStatus
from app.modules.checkin.repository import DatabaseCheckInRepository
from app.modules.checkin.schemas import CheckInRequest, CheckInResponse, ParkingTransactionResponse
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
    current_user: User = Depends(require_roles(RoleName.OPERATOR, RoleName.ADMIN)),
) -> CheckInResponse:
    return service.process_check_in(
        request,
        operator=current_user,
        idempotency_key=idempotency_key,
    )


@router.get("/transactions")
def list_parking_transactions(
    request: Request,
    q: str | None = None,
    lane_id: UUID | None = None,
    status: TransactionStatus | None = None,
    from_time: Annotated[datetime | None, Query(alias="from")] = None,
    to_time: Annotated[datetime | None, Query(alias="to")] = None,
    page: int | None = Query(None, ge=0),
    pageSize: int | None = Query(None, ge=1, le=100),
    limit: int | None = Query(None, ge=1, le=100),
    skip: int | None = Query(None, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.OPERATOR, RoleName.ADMIN)),
):
    del current_user
    is_paginated = (
        "page" in request.query_params
        or "pageSize" in request.query_params
        or request.query_params.get("format") == "paginated"
    )
    eff_page = page if page is not None else 0
    eff_page_size = pageSize if pageSize is not None else (limit if limit is not None else 20)
    # compat: limit/skip -> page/pageSize
    if limit is not None and not is_paginated:
        eff_page_size = limit
        eff_page = (skip // max(1, eff_page_size)) if skip else 0
    if eff_page < 0 or eff_page_size < 1 or eff_page_size > 100:
        raise AppError(status_code=422, code="VALIDATION_ERROR", message="Invalid page/pageSize")
    # pass through service for filtered list then paginate server-side
    from sqlalchemy import or_ as _or

    base_q = select(ParkingTransaction)
    count_q = select(_func.count()).select_from(ParkingTransaction)
    conds = []
    if q:
        pat = f"%{q.upper()}%"
        cond = _or(
            ParkingTransaction.license_plate.ilike(pat),
            ParkingTransaction.normalized_plate.ilike(pat),
        )
        conds.append(cond)
    if lane_id is not None:
        conds.append(ParkingTransaction.lane_id == lane_id)
    if status is not None:
        conds.append(ParkingTransaction.status == status)
    if from_time is not None:
        conds.append(ParkingTransaction.check_in_time >= from_time)
    if to_time is not None:
        to_inc = to_time
        conds.append(ParkingTransaction.check_in_time <= to_inc)
    for c in conds:
        base_q = base_q.where(c)
        count_q = count_q.where(c)
    total = db.scalar(count_q) or 0
    totalPages = max(1, (total + eff_page_size - 1) // eff_page_size)
    items = list(
        db.scalars(
            base_q.order_by(ParkingTransaction.check_in_time.desc())
            .offset(eff_page * eff_page_size)
            .limit(eff_page_size)
        ).all()
    )
    # map to response shape via from_attributes
    out_items = [
        ParkingTransactionResponse.model_validate(x, from_attributes=True).model_dump(mode="json")
        for x in items
    ]
    if is_paginated:
        return {
            "items": out_items,
            "total": total,
            "page": eff_page,
            "pageSize": eff_page_size,
            "totalPages": totalPages,
        }
    return out_items


@router.get("/transactions/{transaction_id}", response_model=ParkingTransactionResponse)
def get_parking_transaction(
    transaction_id: UUID,
    service: CheckInService = Depends(get_checkin_service),
    current_user: User = Depends(require_roles(RoleName.OPERATOR, RoleName.ADMIN)),
) -> ParkingTransactionResponse:
    del current_user
    return service.get_transaction(transaction_id)
