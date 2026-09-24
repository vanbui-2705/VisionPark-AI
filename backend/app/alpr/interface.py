from abc import ABC, abstractmethod

from .schema import ALPRResult


class ALPRRuntime(ABC):
    """
    Abstract Base Class định nghĩa giao diện (interface) cho runtime nhận diện ALPR.
    Bất kỳ implementation nào (như OnnxALPRRuntime) cũng phải tuân theo các hàm này.
    """

    @abstractmethod
    def is_ready(self) -> tuple[bool, str]:
        """
        Kiểm tra xem runtime đã sẵn sàng để xử lý ảnh chưa (VD: file trọng số đã load thành công).
        Trả về:
            (is_ready: bool, message: str)
        """
        pass

    @abstractmethod
    def detect_and_read(self, image_bytes: bytes) -> ALPRResult:
        """
        Xử lý ảnh đầu vào và trả về kết quả ALPR.

        Tham số:
            image_bytes: Chuỗi byte thô của ảnh (JPEG/PNG)

        Trả về:
            ALPRResult chứa biển số xe, bounding box, và độ tin cậy.

        Ngoại lệ (Raises):
            ALPRNotReadyError: Nếu model chưa sẵn sàng/chưa load.
            ALPRProcessingError: Nếu gặp sự cố trong lúc giải mã OpenCV hoặc Inference bằng ONNX.
        """
        pass
