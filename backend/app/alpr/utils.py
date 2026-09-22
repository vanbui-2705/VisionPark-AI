import re

import numpy as np


def decode_image(image_bytes: bytes) -> np.ndarray:
    """
    Giải mã mảng byte thô thành mảng numpy (numpy array) để OpenCV xử lý.
    Sử dụng cv2.imdecode.
    """
    import cv2

    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img


def normalize_plate(plate: str) -> str:
    """
    Chuẩn hóa chuỗi biển số xe: chuyển thành chữ in hoa
    và xóa bỏ các ký tự không phải là chữ cái hoặc số (khoảng trắng, dấu chấm, dấu gạch).
    """
    if not plate:
        return ""
    # Chỉ giữ lại chữ cái A-Z và số 0-9
    return re.sub(r"[^A-Z0-9]", "", plate.upper())


def clamp_bbox(
    bbox: tuple[int, int, int, int], img_width: int, img_height: int
) -> tuple[int, int, int, int]:
    """
    Giới hạn tọa độ bounding box (kẹp giá trị) để đảm bảo không bị vượt ra khỏi kích thước ảnh.
    Định dạng bbox: (x1, y1, x2, y2)
    """
    x1, y1, x2, y2 = bbox
    x1 = max(0, min(x1, img_width - 1))
    y1 = max(0, min(y1, img_height - 1))
    x2 = max(0, min(x2, img_width))
    y2 = max(0, min(y2, img_height))
    return x1, y1, x2, y2


def crop_plate(image: np.ndarray, bbox: tuple[int, int, int, int]) -> np.ndarray:
    """
    Cắt riêng phần biển số ra khỏi ảnh dựa trên bounding box.
    """
    x1, y1, x2, y2 = bbox
    return image[y1:y2, x1:x2]


def resize_for_inference(image: np.ndarray, target_size: tuple[int, int]) -> np.ndarray:
    """
    Chỉnh lại kích thước ảnh (resize) cho đúng với kích thước đầu vào mà model ONNX yêu cầu.
    target_size: (chiều_rộng, chiều_cao)
    """
    import cv2

    return cv2.resize(image, target_size)
