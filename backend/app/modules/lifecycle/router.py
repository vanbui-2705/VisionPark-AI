from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.auth.dependencies import require_roles
from app.modules.users.models import User
from app.modules.users.schemas import RoleName

from .schemas import (
    SessionDetailResponse,
    SessionLifecycleFilter,
    SessionListPaginatedResponse,
)
from .service import LifecycleService

router = APIRouter(prefix="/lifecycle", tags=["lifecycle"])

LifecycleViewer = Annotated[
    User,
    Depends(
        require_roles(
            RoleName.BUILDING_ADMIN,
            RoleName.OPERATOR,
            RoleName.ACCOUNTANT,
            RoleName.SYSTEM_ADMIN,
        )
    ),
]


@router.get("/sessions", response_model=SessionListPaginatedResponse)
def list_sessions(
    current_user: LifecycleViewer,
    db: Annotated[Session, Depends(get_db)],
    license_plate: str | None = None,
    ticket_code: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    vehicle_type: str | None = None,
    ticket_kind: str | None = None,
    status: str | None = None,
    lane_id: UUID | None = None,
    has_exception: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> SessionListPaginatedResponse:
    """GET /api/v1/lifecycle/sessions — danh sách lượt xe phân trang và lọc (BR-4.8)."""
    filter_params = SessionLifecycleFilter(
        license_plate=license_plate,
        ticket_code=ticket_code,
        from_time=from_time,
        to_time=to_time,
        vehicle_type=vehicle_type,
        ticket_kind=ticket_kind,
        status=status,
        lane_id=lane_id,
        has_exception=has_exception,
        page=page,
        page_size=page_size,
    )
    service = LifecycleService(db)
    return service.list_sessions(filter_params, current_user)


@router.get("/sessions/export-csv")
def export_sessions_csv(
    current_user: LifecycleViewer,
    db: Annotated[Session, Depends(get_db)],
    license_plate: str | None = None,
    ticket_code: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    vehicle_type: str | None = None,
    ticket_kind: str | None = None,
    status: str | None = None,
    lane_id: UUID | None = None,
    has_exception: bool | None = None,
) -> Response:
    """GET /api/v1/lifecycle/sessions/export-csv — xuất danh sách lượt xe ra CSV (BR-4.8)."""
    filter_params = SessionLifecycleFilter(
        license_plate=license_plate,
        ticket_code=ticket_code,
        from_time=from_time,
        to_time=to_time,
        vehicle_type=vehicle_type,
        ticket_kind=ticket_kind,
        status=status,
        lane_id=lane_id,
        has_exception=has_exception,
        page=1,
        page_size=5000,
    )
    service = LifecycleService(db)
    csv_content = service.export_sessions_csv(filter_params, current_user)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    filename = f"parking_sessions_{timestamp}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
def get_session_detail(
    session_id: UUID,
    current_user: LifecycleViewer,
    db: Annotated[Session, Depends(get_db)],
) -> SessionDetailResponse:
    """GET /api/v1/lifecycle/sessions/{id} — chi tiết lượt xe và timeline (BR-4.8)."""
    service = LifecycleService(db)
    return service.get_session_detail(session_id, current_user)
