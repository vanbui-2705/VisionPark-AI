import os
<<<<<<< HEAD
from typing import Annotated
=======
from typing import Annotated, Literal
>>>>>>> main
from uuid import UUID

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.alpr.errors import ALPRInvalidImageError, ALPRNotReadyError, ALPRProcessingError

# Giữ nguyên import của Người 1
# Import thêm HTTP DTO của Người 3
from app.alpr.schema import ALPRHTTPResponse, ALPRResult
from app.alpr.service import ALPRApplicationService
from app.alpr.utils import normalize_plate
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.database.session import get_db
from app.di_container import get_alpr_service
from app.integrations.persistence.database_health import get_database_readiness
from app.modules.alpr.models import Detection
from app.modules.alpr.schemas import DetectionConfirmRequest, DetectionResponse
from app.modules.audit_logs.service import log_action

#
from app.modules.auth.dependencies import require_roles
from app.modules.users.models import User
from app.modules.users.schemas import RoleName

router = APIRouter()

_DEFAULT_ALPR_FACTORY = get_alpr_service


def resolve_alpr_service(
    request: Request,
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ALPRApplicationService:
    """Resolve the service while keeping the endpoint factory replaceable in tests."""
    if get_alpr_service is not _DEFAULT_ALPR_FACTORY:
        return get_alpr_service()
    return get_alpr_service(request=request, session=session, settings=settings)


@router.post("/detections", response_model=ALPRHTTPResponse)
async def create_detection(
    lane_id: str = Form(...),
    image: UploadFile = File(...),
    mode: Literal["preview", "final"] = Form("preview"),
    persist: bool | None = Form(None),
    alpr_service: ALPRApplicationService = Depends(resolve_alpr_service),
    current_user: Annotated[User, Depends(require_roles(RoleName.OPERATOR, RoleName.ADMIN))] = None,
):
    # 1. Check định dạng
    if image.content_type not in ["image/jpeg", "image/png"]:
        raise AppError(
            status_code=422,
            code="INVALID_FORMAT",
            message="Định dạng ảnh không hợp lệ. Hệ thống chỉ hỗ trợ JPEG và PNG.",
        )

    image_bytes = await image.read()

    # 2. Check dung lượng
    MAX_SIZE = 5 * 1024 * 1024
    if len(image_bytes) > MAX_SIZE:
        raise AppError(
            status_code=422,
            code="FILE_TOO_LARGE",
            message="Kích thước ảnh vượt quá giới hạn 5MB cho phép.",
        )

    # 3. Decode bằng OpenCV để chặn file hỏng
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        image_matrix = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image_matrix is None:
            raise ValueError("Không thể giải mã ảnh")
    except Exception:
        raise AppError(
            status_code=422,
            code="CORRUPTED_IMAGE",
            message="Ảnh tải lên bị hỏng hoặc không thể giải mã.",
        ) from None

    try:
<<<<<<< HEAD
        result: ALPRResult = alpr_service.process_detection(image_bytes, lane_id)

        # P1-BE2-10: Mapping dữ liệu trước khi trả về
        raw_plate = result.plate_number
        normalized = None
        if raw_plate:
            normalized = raw_plate.replace("-", "").replace(".", "").replace(" ", "").strip()
=======
        should_persist = mode != "preview" if persist is None else persist
        if should_persist is True and mode == "final" and persist is None:
            # Keep compatibility with lightweight service doubles used by the
            # existing API tests and integrations.
            result: ALPRResult = alpr_service.process_detection(image_bytes, lane_id)
        else:
            result = alpr_service.process_detection(
                image_bytes, lane_id, persist=should_persist
            )

        # P1-BE2-10: Mapping dữ liệu trước khi trả về
        raw_plate = result.raw_plate if isinstance(result.raw_plate, str) else result.plate_number
        normalized = (
            result.normalized_plate
            if isinstance(result.normalized_plate, str)
            else normalize_plate(raw_plate) if raw_plate else None
        )
>>>>>>> main

        bbox_list = list(result.bbox.as_tuple) if result.bbox else [0, 0, 0, 0]
        model_version = result.model_version if isinstance(result.model_version, str) else "unknown"
        detection_id = result.detection_id if isinstance(result.detection_id, str) else None
        combined_confidence = (
            result.combined_confidence
            if result.combined_confidence is not None
            else result.confidence
        )

        return ALPRHTTPResponse(
            raw_plate=raw_plate,
            normalized_plate=normalized,
            bbox=bbox_list,
            confidence=result.confidence,
            latency_ms=result.processing_time_ms,
            model_version=model_version,
            requires_confirmation=result.requires_confirmation,
            detection_id=detection_id,
            raw_plate_number=raw_plate,
            normalized_plate_number=normalized,
            processing_time_ms=result.processing_time_ms,
            detector_confidence=result.detector_confidence,
            ocr_confidence=result.ocr_confidence,
            combined_confidence=combined_confidence,
            quality_flags=result.quality_flags,
            provider=result.provider if isinstance(result.provider, str) else "unknown",
            provider_status=(
                result.provider_status
                if isinstance(result.provider_status, str)
                else "ready"
            ),
            detector_latency_ms=result.detector_latency_ms,
            ocr_latency_ms=result.ocr_latency_ms,
        )

<<<<<<< HEAD
=======
    except ALPRInvalidImageError as e:
        raise AppError(status_code=422, code="CORRUPTED_IMAGE", message=str(e)) from e
>>>>>>> main
    except ValueError as ve:
        raise AppError(status_code=404, code="NOT_FOUND", message=str(ve)) from ve
    except ALPRNotReadyError as e:
        raise AppError(status_code=503, code="DEPENDENCY_UNAVAILABLE", message=str(e)) from e
    except ALPRProcessingError as e:
        raise AppError(status_code=503, code="ALPR_PROCESSING_ERROR", message=str(e)) from e
    except TimeoutError as e:
        raise AppError(
            status_code=503,
            code="ALPR_PROCESSING_ERROR",
            message=str(e),
        ) from e
    except Exception:
        raise AppError(
            status_code=500,
            code="INTERNAL_SERVER_ERROR",
            message="Đã xảy ra lỗi hệ thống không xác định.",
        ) from None


@router.get("/health/live")
async def alpr_live_health():
    """Liveness probe - chỉ cần endpoint còn chạy là healthy."""
    return {"status": "alive"}


@router.get("/health/ready")
async def alpr_ready_health(
    database_status=Depends(get_database_readiness),
    alpr_service: ALPRApplicationService = Depends(resolve_alpr_service),
):
    """Readiness probe - kiểm tra DB và AI runtime."""
    if not database_status.ready:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "database": database_status.to_dict(),
                "alpr": {"status": "unknown", "message": "Database is not ready."},
            },
        )
    ready, message = alpr_service.runtime.is_ready()
    if not ready:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "database": database_status.to_dict(),
                "alpr": {
                    "status": "not_ready",
                    "message": message,
                    "provider": getattr(alpr_service.runtime, "version", None),
                },
            },
        )
    return {
        "status": "ready",
        "checks": {
            "database": "ok",
            "alpr_runtime": f"ok ({alpr_service.runtime.version})",
        },
    }


