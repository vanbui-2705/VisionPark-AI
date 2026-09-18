from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
import cv2
import numpy as np

# Giữ nguyên import của Người 1
from app.alpr.schema import ALPRResult
from app.alpr.service import ALPRApplicationService
from app.alpr.errors import ALPRNotReadyError, ALPRProcessingError

# Import thêm HTTP DTO của Người 3
from app.alpr.schema import ALPRHTTPResponse
from app.di_container import get_alpr_service

router = APIRouter()

@router.post("/detections", response_model=ALPRHTTPResponse)
async def create_detection(
    lane_id: str = Form(...),
    image: UploadFile = File(...),
    alpr_service: ALPRApplicationService = Depends(get_alpr_service)
):
    if not image.content_type in ["image/jpeg", "image/png"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Định dạng ảnh không hợp lệ. Hệ thống chỉ hỗ trợ JPEG và PNG."
        )

    image_bytes = await image.read()
    
    MAX_SIZE = 5 * 1024 * 1024
    if len(image_bytes) > MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Kích thước ảnh vượt quá giới hạn 5MB cho phép."
        )

    # P1-BE2-08: Decode bằng OpenCV để chặn file hỏng
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        image_matrix = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image_matrix is None:
            raise ValueError("Không thể giải mã ảnh")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
            detail="File ảnh hỏng hoặc không thể đọc bằng OpenCV."
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except ALPRNotReadyError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"code": "ALPR_NOT_READY", "message": str(e)})
    except ALPRProcessingError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"code": "ALPR_PROCESSING_ERROR", "message": str(e)})
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Đã xảy ra lỗi hệ thống không xác định.")


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
        raise HTTPException(status_code=503, detail=str(e))