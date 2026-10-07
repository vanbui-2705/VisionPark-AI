import os
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Form, Header, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.alpr.errors import ALPRInvalidImageError, ALPRNotReadyError, ALPRProcessingError

# Giữ nguyên import của Người 1
# Import thêm HTTP DTO của Người 3
from app.alpr.schema import ALPRHTTPResponse
from app.alpr.service import ALPRApplicationService
from app.alpr.utils import normalize_plate
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.database.session import get_db
from app.di_container import get_alpr_service
from app.integrations.persistence.database_health import get_database_readiness
from app.modules.alpr.confirmation import confirm_detection as confirm_detection_service
from app.modules.alpr.models import Detection
from app.modules.alpr.schemas import DetectionConfirmRequest, DetectionResponse

#
from app.modules.auth.dependencies import require_roles
from app.modules.checkin.schemas import CheckInResponse
from app.modules.lanes.models import Lane, LaneDirection
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
    capture_id: UUID | None = Form(None),
    input_kind: Literal["IMAGE_UPLOAD", "VIDEO_FRAME"] | None = Form(None),
    video_time_ms: int | None = Form(None, ge=0),
    alpr_service: ALPRApplicationService = Depends(resolve_alpr_service),
    current_user: Annotated[
        User, Depends(require_roles(RoleName.OPERATOR, RoleName.ADMIN, RoleName.TECHNICIAN))
    ] = None,
):
    # 1. Check định dạng
    if image.content_type not in ["image/jpeg", "image/png"]:
        raise AppError(
            status_code=422,
            code="INVALID_FORMAT",
            message="Định dạng ảnh không hợp lệ. Hệ thống chỉ hỗ trợ JPEG và PNG.",
        )

    image_bytes = await image.read()

    actual_type = (
        "image/png"
        if image_bytes.startswith(b"\x89PNG\r\n\x1a\n")
        else "image/jpeg"
        if image_bytes.startswith(b"\xff\xd8\xff")
        else None
    )
    if actual_type != image.content_type:
        raise AppError(
            status_code=422,
            code="INVALID_FORMAT",
            message="Image content must match JPEG/PNG content type.",
        )

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
        should_persist = mode != "preview" if persist is None else persist
        if capture_id and not should_persist:
            raise AppError(
                status_code=422, code="INVALID_CAPTURE", message="Capture ID requires persistence."
            )
        kwargs = {"persist": should_persist, "actor_id": str(current_user.id)}
        if capture_id:
            kwargs["capture_id"] = str(capture_id)
        if input_kind:
            kwargs.update(
                input_kind=input_kind, video_time_ms=video_time_ms, actor_id=str(current_user.id)
            )
        result = await run_in_threadpool(
            alpr_service.process_detection, image_bytes, lane_id, **kwargs
        )

        # P1-BE2-10: Mapping dữ liệu trước khi trả về
        raw_plate = result.raw_plate if isinstance(result.raw_plate, str) else result.plate_number
        normalized = (
            result.normalized_plate
            if isinstance(result.normalized_plate, str)
            else normalize_plate(raw_plate)
            if raw_plate
            else None
        )

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
                result.provider_status if isinstance(result.provider_status, str) else "ready"
            ),
            detector_latency_ms=result.detector_latency_ms,
            ocr_latency_ms=result.ocr_latency_ms,
            input_kind=result.input_kind,
            video_time_ms=result.video_time_ms,
            actor_id=result.actor_id,
        )

    except AppError:
        raise
    except ALPRInvalidImageError as e:
        raise AppError(status_code=422, code="CORRUPTED_IMAGE", message=str(e)) from e
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

        return FileResponse(
            file_path,
            media_type="image/png" if image_key.lower().endswith(".png") else "image/jpeg",
        )
    except AppError:
        raise
    except Exception:
        from app.core.errors import AppError

        raise AppError(
            status_code=400,
            code="BAD_REQUEST",
            message="Image key không hợp lệ",
        ) from None


