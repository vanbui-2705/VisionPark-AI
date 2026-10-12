from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.auth.dependencies import CurrentUser, require_roles
from app.modules.lanes import schemas, service
from app.modules.users.models import User
from app.modules.users.schemas import RoleName

router = APIRouter(prefix="/lanes", tags=["lanes"])


@router.post("/", response_model=schemas.LaneResponse)
def create_lane(
    lane: schemas.LaneCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleName.BUILDING_ADMIN))],
):
    """Tạo mới lane (chỉ Admin)."""
    return service.create_lane(db, lane, admin_id=current_user.id)


@router.get("/", response_model=list[schemas.LaneResponse])
def list_lanes(
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
):
    """Liệt kê tất cả lane cho user đã xác thực."""
    lanes = service.list_lanes(db)
    if current_user.role.name == RoleName.SYSTEM_ADMIN:
        return lanes
    return [lane for lane in lanes if lane.building_id == db.info.get("building_id")]


@router.get("/active", response_model=list[schemas.LaneResponse])
def list_active_lanes(
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
):
    """Liệt kê lane đang active cho user đã xác thực."""
    lanes = service.list_active_lanes(db)
    if current_user.role.name == RoleName.SYSTEM_ADMIN:
        return lanes
    return [lane for lane in lanes if lane.building_id == db.info.get("building_id")]


@router.get("/{lane_id}", response_model=schemas.LaneResponse)
def get_lane(
    lane_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
):
    """Lấy chi tiết lane theo ID cho user đã xác thực."""
    lane = service.get_lane(db, lane_id)
    if (
        current_user.role.name != RoleName.SYSTEM_ADMIN
        and lane.building_id != db.info.get("building_id")
    ):
        from app.core.errors import AppError

        raise AppError(status_code=404, code="NOT_FOUND", message="Lane not found.")
    return lane


@router.patch("/{lane_id}", response_model=schemas.LaneResponse)
def update_lane(
    lane_id: UUID,
    lane_update: schemas.LaneUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleName.BUILDING_ADMIN))],
):
    """Cập nhật lane (chỉ Admin)."""
    return service.update_lane(db, lane_id, admin_id=current_user.id, update_data=lane_update)


@router.post("/{lane_id}/deactivate", response_model=schemas.LaneResponse)
def deactivate_lane(
    lane_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleName.BUILDING_ADMIN))],
):
    """Inactive lane (chỉ Admin)."""
    return service.deactivate_lane(db, lane_id, admin_id=current_user.id)
