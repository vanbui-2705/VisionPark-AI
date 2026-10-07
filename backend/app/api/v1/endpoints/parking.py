from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.auth.dependencies import require_roles
from app.modules.checkin.models import TransactionStatus
from app.modules.checkin.repository import DatabaseCheckInRepository
from app.modules.checkin.schemas import (
    CheckInRequest,
    CheckInResponse,
    PaginatedParkingTransactions,
    ParkingTransactionResponse,
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
    current_user: User = Depends(require_roles(RoleName.OPERATOR, RoleName.ADMIN)),
) -> CheckInResponse:
    return service.process_check_in(
        request,
        operator=current_user,
        idempotency_key=idempotency_key,
    )


@router.get("/transactions", response_model=PaginatedParkingTransactions)
def list_parking_transactions(
    q: str | None = None,
    lane_id: UUID | None = None,
    status: TransactionStatus | None = None,
    from_time: Annotated[datetime | None, Query(alias="from")] = None,
    to_time: Annotated[datetime | None, Query(alias="to")] = None,
    limit: int = Query(100, ge=1, le=200),
    page: int = Query(0, ge=0),
    service: CheckInService = Depends(get_checkin_service),
    current_user: User = Depends(require_roles(RoleName.OPERATOR, RoleName.ADMIN)),
) -> PaginatedParkingTransactions:
    del current_user
    return service.list_transactions(
        query=q,
        lane_id=lane_id,
        status=status,
        from_time=from_time,
        to_time=to_time,
        limit=limit,
        offset=page * limit,
    )


@router.get("/transactions/{transaction_id}", response_model=ParkingTransactionResponse)
def get_parking_transaction(
    transaction_id: UUID,
    service: CheckInService = Depends(get_checkin_service),
    current_user: User = Depends(require_roles(RoleName.OPERATOR, RoleName.ADMIN)),
) -> ParkingTransactionResponse:
    del current_user
    return service.get_transaction(transaction_id)