@router.get("/detections", response_model=list[DetectionResponse] | dict)
def get_detection_history(
    request: Request,
    lane_id: UUID | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    page: int | None = Query(None, ge=0),
    pageSize: int | None = Query(None, ge=1, le=100),
    q: str | None = None,
    paginated: bool = False,
    input_kind: str | None = None,
    min_confidence: float | None = Query(None, ge=0, le=1),
    max_confidence: float | None = Query(None, ge=0, le=1),
    direction: LaneDirection | None = None,
    status: Literal["DETECTED", "NEEDS_CONFIRMATION", "CONFIRMED", "CORRECTED", "NO_PLATE"]
    | None = None,
    from_time: Annotated[datetime | None, Query(alias="from")] = None,
    to_time: Annotated[datetime | None, Query(alias="to")] = None,
    db: Session = Depends(get_db),
    # Yêu cầu phải đăng nhập mới xem được lịch sử
    current_user: Annotated[
        User, Depends(require_roles(RoleName.OPERATOR, RoleName.ADMIN, RoleName.TECHNICIAN))
    ] = None,
):
    """API lấy danh sách lịch sử nhận diện (có phân trang và lọc theo làn)."""
    del current_user
    is_paginated = (
        paginated
        or ("page" in request.query_params)
        or ("pageSize" in request.query_params)
        or (request.query_params.get("format") == "paginated")
    )
    eff_page_size = pageSize if pageSize is not None else limit
    eff_page = page if page is not None else (skip // max(1, eff_page_size) if skip else 0)
    eff_skip = eff_page * eff_page_size if page is not None else skip

    query = select(Detection).order_by(Detection.created_at.desc(), Detection.id.desc())

    if lane_id:
        query = query.where(Detection.lane_id == lane_id)
    if input_kind:
        query = query.where(Detection.input_kind == input_kind)
    if min_confidence is not None:
        query = query.where(Detection.confidence >= min_confidence)
    if max_confidence is not None:
        query = query.where(Detection.confidence <= max_confidence)
    if q:
        clean_q = normalize_plate(q) or q
        query = query.where(
            or_(
                Detection.raw_plate.ilike(f"%{q}%"),
                Detection.normalized_plate.ilike(f"%{clean_q}%"),
                Detection.confirmed_plate.ilike(f"%{clean_q}%"),
            )
        )
    if direction:
        query = query.join(Detection.lane).where(
            or_(
                Detection.direction_snapshot == direction.value,
                (Detection.direction_snapshot.is_(None)) & (Lane.direction == direction),
            )
        )
    if from_time:
        query = query.where(Detection.created_at >= from_time)
    if to_time:
        query = query.where(Detection.created_at <= to_time)
    if status == "NO_PLATE":
        query = query.where(Detection.normalized_plate.is_(None), Detection.is_confirmed.is_(False))
    elif status == "NEEDS_CONFIRMATION":
        query = query.where(
            Detection.requires_confirmation.is_(True),
            Detection.is_confirmed.is_(False),
            Detection.normalized_plate.is_not(None),
        )
    elif status == "DETECTED":
        query = query.where(
            Detection.is_confirmed.is_(False),
            Detection.requires_confirmation.is_(False),
            Detection.normalized_plate.is_not(None),
        )
    elif status in ("CONFIRMED", "CORRECTED"):
        query = query.where(Detection.is_confirmed.is_(True))
        same_plate = Detection.confirmed_plate == Detection.normalized_plate
        query = query.where(
            same_plate
            if status == "CONFIRMED"
            else or_(~same_plate, Detection.normalized_plate.is_(None))
        )

    detections = db.scalars(query.offset(eff_skip).limit(eff_page_size)).all()
    if is_paginated:
        total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
        total_pages = max(1, (total + eff_page_size - 1) // eff_page_size)
        return {
            "items": [
                DetectionResponse.model_validate(d).model_dump(mode="json") for d in detections
            ],
            "total": total,
            "page": eff_page,
            "pageSize": eff_page_size,
            "totalPages": total_pages,
            "limit": eff_page_size,
            "offset": eff_skip,
        }
    return detections


@router.get("/detections/{detection_id}", response_model=DetectionResponse)
def get_detection(
    detection_id: UUID,
    db: Session = Depends(get_db),
    current_user: Annotated[
        User, Depends(require_roles(RoleName.OPERATOR, RoleName.ADMIN, RoleName.TECHNICIAN))
    ] = None,
):
    detection = db.get(Detection, detection_id)
    if detection is None:
        raise AppError(status_code=404, code="NOT_FOUND", message="Detection not found.")
    return detection


@router.post(
    "/detections/{detection_id}/confirm", response_model=DetectionResponse | CheckInResponse
)
def confirm_detection(
    detection_id: UUID,
    payload: DetectionConfirmRequest,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    db: Session = Depends(get_db),
    # Station operators and technicians may confirm detections.
    current_user: Annotated[
        User, Depends(require_roles(RoleName.OPERATOR, RoleName.ADMIN, RoleName.TECHNICIAN))
    ] = None,
):
    """Confirm or correct a detected plate for an authorized Station user."""
    detection = db.scalar(select(Detection).where(Detection.id == detection_id))
    if not detection:
        from app.core.errors import AppError

        raise AppError(
            status_code=404,
            code="NOT_FOUND",
            message="Không tìm thấy bản ghi nhận diện",
        )

    return confirm_detection_service(db, detection, payload, current_user, idempotency_key)
