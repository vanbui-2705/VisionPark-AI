from uuid import UUID
from sqlalchemy.orm import Session

from app.core.errors import AppError
from . import repository, schemas


def create_lane(db: Session, lane_data: schemas.LaneCreate) -> schemas.LaneResponse:
    """Tạo mới một lane. Kiểm tra duplicate tên trước."""
    
    # 1. Kiểm tra trùng tên
    existing_lane = repository.get_lane_by_name(db, lane_data.name)
    if existing_lane:
        raise AppError(
            status_code=409,
            code="CONFLICT",
            message=f"Lane '{lane_data.name}' đã tồn tại.",
            details={"name": lane_data.name},
        )
    
    # 2. Chuẩn bị data và tạo mới
    lane_dict = lane_data.model_dump()
    db_lane = repository.create_lane(db, lane_dict)
    
    return schemas.LaneResponse.model_validate(db_lane)


def get_lane(db: Session, lane_id: UUID) -> schemas.LaneResponse:
    """Lấy chi tiết một lane theo ID."""
    db_lane = repository.get_lane_by_id(db, lane_id)
    if db_lane is None:
        raise AppError(
            status_code=404,
            code="NOT_FOUND",
            message=f"Không tìm thấy lane với id={lane_id}",
            details={"lane_id": str(lane_id)},
        )
    return schemas.LaneResponse.model_validate(db_lane)


def update_lane(
    db: Session, lane_id: UUID, update_data: schemas.LaneUpdate
) -> schemas.LaneResponse:
    """Cập nhật thông tin lane."""
    db_lane = repository.get_lane_by_id(db, lane_id)
    if db_lane is None:
        raise AppError(
            status_code=404,
            code="NOT_FOUND",
            message=f"Không tìm thấy lane với id={lane_id}",
            details={"lane_id": str(lane_id)},
        )
    
    # Kiểm tra trùng tên nếu có thay đổi tên
    if update_data.name and update_data.name != db_lane.name:
        existing = repository.get_lane_by_name(db, update_data.name)
        if existing and existing.id != lane_id:
            raise AppError(
                status_code=409,
                code="CONFLICT",
                message=f"Lane '{update_data.name}' đã tồn tại.",
                details={"name": update_data.name},
            )
    
    updated = repository.update_lane(db, db_lane, update_data.model_dump(exclude_unset=True))
    return schemas.LaneResponse.model_validate(updated)


def deactivate_lane(db: Session, lane_id: UUID) -> schemas.LaneResponse:
    """Inactive một lane (soft delete)."""
    db_lane = repository.get_lane_by_id(db, lane_id)
    if db_lane is None:
        raise AppError(
            status_code=404,
            code="NOT_FOUND",
            message=f"Không tìm thấy lane với id={lane_id}",
            details={"lane_id": str(lane_id)},
        )
    
    update_data = schemas.LaneUpdate(is_active=False)
    return update_lane(db, lane_id, update_data)


def list_lanes(db: Session) -> list[schemas.LaneResponse]:
    """Liệt kê tất cả lane."""
    lanes = repository.get_all_lanes(db)
    return [schemas.LaneResponse.model_validate(lane) for lane in lanes]


def list_active_lanes(db: Session) -> list[schemas.LaneResponse]:
    """Liệt kê các lane đang active."""
    lanes = repository.list_active_lanes(db)
    return [schemas.LaneResponse.model_validate(lane) for lane in lanes]