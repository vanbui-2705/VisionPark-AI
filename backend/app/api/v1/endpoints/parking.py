import re
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Header, Query, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.database.session import get_db
from app.database.tenant import requested_building
from app.integrations.storage.paths import media_root
from app.modules.audit_logs.service import log_action
from app.modules.auth.dependencies import require_roles
from app.modules.checkin.models import ParkingTransaction, TransactionStatus
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
        require_roles(RoleName.OPERATOR, RoleName.SYSTEM_ADMIN, RoleName.BUILDING_ADMIN)
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
        require_roles(RoleName.OPERATOR, RoleName.SYSTEM_ADMIN, RoleName.BUILDING_ADMIN)
    ),
) -> AccessCheckResponse:
    return service.check_access(request, operator=current_user)


@router.get("/availability", response_model=list[AvailabilityItem])
def get_parking_availability(
    db: Annotated[Session, Depends(get_db)],
    building_id: UUID | None = None,
    current_user: User = Depends(
        require_roles(
            RoleName.OPERATOR,
            RoleName.SYSTEM_ADMIN,
            RoleName.BUILDING_ADMIN,
            RoleName.ACCOUNTANT,
        )
    ),
) -> list[AvailabilityItem]:
    """Lấy số chỗ trống theo loại xe cho màn hình cổng / dashboard (mục 4.4 nghiepvu.md)."""
    from app.modules.checkin.counter_service import CounterService

    effective_building_id = requested_building(db, current_user, building_id)
    if effective_building_id is None:
        raise AppError(
            status_code=422,
            code="BUILDING_REQUIRED",
            message="Select a building before requesting parking availability.",
        )
    return [
        AvailabilityItem(**item)
        for item in CounterService.get_availability(db, building_id=effective_building_id)
    ]


@router.post("/counters/adjust", response_model=AdjustCounterResponse)
def adjust_parking_counter(
    request: AdjustCounterRequest,
    db: Annotated[Session, Depends(get_db)],
    building_id: UUID | None = None,
    current_user: User = Depends(
        require_roles(RoleName.OPERATOR, RoleName.SYSTEM_ADMIN, RoleName.BUILDING_ADMIN)
    ),
) -> AdjustCounterResponse:
    """Hiệu chỉnh bộ đếm thủ công có lý do (mục 4.4 nghiepvu.md)."""
    from app.modules.audit_logs.service import log_action
    from app.modules.checkin.counter_service import CounterService

    effective_building_id = requested_building(db, current_user, building_id)
    if effective_building_id is None:
        raise AppError(
            status_code=422,
            code="BUILDING_REQUIRED",
            message="Select a building before adjusting a parking counter.",
        )
    counter = CounterService.adjust_counter(
        db=db,
        building_id=effective_building_id,
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
    current_user: User = Depends(
        require_roles(RoleName.OPERATOR, RoleName.SYSTEM_ADMIN, RoleName.BUILDING_ADMIN)
    ),
) -> list[CounterDiscrepancyItem]:
    """Kiểm tra sai lệch giữa số phiên PARKED thực tế và bộ đếm (mục 4.4 nghiepvu.md)."""
    effective_building_id = requested_building(db, current_user, building_id)
    if effective_building_id is None:
        raise AppError(
            status_code=422,
            code="BUILDING_REQUIRED",
            message="Select a building before checking parking counters.",
        )
    from app.modules.checkin.counter_reconciliation import CounterReconciliationService

    discrepancies = CounterReconciliationService.check_discrepancies(
        db, building_id=effective_building_id
    )
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
    current_user: User = Depends(
        require_roles(RoleName.OPERATOR, RoleName.SYSTEM_ADMIN, RoleName.BUILDING_ADMIN)
    ),
) -> ReconciliationReportResponse:
    """Job đối soát định kỳ và hiệu chỉnh qua counter_events có audit (mục 4.4 nghiepvu.md)."""
    effective_building_id = requested_building(db, current_user, building_id)
    if effective_building_id is None:
        raise AppError(
            status_code=422,
            code="BUILDING_REQUIRED",
            message="Select a building before reconciling parking counters.",
        )
    from app.modules.checkin.counter_reconciliation import CounterReconciliationService

    discrepancies, adjusted = CounterReconciliationService.reconcile_and_adjust(
        db=db,
        building_id=effective_building_id,
        auto_correct=request.auto_correct,
        actor_type="OPERATOR",
        actor_id=current_user.id,
        reason=request.reason,
    )
    return ReconciliationReportResponse(
        building_id=effective_building_id,
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
    current_user: User = Depends(
        require_roles(RoleName.OPERATOR, RoleName.SYSTEM_ADMIN, RoleName.BUILDING_ADMIN)
    ),
) -> CompensatorySessionResponse:
    """Tạo phiên bù khi mạng lỗi: tăng bộ đếm qua counter_events (mục 4.4 nghiepvu.md)."""
    from app.modules.checkin.counter_reconciliation import CounterReconciliationService

    effective_building_id = requested_building(db, current_user, building_id)
    if effective_building_id is None:
        raise AppError(
            status_code=422,
            code="BUILDING_REQUIRED",
            message="Select a building before compensating a parking session.",
        )
    counter = CounterReconciliationService.compensate_offline_session(
        db=db,
        building_id=effective_building_id,
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
        require_roles(
            RoleName.OPERATOR, RoleName.SYSTEM_ADMIN, RoleName.BUILDING_ADMIN, RoleName.ACCOUNTANT
        )
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
        require_roles(
            RoleName.OPERATOR, RoleName.SYSTEM_ADMIN, RoleName.BUILDING_ADMIN, RoleName.ACCOUNTANT
        )
    ),
) -> dict[str, int]:
    del current_user
    return DatabaseCheckInRepository(db).summary()


