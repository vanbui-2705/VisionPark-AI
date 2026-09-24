from .interface import ALPRRuntime
from .ports.detection_recorder import DetectionRecorder
from .ports.image_storage import ImageStorage
from .ports.lane_checker import ActiveLaneChecker
from .schema import ALPRResult


class ALPRApplicationService:
    """
    Điều phối toàn bộ luồng use case (use case flow) của hệ thống ALPR:
    1. Kiểm tra tính hợp lệ của làn xe.
    2. Gọi Runtime AI ONNX để nhận diện biển số.
    3. Lưu lại ảnh gốc vào kho lưu trữ (Storage).
    4. Ghi nhận kết quả nhận diện xuống cơ sở dữ liệu.
    """

    def __init__(
        self,
        runtime: ALPRRuntime,
        lane_checker: ActiveLaneChecker,
        image_storage: ImageStorage,
        detection_recorder: DetectionRecorder,
    ):
        self.runtime = runtime
        self.lane_checker = lane_checker
        self.image_storage = image_storage
        self.detection_recorder = detection_recorder

    def process_detection(self, image_bytes: bytes, lane_id: str) -> ALPRResult:
        # 1. Xác thực làn xe (Validate lane)
        if not self.lane_checker.check_active_lane(lane_id):
            raise ValueError(f"Làn xe {lane_id} không tồn tại hoặc đang không hoạt động.")

        # 2. Gọi AI Runtime
        # Sẽ văng ra lỗi ALPRNotReadyError hoặc ALPRProcessingError nếu AI có vấn đề
        result = self.runtime.detect_and_read(image_bytes)

        # 3. Lưu ảnh (Persist Image)
        image_key = self.image_storage.save_image(image_bytes, lane_id)

        # 4. Ghi nhận lịch sử (Record Detection)
        try:
            self.detection_recorder.record_detection(lane_id, image_key, result)
        except Exception:
            self.image_storage.delete_image(image_key, lane_id)
            raise

        return result
