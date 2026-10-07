from abc import ABC, abstractmethod

from ..schema import ALPRResult


class DetectionRecorder(ABC):
    """Cổng (Port) dùng để lưu lại kết quả nhận diện xuống database."""

    @abstractmethod
    def record_detection(
        self,
        lane_id: str,
        image_key: str,
        result: ALPRResult,
        *,
        capture_id: str | None = None,
        capture_fingerprint: str | None = None,
    ) -> str:
        """
        Lưu lại kết quả nhận diện, liên kết với ID ảnh và ID làn xe.
        Tham số:
            lane_id: ID của làn xe.
            image_key: Storage key do ImageStorage trả về.
            result: Kết quả ALPRResult đầu ra của mô hình AI.
        Trả về:
            Chuỗi (String) đại diện cho ID của bản ghi detection.
        """
        pass

    def get_capture(self, capture_id: str, fingerprint: str) -> ALPRResult | None:
        raise NotImplementedError("This recorder does not support idempotent captures.")
