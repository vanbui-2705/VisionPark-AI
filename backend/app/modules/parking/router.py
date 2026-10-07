from typing import Annotated
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select

from app.core.errors import AppError
from app.database.session import get_db
from app.modules.auth.dependencies import require_roles
from app.modules.users.models import User
from app.modules.users.schemas import RoleName
from app.modules.parking.schemas import ParkingTransactionResponse, PaginatedResponse, CheckInRequest
from app.modules.parking.repository import list_transactions, get_transaction
from app.modules.parking.service import create_check_in
from app.modules.parking.models import TransactionStatus, ParkingTransaction

router = APIRouter(prefix="/parking", tags=["parking"])


def _to_response(tx: ParkingTransaction, db: Session) -> ParkingTransactionResponse:
    op_name = None
    if tx.check_in_operator_id:
        u = db.get(User, tx.check_in_operator_id)
        op_name = getattr(u, "display_name", None) if u else None
    return ParkingTransactionResponse(
        id=tx.id,
        license_plate=tx.license_plate,
        original_ai_plate=tx.original_ai_plate,
        normalized_plate=tx.normalized_plate,
        status=tx.status,
        lane_id=tx.lane_id,
        lane_name=tx.lane_name,
        detection_id=tx.detection_id,
        confidence=tx.confidence,
        check_in_time=tx.check_in_time,
        check_in_operator_id=tx.check_in_operator_id,
        check_in_operator_name=op_name,
        source=tx.source,
        is_manual_override=tx.is_manual_override,
        notes=tx.notes,
        created_at=tx.created_at,
    )


@router.get("/transactions", response_model=PaginatedResponse[ParkingTransactionResponse])
def list_parking_transactions(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleName.OPERATOR, RoleName.ADMIN))],
    q: str | None = Query(None),
    lane_id: UUID | None = Query(None),
    status: TransactionStatus | None = Query(None),
    from_time: datetime | None = Query(None, alias="from"),
    to_time: datetime | None = Query(None, alias="to"),
    page: int = Query(0, ge=0),
    pageSize: int = Query(20, ge=1, le=100),
):
    items, total = list_transactions(db, q=q, lane_id=lane_id, status=status, from_time=from_time, to_time=to_time, page=page, pageSize=pageSize)
    totalPages = max(1, (total + pageSize - 1) // pageSize)
    mapped = [_to_response(x, db) for x in items]
    return {"items": mapped, "total": total, "page": page, "pageSize": pageSize, "totalPages": totalPages}


@router.get("/transactions/{tx_id}", response_model=ParkingTransactionResponse)
def get_parking_transaction(
    tx_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleName.OPERATOR, RoleName.ADMIN))],
):
    tx = get_transaction(db, tx_id)
    if not tx:
        raise AppError(status_code=404, code="NOT_FOUND", message="Transaction not found")
    return _to_response(tx, db)


@router.post("/check-in", response_model=dict)
def check_in(
    payload: CheckInRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleName.OPERATOR, RoleName.ADMIN))],
):
    tx = create_check_in(db, lane_id=payload.lane_id, license_plate=payload.license_plate, operator=current_user, source=payload.source, detection_id=payload.detection_id, confidence=payload.confidence, override_reason=payload.override_reason)
    from app.modules.audit_logs.service import log_action
    log_action(db, user_id=current_user.id, action="CHECK_IN", entity_type="ParkingTransaction", entity_id=str(tx.id), new_value={"plate": tx.license_plate, "lane_id": str(tx.lane_id)})
    db.commit()
    db.refresh(tx)
    return {"transaction": _to_response(tx, db).model_dump(mode="json"), "message": "Check-in successful"}
