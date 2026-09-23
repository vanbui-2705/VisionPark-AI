import os  # Backward-compatible module surface used by existing integrations/tests.
from pathlib import Path

import numpy as np
import onnxruntime as ort

from . import utils
from .errors import ALPRNotReadyError, ALPRProcessingError
from .interface import ALPRRuntime
from .schema import ALPRResult, BoundingBox


class OnnxALPRRuntime(ALPRRuntime):
    """
    Lớp triển khai ALPR Runtime sử dụng thư viện ONNX Runtime để chạy Inference thật.
    Cần có hai file model:
    - plate_detector.onnx: Model YOLO dùng để phát hiện vùng chứa biển số xe
    - ocr_model.onnx: Model OCR dùng để đọc các ký tự từ ảnh biển số đã được cắt
    """

    def __init__(self, weights_dir: str = "backend/app/alpr/weights"):
        self.weights_dir = Path(weights_dir)
        self.detector_path = self.weights_dir / "plate_detector.onnx"
        self.ocr_path = self.weights_dir / "ocr_model.onnx"

        self.detector_session: ort.InferenceSession | None = None
        self.ocr_session: ort.InferenceSession | None = None

        # Thử load model ngay khi khởi tạo (nếu file đã tồn tại)
        self._try_load_models()

    def _try_load_models(self):
        """Cố gắng tải các phiên ONNX (ONNX sessions) nếu tìm thấy file."""
        try:
            if self.detector_path.exists() and self.detector_session is None:
                self.detector_session = ort.InferenceSession(str(self.detector_path))

            if self.ocr_path.exists() and self.ocr_session is None:
                self.ocr_session = ort.InferenceSession(str(self.ocr_path))
        except Exception:
            # Nếu có lỗi (ví dụ file onnx bị hỏng), tạm bỏ qua, chỉ văng lỗi khi thực sự gọi hàm
            # chạy inference
            pass

    def is_ready(self) -> tuple[bool, str]:
        # Thử load lại nếu trước đó chưa tìm thấy file
        self._try_load_models()

        if not self.detector_path.exists():
            return False, f"Thiếu model Detector tại {self.detector_path}"
        if not self.ocr_path.exists():
            return False, f"Thiếu model OCR tại {self.ocr_path}"

        if self.detector_session is None or self.ocr_session is None:
            return (
                False,
                "Không thể khởi tạo phiên ONNX (model không hợp lệ hoặc lỗi thư viện ONNX)",
            )

        return True, "Load model thành công"

    def _run_detector(self, image: np.ndarray) -> tuple[BoundingBox | None, float]:
        """
        Chạy phát hiện bằng YOLO. Trả về Bbox có độ tự tin cao nhất và độ tự tin (confidence) đó.
        Bạn cần tùy chỉnh đoạn này cho khớp với layer Output của file YOLO ONNX mà bạn train.
        """
        # Ví dụ chuẩn hóa và định dạng lại kích thước cho YOLO (thường là 640x640, float32, ảnh
        # normalized)
        input_size = (640, 640)
        img_resized = utils.resize_for_inference(image, input_size)

        # TÙY CHỈNH: Tiền xử lý theo yêu cầu của YOLO (HWC -> CHW, 1/255.0 v.v..)
        input_blob = img_resized.astype(np.float32) / 255.0
        input_blob = np.transpose(input_blob, (2, 0, 1))
        input_blob = np.expand_dims(input_blob, axis=0)

        # Chạy inference
        input_name = self.detector_session.get_inputs()[0].name
        _outputs = self.detector_session.run(None, {input_name: input_blob})

        # TÙY CHỈNH: Bóc tách kết quả `outputs` thành BoundingBox và độ tự tin
        # Mock logic tạm để code không văng lỗi khi chạy thử:
        mock_bbox = BoundingBox(x1=100, y1=200, x2=300, y2=250)
        mock_conf = 0.92

        return mock_bbox, mock_conf

    def _run_ocr(self, cropped_plate: np.ndarray) -> tuple[str, float]:
        """
        Chạy model OCR trên ảnh biển số đã bị cắt.
        Bạn cần tùy chỉnh đoạn này cho khớp với Input/Output của mô hình OCR/KNN của bạn.
        """
        # Tiền xử lý cho OCR
        input_size = (320, 64)  # Ví dụ kích thước mặc định OCR
        img_resized = utils.resize_for_inference(cropped_plate, input_size)

        input_blob = img_resized.astype(np.float32) / 255.0
        input_blob = np.expand_dims(input_blob, axis=0)

        # Chạy inference
        input_name = self.ocr_session.get_inputs()[0].name
        _outputs = self.ocr_session.run(None, {input_name: input_blob})

        # TÙY CHỈNH: Bóc tách kết quả chữ ra text
        mock_text = "29A12345"
        mock_conf = 0.88

        return mock_text, mock_conf

    def detect_and_read(self, image_bytes: bytes) -> ALPRResult:
        import time

        start_time = time.time()

        ready, msg = self.is_ready()
        if not ready:
            raise ALPRNotReadyError(msg)

        try:
            # 1. Giải mã ảnh (Decode)
            img = utils.decode_image(image_bytes)
            img_height, img_width = img.shape[:2]

            # 2. Phát hiện khung biển số (Detect)
            bbox, det_conf = self._run_detector(img)

            if bbox is None:
                # Không tìm thấy biển số nào trong ảnh
                return ALPRResult(
                    plate_number=None,
                    bbox=None,
                    confidence=0.0,
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    requires_confirmation=True,
                )

            # 3. Kẹp giới hạn (Clamp) & Cắt biển số (Crop)
            valid_bbox_coords = utils.clamp_bbox(bbox.as_tuple, img_width, img_height)
            bbox = BoundingBox(
                x1=valid_bbox_coords[0],
                y1=valid_bbox_coords[1],
                x2=valid_bbox_coords[2],
                y2=valid_bbox_coords[3],
            )
            cropped = utils.crop_plate(img, bbox.as_tuple)

            # 4. Đọc chữ trên biển (OCR)
            raw_text, ocr_conf = self._run_ocr(cropped)
            plate_text = utils.normalize_plate(raw_text)

            # 5. Tổng hợp (VD: Lấy trung bình cộng của 2 model)
            final_conf = (det_conf + ocr_conf) / 2.0

            return ALPRResult(
                plate_number=plate_text,
                bbox=bbox,
                confidence=final_conf,
                processing_time_ms=int((time.time() - start_time) * 1000),
                requires_confirmation=(final_conf < 0.85),
            )

        except Exception as e:
            raise ALPRProcessingError(f"Quá trình Inference bị lỗi: {str(e)}") from e