@router.get("/media/{image_key}")
async def get_detection_image(image_key: str):
    """API lấy ảnh (Media Serve) để hiển thị lên UI."""
    settings = get_settings()
    try:
        lane_id = image_key.split("_")[0]
        file_path = os.path.join(settings.local_storage_path, lane_id, image_key)

        if not os.path.exists(file_path):
            from app.core.errors import AppError

            raise AppError(status_code=404, code="NOT_FOUND", message="Không tìm thấy file ảnh")

        return FileResponse(file_path, media_type="image/jpeg")
    except AppError:
        raise
    except Exception:
        from app.core.errors import AppError

        raise AppError(
            status_code=400,
            code="BAD_REQUEST",
            message="Image key không hợp lệ",
        ) from None


@router.get("/detections", response_model=list[DetectionResponse])
def get_detection_history(
    lane_id: str | None = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    # Yêu cầu phải đăng nhập mới xem được lịch sử
    current_user: Annotated[User, Depends(require_roles(RoleName.OPERATOR, RoleName.ADMIN))] = None,
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
    current_user: Annotated[User, Depends(require_roles(RoleName.OPERATOR, RoleName.ADMIN))] = None,
):
    """API Nhân viên (Operator) xác nhận và sửa biển số bằng tay."""
    detection = db.scalar(select(Detection).where(Detection.id == detection_id))
    if not detection:
        from app.core.errors import AppError

        raise AppError(
            status_code=404,
            code="NOT_FOUND",
            message="Không tìm thấy bản ghi nhận diện",
        )

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
        new_value={"plate": payload.confirmed_plate},
    )

    db.commit()
    db.refresh(detection)

    return detection