@router.get("/transactions/{transaction_id}", response_model=ParkingTransactionResponse)
def get_parking_transaction(
    transaction_id: UUID,
    service: CheckInService = Depends(get_checkin_service),
    current_user: User = Depends(
        require_roles(
            RoleName.OPERATOR, RoleName.SYSTEM_ADMIN, RoleName.BUILDING_ADMIN, RoleName.ACCOUNTANT
        )
    ),
) -> ParkingTransactionResponse:
    del current_user
    return service.get_transaction(transaction_id)


# Ảnh thủ công của phiên gửi xe: không phụ thuộc ALPR.
_IMAGE_FILENAME = re.compile(r"^[0-9a-f]{32}\.(jpg|png)$")


@router.post("/sessions/{session_id}/images/{direction}")
async def upload_session_image(
    session_id: UUID,
    direction: Literal["entry", "exit"],
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(
        require_roles(
            RoleName.OPERATOR,
            RoleName.SYSTEM_ADMIN,
            RoleName.BUILDING_ADMIN,
        )
    ),
):
    tx = db.get(ParkingTransaction, session_id)
    if tx is None:
        raise AppError(
            status_code=404,
            code="SESSION_NOT_FOUND",
            message="Không tìm thấy phiên gửi xe.",
        )

    if tx.status not in {
        TransactionStatus.PARKED,
        TransactionStatus.ENTERED,
        TransactionStatus.PAYMENT_PENDING,
        TransactionStatus.PAID,
    }:
        raise AppError(
            status_code=409,
            code="SESSION_NOT_ACTIVE",
            message="Phiên không còn ở trạng thái cho phép bổ sung ảnh.",
        )

    if direction == "entry" and tx.image_url:
        raise AppError(
            status_code=409,
            code="ENTRY_IMAGE_EXISTS",
            message="Phiên này đã có ảnh xe vào.",
        )

    data = await image.read(settings.upload_max_bytes + 1)

    if not data or len(data) > settings.upload_max_bytes:
        raise AppError(
            status_code=422,
            code="INVALID_IMAGE_SIZE",
            message="Ảnh phải có dung lượng từ 1 byte đến 5 MB.",
        )

    if data.startswith(b"\xff\xd8\xff"):
        content_type, extension = "image/jpeg", "jpg"
    elif data.startswith(b"\x89PNG\r\n\x1a\n"):
        content_type, extension = "image/png", "png"
    else:
        raise AppError(
            status_code=422,
            code="INVALID_IMAGE",
            message="Chỉ chấp nhận ảnh JPEG hoặc PNG hợp lệ.",
        )

    if image.content_type != content_type:
        raise AppError(
            status_code=422,
            code="INVALID_IMAGE_TYPE",
            message="Định dạng file không khớp nội dung ảnh.",
        )

    try:
        decoded = cv2.imdecode(
            np.frombuffer(data, dtype=np.uint8),
            cv2.IMREAD_COLOR,
        )
    except cv2.error:
        decoded = None

    if decoded is None:
        raise AppError(
            status_code=422,
            code="CORRUPTED_IMAGE",
            message="Không thể đọc nội dung ảnh.",
        )

    folder = (
        media_root(settings.local_storage_path)
        / "parking_sessions"
        / str(tx.building_id)
        / str(tx.id)
        / direction
    )

    filename = f"{uuid4().hex}.{extension}"
    image_path = folder / filename

    try:
        folder.mkdir(parents=True, exist_ok=True)
        image_path.write_bytes(data)
    except OSError as exc:
        raise AppError(
            status_code=500,
            code="IMAGE_STORAGE_FAILED",
            message="Không thể lưu ảnh lên máy chủ.",
        ) from exc

    image_url = f"/api/v1/parking/sessions/{tx.id}/images/{direction}/{filename}"

    old_image_url = tx.image_url if direction == "entry" else None

    if direction == "entry":
        tx.image_url = image_url

    try:
        log_action(
            db=db,
            user_id=current_user.id,
            action="UPLOAD_SESSION_IMAGE",
            entity_type="ParkingTransaction",
            entity_id=str(tx.id),
            old_value={"image_url": old_image_url},
            new_value={
                "direction": direction,
                "image_url": image_url,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        image_path.unlink(missing_ok=True)
        raise

    return {"image_url": image_url}


@router.get("/sessions/{session_id}/images/{direction}/{filename}")
def get_session_image(
    session_id: UUID,
    direction: Literal["entry", "exit"],
    filename: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(
        require_roles(
            RoleName.OPERATOR,
            RoleName.SYSTEM_ADMIN,
            RoleName.BUILDING_ADMIN,
            RoleName.ACCOUNTANT,
        )
    ),
):
    tx = db.get(ParkingTransaction, session_id)

    if tx is None or not _IMAGE_FILENAME.fullmatch(filename):
        raise AppError(
            status_code=404,
            code="IMAGE_NOT_FOUND",
            message="Không tìm thấy ảnh.",
        )

    path = (
        media_root(settings.local_storage_path)
        / "parking_sessions"
        / str(tx.building_id)
        / str(tx.id)
        / direction
        / filename
    )

    if not path.is_file():
        raise AppError(
            status_code=404,
            code="IMAGE_NOT_FOUND",
            message="Ảnh không tồn tại trên máy chủ.",
        )

    media_type = "image/png" if filename.endswith(".png") else "image/jpeg"

    return FileResponse(
        path,
        media_type=media_type,
        headers={"Cache-Control": "private, no-store"},
    )
