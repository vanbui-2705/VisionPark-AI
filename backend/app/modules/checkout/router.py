from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.auth.dependencies import require_roles
from app.modules.checkin.repository import DatabaseCheckInRepository
from app.modules.users.models import User
from app.modules.users.schemas import RoleName

from .schemas import (
    CheckOutPreviewResponse,
    CheckOutRequest,
    CheckOutResponse,
    PaymentRecordRequest,
)
from .service import CheckOutService

router = APIRouter(prefix="/parking", tags=["checkout"])


def get_checkout_service(db: Annotated[Session, Depends(get_db)]) -> CheckOutService:
    return CheckOutService(DatabaseCheckInRepository(db), session=db)


@router.post("/check-out/preview", response_model=CheckOutPreviewResponse)
def preview_check_out(
    request: CheckOutRequest,
    service: CheckOutService = Depends(get_checkout_service),
    current_user: User = Depends(
        require_roles(RoleName.OPERATOR, RoleName.SYSTEM_ADMIN, RoleName.BUILDING_ADMIN)
    ),
) -> CheckOutPreviewResponse:
    """Xem trước phí và thông tin xe ra (chưa đóng phiên)."""
    return service.preview(request, operator=current_user)


@router.post("/check-out", response_model=CheckOutResponse)
def create_check_out(
    request: CheckOutRequest,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    service: CheckOutService = Depends(get_checkout_service),
    current_user: User = Depends(
        require_roles(RoleName.OPERATOR, RoleName.SYSTEM_ADMIN, RoleName.BUILDING_ADMIN)
    ),
) -> CheckOutResponse:
    """Đóng phiên gửi xe idempotent, mở barrier, giảm bộ đếm (mục 4.7 nghiepvu.md)."""
    return service.process_checkout(
        request,
        operator=current_user,
        idempotency_key=idempotency_key,
    )


@router.post("/sessions/{session_id}/payments", response_model=CheckOutResponse)
def record_session_payment(
    session_id: UUID,
    request: PaymentRecordRequest,
    service: CheckOutService = Depends(get_checkout_service),
    current_user: User = Depends(
        require_roles(RoleName.OPERATOR, RoleName.SYSTEM_ADMIN, RoleName.BUILDING_ADMIN)
    ),
) -> CheckOutResponse:
    """Ghi nhận thanh toán tiền mặt/override cho phiên PAYMENT_PENDING để hoàn tất xe ra."""
    return service.record_payment(
        session_id=session_id,
        operator=current_user,
        payment_method=request.payment_method,
        amount=request.amount,
        provider_ref=request.provider_ref,
        override_reason=request.override_reason,
    )
