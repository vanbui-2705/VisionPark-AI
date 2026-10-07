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


@router.get("/transactions", response_model=list[ParkingTransactionResponse] | dict)
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
    current_user: User = Depends(require_roles(RoleName.OPERATOR, RoleName.ADMIN)),
):
    del current_user
    is_paginated = (
        paginated
        or ("page" in request.query_params)
        or ("pageSize" in request.query_params)
        or (request.query_params.get("format") == "paginated")
    )
    eff_page_size = pageSize if pageSize is not None else (limit if limit is not None else 20)
    eff_skip = (
        (page * eff_page_size) if page is not None else (skip if skip is not None else 0)
    )
    eff_page = page if page is not None else (eff_skip // max(1, eff_page_size))

    if eff_page < 0 or eff_page_size < 1 or eff_page_size > 100:
        raise AppError(status_code=422, code="VALIDATION_ERROR", message="Invalid page/pageSize")

    rows = service.list_transactions(
        query=q,
        lane_id=lane_id,
        status=status,
        from_time=from_time,
        to_time=to_time,
        limit=eff_page_size,
        offset=eff_skip,
    )
    if is_paginated:
        total = service.repo.list_transactions(
            query=q,
            lane_id=lane_id,
            status=status,
            from_time=from_time,
            to_time=to_time,
            count_only=True,
        )
        total_pages = max(1, (total + eff_page_size - 1) // eff_page_size)
        return {
            "items": [
                row.model_dump(mode="json") if hasattr(row, "model_dump") else row for row in rows
            ],
            "total": total,
            "page": eff_page,
            "pageSize": eff_page_size,
            "totalPages": total_pages,
            "limit": eff_page_size,
            "offset": eff_skip,
        }
    return rows


@router.get("/transactions/{transaction_id}", response_model=ParkingTransactionResponse)
def get_parking_transaction(
    transaction_id: UUID,
    service: CheckInService = Depends(get_checkin_service),
    current_user: User = Depends(require_roles(RoleName.OPERATOR, RoleName.ADMIN)),
) -> ParkingTransactionResponse:
    del current_user
    return service.get_transaction(transaction_id)
