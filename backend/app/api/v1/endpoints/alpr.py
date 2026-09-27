from fastapi import APIRouter, UploadFile, File, Form, Depends, status
from typing import List, Optional, Annotated
from app.core.errors import AppError
import cv2
import numpy as np

import os
from fastapi.responses import FileResponse
from app.core.config import get_settings

# Giữ nguyên import của Người 1
from app.alpr.schema import ALPRResult
from app.alpr.service import ALPRApplicationService
from app.alpr.errors import ALPRNotReadyError, ALPRProcessingError
#
from app.modules.auth.dependencies import require_roles
from app.modules.users.models import User
from app.modules.users.schemas import RoleName

# Import thêm HTTP DTO của Người 3
from app.alpr.schema import ALPRHTTPResponse
from app.di_container import get_alpr_service

from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID
from app.database.session import get_db
from app.modules.alpr.models import Detection
from app.modules.alpr.schemas import DetectionResponse, DetectionConfirmRequest

from app.modules.audit_logs.service import log_action

router = APIRouter()

@router.post("/detections", response_model=ALPRHTTPResponse)
async def create_detection(
    lane_id: str = Form(...),
    image: UploadFile = File(...),
    alpr_service: ALPRApplicationService = Depends(get_alpr_service),
    current_user: Annotated[User, Depends(require_roles(RoleName.OPERATOR, RoleName.ADMIN))] = None
):
    # 1. Check định dạng
    if image.content_type not in ["image/jpeg", "image/png"]:
        raise AppError(
            status_code=422,
            code="INVALID_FORMAT",
            message="Định dạng ảnh không hợp lệ. Hệ thống chỉ hỗ trợ JPEG và PNG."
        )

    image_bytes = await image.read()
    
    # 2. Check dung lượng
    MAX_SIZE = 5 * 1024 * 1024
    if len(image_bytes) > MAX_SIZE:
        raise AppError(
            status_code=422,
            code="FILE_TOO_LARGE",
            message="Kích thước ảnh vượt quá giới hạn 5MB cho phép."
        )

    # 3. Decode bằng OpenCV để chặn file hỏng
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        image_matrix = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image_matrix is None:
            raise ValueError("Không thể giải mã ảnh")
    except Exception as e:
        raise AppError(
            status_code=422,
            code="CORRUPTED_IMAGE",
            message="Ảnh tải lên bị hỏng hoặc không thể giải mã."
        )

    try:
        result: ALPRResult = alpr_service.process_detection(image_bytes, lane_id)
        
        # P1-BE2-10: Mapping dữ liệu trước khi trả về
        raw_plate = result.plate_number
        normalized = None
        if raw_plate:
            normalized = raw_plate.replace("-", "").replace(".", "").replace(" ", "").strip()
            
        bbox_list = list(result.bbox.as_tuple) if result.bbox else [0, 0, 0, 0]

        return ALPRHTTPResponse(
            raw_plate=raw_plate,
            normalized_plate=normalized,
            bbox=bbox_list,
            confidence=result.confidence,
            latency_ms=result.processing_time_ms,
            model_version="v1.0" 
        )
        
    except ValueError as ve:
        raise AppError(
            status_code=404,
            code="NOT_FOUND",
            message=str(ve)
        )
    except ALPRNotReadyError as e:
        raise AppError(
            status_code=503,
            code="DEPENDENCY_UNAVAILABLE",
            message=str(e)
        )
    except ALPRProcessingError as e:
        raise AppError(
            status_code=503,
            code="ALPR_PROCESSING_ERROR",
            message=str(e)
        )
    except Exception as e:
        raise AppError(
            status_code=500,
            code="INTERNAL_SERVER_ERROR",
            message="Đã xảy ra lỗi hệ thống không xác định."
        )


@router.get("/health/live")
async def alpr_live_health():
    """Liveness probe - chỉ cần endpoint còn chạy là healthy."""
    return {"status": "alive"}

@router.get("/health/ready")
async def alpr_ready_health(alpr_service: ALPRApplicationService = Depends(get_alpr_service)):
    """Readiness probe - kiểm tra DB và AI runtime."""
    try:
        _ = alpr_service.runtime.version
        return {
            "status": "ready",
            "checks": {
                "database": "ok",
                "alpr_runtime": f"ok ({alpr_service.runtime.version})"
            }
        }
    except Exception as e:
        raise AppError(
            status_code=503,
            code="DEPENDENCY_UNAVAILABLE",
            message=str(e)
        )

@router.get("/media/{image_key}")
async def get_detection_image(image_key: str):
    """API lấy ảnh (Media Serve) để hiển thị lên UI."""
    settings = get_settings()
    # Image key có format: {lane_id}_{uuid}.jpg
    try:
        lane_id = image_key.split("_")[0]
        # Đường dẫn file ảnh thực tế trên server
        file_path = os.path.join(settings.local_storage_path, lane_id, image_key)
        
        if not os.path.exists(file_path):
            from app.core.errors import AppError
            raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy file ảnh")
            
        return FileResponse(file_path, media_type="image/jpeg")
    except Exception as e:
        from app.core.errors import AppError
        raise AppError(status_code=400, code="BAD_REQUEST", message="Image key không hợp lệ")

@router.get("/detections", response_model=List[DetectionResponse])
def get_detection_history(
    lane_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    # Yêu cầu phải đăng nhập mới xem được lịch sử
    current_user: Annotated[User, Depends(require_roles(RoleName.OPERATOR, RoleName.ADMIN))] = None
):
    """API lấy danh sách lịch sử nhận diện (có phân trang và lọc theo làn)."""
    query = select(Detection).order_by(Detection.created_at.desc())
    
    if lane_id:
        query = query.where(Detection.lane_id == lane_id)
        
    detections = db.scalars(query.offset(skip).limit(limit)).all()
    return detections


@router.post("/detections/{detection_id}/confirm", response_model=DetectionResponse)
def confirm_detection(
    detection_id: UUID,
    payload: DetectionConfirmRequest,
    db: Session = Depends(get_db),
    # Yêu cầu quyền OPERATOR (Nhân viên) hoặc ADMIN để xác nhận
    current_user: Annotated[User, Depends(require_roles(RoleName.OPERATOR, RoleName.ADMIN))] = None
):
    """API Nhân viên (Operator) xác nhận và sửa biển số bằng tay."""
    detection = db.scalar(select(Detection).where(Detection.id == detection_id))
    if not detection:
        from app.core.errors import AppError
        raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy bản ghi nhận diện")
        
    # Cập nhật thông tin xác nhận
    detection.is_confirmed = True
    detection.confirmed_plate = payload.confirmed_plate
    detection.confirmed_by_id = current_user.id

    # Ghi vết hành động sửa biển số
    log_action(
        db=db,
        user_id=current_user.id,
        action="CONFIRM_PLATE",
        entity_type="Detection",
        entity_id=str(detection.id),
        old_value={"plate": detection.raw_plate},
        new_value={"plate": payload.confirmed_plate}
    )

    db.commit()
    db.refresh(detection)
    
    return detection
