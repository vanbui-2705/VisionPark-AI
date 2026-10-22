import hashlib
import time
from collections.abc import Callable
from typing import Any

from .interface import ALPRRuntime
from .ports.detection_recorder import DetectionRecorder
from .ports.image_storage import ImageStorage
from .ports.lane_checker import ActiveLaneChecker
from .schema import ALPRResult


class ALPRApplicationService:
    """
    Điều phối toàn bộ luồng use case (use case flow) của hệ thống ALPR:
    1. Kiểm tra tính hợp lệ của làn xe.
    2. Gọi ALPR runtime được cấu hình để nhận diện biển số & loại xe.
    3. Áp dụng bộ lọc khử trùng debounce (SPEC-AI-04).
    4. Lưu lại ảnh gốc vào kho lưu trữ (Storage).
    5. Ghi nhận kết quả nhận diện xuống cơ sở dữ liệu.
    """

    def __init__(
        self,
        runtime: ALPRRuntime,
        lane_checker: ActiveLaneChecker,
        image_storage: ImageStorage,
        detection_recorder: DetectionRecorder,
        *,
        debounce_window_seconds: float = 5.0,
        review_policy: Callable[[str, ALPRResult], ALPRResult] | None = None,
    ):
        self.runtime = runtime
        self.lane_checker = lane_checker
        self.image_storage = image_storage
        self.detection_recorder = detection_recorder
        self.debounce_window_seconds = debounce_window_seconds
        self._cooldown_cache: dict[tuple[str, str], tuple[float, str]] = {}
        self.review_policy = review_policy

    def process_detection(
        self,
        image_bytes: bytes,
        lane_id: str,
        *,
        persist: bool = True,
        capture_id: str | None = None,
        input_kind: str | None = None,
        video_time_ms: int | None = None,
        actor_id: str | None = None,
        settings: dict[str, Any] | None = None,
        building_id: str | None = None,
    ) -> ALPRResult:
        # 1. Xác thực làn xe (Validate lane)
        if not self.lane_checker.check_active_lane(lane_id):
            raise ValueError(f"Làn xe {lane_id} không tồn tại hoặc đang không hoạt động.")

        fingerprint = hashlib.sha256(
            lane_id.encode()
            + b"\0"
            + str(input_kind).encode()
            + b"\0"
            + str(video_time_ms).encode()
            + b"\0"
            + image_bytes
        ).hexdigest()
        if capture_id and persist:
            existing = self.detection_recorder.get_capture(capture_id, fingerprint)
            if existing is not None:
                return existing

        # 2. Gọi AI Runtime (hỗ trợ cả runtime mới nhận settings và mock runtime cũ)
        merged_settings = dict(settings or {})
        if building_id:
            merged_settings["building_id"] = building_id

        try:
            raw_result = self.runtime.detect_and_read(image_bytes, merged_settings)
        except TypeError:
            raw_result = self.runtime.detect_and_read(image_bytes)

        result = raw_result.model_copy(
            update={
                "input_kind": input_kind,
                "video_time_ms": video_time_ms,
                "actor_id": actor_id,
                "image_size_bytes": len(image_bytes),
                "building_id": building_id or merged_settings.get("building_id") or getattr(raw_result, "building_id", None),
            }
        )

        if self.review_policy is not None:
            result = self.review_policy(lane_id, result)

        if not persist:
            return result.model_copy(update={"detection_id": None})

        # SPEC-AI-04: Station Debounce / Cooldown check
        plate_or_type = result.normalized_plate or result.plate_number or result.vehicle_type
        now = time.time()
        if plate_or_type:
            cache_key = (lane_id, plate_or_type)
            if cache_key in self._cooldown_cache:
                last_time, last_detection_id = self._cooldown_cache[cache_key]
                if now - last_time < self.debounce_window_seconds and not capture_id:
                    # Return recent detection without creating duplicate records
                    return result.model_copy(update={"detection_id": last_detection_id})

        # 3. Lưu ảnh (Persist Image)
        image_key = self.image_storage.save_image(image_bytes, lane_id)

        # 4. Ghi nhận lịch sử (Record Detection)
        try:
            if capture_id:
                detection_id = self.detection_recorder.record_detection(
                    lane_id,
                    image_key,
                    result,
                    capture_id=capture_id,
                    capture_fingerprint=fingerprint,
                )
            else:
                detection_id = self.detection_recorder.record_detection(lane_id, image_key, result)
        except Exception:
            self.image_storage.delete_image(image_key, lane_id)
            raise

        if plate_or_type:
            self._cooldown_cache[(lane_id, plate_or_type)] = (now, detection_id)

        return result.model_copy(update={"detection_id": detection_id})
