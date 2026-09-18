from uuid import UUID
from typing import List, Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.database.session import get_db
from app.modules.auth.dependencies import require_roles
from app.modules.users.models import User
from app.modules.users.schemas import RoleName
from app.modules.lanes import schemas, service

router = APIRouter(prefix="/lanes", tags=["lanes"])


@router.post("/", response_model=schemas.LaneResponse)
def create_lane(
    lane: schemas.LaneCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleName.ADMIN))],
):
    """Tạo mới lane (chỉ Admin)."""
    return service.create_lane(db, lane)


@router.get("/", response_model=List[schemas.LaneResponse])
def list_lanes(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleName.ADMIN))],
):
    """Liệt kê tất cả lane (Admin)."""
    return service.list_lanes(db)


@router.get("/active", response_model=List[schemas.LaneResponse])
def list_active_lanes(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleName.ADMIN))],
):
    """Liệt kê lane đang active (Admin)."""
    return service.list_active_lanes(db)


@router.get("/{lane_id}", response_model=schemas.LaneResponse)
def get_lane(
    lane_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleName.ADMIN))],
):
    """Lấy chi tiết lane theo ID (Admin)."""
    return service.get_lane(db, lane_id)


@router.patch("/{lane_id}", response_model=schemas.LaneResponse)
def update_lane(
    lane_id: UUID,
    lane_update: schemas.LaneUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleName.ADMIN))],
):
    """Cập nhật lane (chỉ Admin)."""
    return service.update_lane(db, lane_id, lane_update)


@router.post("/{lane_id}/deactivate", response_model=schemas.LaneResponse)
def deactivate_lane(
    lane_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleName.ADMIN))],
):
    """Inactive lane (chỉ Admin)."""
    return service.deactivate_lane(db, lane_id)