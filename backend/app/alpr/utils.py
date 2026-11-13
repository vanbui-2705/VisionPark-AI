import re

import cv2
import numpy as np

from .errors import ALPRInvalidImageError

SUPPORTED_IMAGE_CONTENT_TYPES = frozenset({"image/jpeg", "image/png"})
DEFAULT_MAX_IMAGE_BYTES = 5 * 1024 * 1024
DEFAULT_CROP_MARGIN = 0.08
MIN_CROP_WIDTH = 32
MIN_CROP_HEIGHT = 8
# Vietnamese motorcycle and legacy car plates commonly use a near-square two-row layout.
MIN_CROP_ASPECT_RATIO = 0.75
MAX_CROP_ASPECT_RATIO = 8.0
MIN_BLUR_VARIANCE = 20.0
MIN_BRIGHTNESS = 25.0
MIN_CONTRAST = 10.0

DIGIT_TO_LETTER: dict[str, str] = {
    "0": "D",
    "1": "T",
    "2": "Z",
    "3": "B",
    "4": "A",
    "5": "S",
    "6": "G",
    "7": "T",
    "8": "B",
    "9": "G",
}

LETTER_TO_DIGIT: dict[str, str] = {
    "A": "4",
    "B": "8",
    "C": "0",
    "D": "0",
    "E": "3",
    "G": "6",
    "I": "1",
    "L": "1",
    "O": "0",
    "Q": "0",
    "S": "5",
    "T": "7",
    "U": "0",
    "Z": "2",
}

KNOWN_TWO_LETTER_SERIES: frozenset[str] = frozenset(
    {"LD", "DA", "MK", "MD", "ME", "CD", "NG", "NN", "KT"}
)


def validate_image_input(
    image_bytes: bytes,
    *,
    content_type: str | None = None,
    max_bytes: int = DEFAULT_MAX_IMAGE_BYTES,
) -> None:
    """Validate image metadata and payload before invoking an inference model."""
    if content_type is not None and content_type not in SUPPORTED_IMAGE_CONTENT_TYPES:
        supported = ", ".join(sorted(SUPPORTED_IMAGE_CONTENT_TYPES))
        raise ALPRInvalidImageError(
            f"Unsupported image content type: {content_type}. Use {supported}."
        )
    if not isinstance(image_bytes, bytes) or not image_bytes:
        raise ALPRInvalidImageError("Image payload is empty.")
    if max_bytes <= 0:
        raise ValueError("max_bytes must be greater than zero")
    if len(image_bytes) > max_bytes:
        raise ALPRInvalidImageError(f"Image payload exceeds the {max_bytes}-byte limit.")


def decode_image(
    image_bytes: bytes,
    *,
    max_bytes: int = DEFAULT_MAX_IMAGE_BYTES,
) -> np.ndarray:
    """
    Giải mã mảng byte thô thành mảng numpy (numpy array) để OpenCV xử lý.
    Sử dụng cv2.imdecode.
    """
    validate_image_input(image_bytes, max_bytes=max_bytes)
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ALPRInvalidImageError("Image payload could not be decoded as JPEG or PNG.")
    return img


def crop_with_quality(
    image: np.ndarray,
    bbox: tuple[int, int, int, int],
    *,
    margin: float = DEFAULT_CROP_MARGIN,
) -> tuple[np.ndarray, tuple[int, int, int, int], list[str]]:
    """Expand, clamp and quality-check a detector crop before OCR."""
    if not 0 <= margin <= 1:
        raise ValueError("margin must be between 0 and 1")
    if image is None or getattr(image, "size", 0) == 0 or image.ndim < 2:
        return np.empty((0, 0), dtype=np.uint8), (0, 0, 0, 0), ["bbox_too_small"]

    height, width = image.shape[:2]
    x1, y1, x2, y2 = bbox
    raw_width = x2 - x1
    raw_height = y2 - y1
    margin_x = int(max(raw_width, 0) * margin)
    margin_y = int(max(raw_height, 0) * margin)
    expanded = (x1 - margin_x, y1 - margin_y, x2 + margin_x, y2 + margin_y)
    clamped = clamp_bbox(expanded, width, height)
    crop = crop_plate(image, clamped)
    flags: list[str] = []

    if x1 < 0 or y1 < 0 or x2 > width or y2 > height:
        flags.append("bbox_out_of_bounds")

    crop_height, crop_width = crop.shape[:2] if crop.ndim >= 2 else (0, 0)
    if crop_width < MIN_CROP_WIDTH or crop_height < MIN_CROP_HEIGHT:
        flags.append("bbox_too_small")
    if crop_width == 0 or crop_height == 0:
        return crop, clamped, flags

    aspect_ratio = crop_width / crop_height
    if not MIN_CROP_ASPECT_RATIO <= aspect_ratio <= MAX_CROP_ASPECT_RATIO:
        flags.append("crop_invalid_ratio")

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
    if float(cv2.Laplacian(gray, cv2.CV_64F).var()) < MIN_BLUR_VARIANCE:
        flags.append("crop_blurry")
    if float(gray.mean()) < MIN_BRIGHTNESS:
        flags.append("crop_dark")
    if float(gray.std()) < MIN_CONTRAST:
        flags.append("crop_low_contrast")
    return crop, clamped, flags


def correct_vietnamese_plate(cleaned_plate: str) -> str:
    """
    Áp dụng các quy tắc heuristics để sửa lỗi ký tự OCR thường gặp
    dựa trên cấu trúc chuẩn của biển số xe Việt Nam.

    Quy tắc:
    1. Biển hợp lệ thường có độ dài từ 7 đến 9 ký tự.
    2. Vị trí 0-1 (Mã tỉnh/thành): Bắt buộc là chữ số (ví dụ: B9 -> 89, O9 -> 09).
    3. Vị trí 2 (Ký hiệu series): Bắt buộc là chữ cái (ví dụ: 8 -> B, 0 -> D).
    4. Vị trí đuôi (Dãy số thứ tự): Bắt buộc là chữ số (ví dụ: D/O -> 0, B -> 8, S -> 5).
    """
    n = len(cleaned_plate)
    if n not in (7, 8, 9):
        return cleaned_plate

    chars = list(cleaned_plate)

    # 1. Hai ký tự đầu (Mã tỉnh): Phải là số
    for i in (0, 1):
        if not chars[i].isdigit() and chars[i] in LETTER_TO_DIGIT:
            chars[i] = LETTER_TO_DIGIT[chars[i]]

    # 2. Ký tự thứ 3 (Series): Phải là chữ cái
    if chars[2].isdigit() and chars[2] in DIGIT_TO_LETTER:
        chars[2] = DIGIT_TO_LETTER[chars[2]]

    # 3. Dãy số thứ tự ở cuối: Phải là số
    if n == 7:
        # Biển 4 số ô tô (29A-1234): chars[3:7] là số
        num_start = 3
    elif n == 8:
        series_two = f"{chars[2]}{chars[3]}"
        # Kiểm tra series 2 chữ cái (ô tô liên doanh/ngoại giao hoặc xe máy 50cc)
        if series_two in KNOWN_TWO_LETTER_SERIES or (
            chars[2].isalpha() and chars[3].isalpha() and not chars[3].isdigit()
        ):
            num_start = 4
        else:
            # Biển 5 số ô tô (29A-12345) hoặc 4 số xe máy (29P1-1234): chars[3:8] là số
            num_start = 3
    else:  # n == 9
        # Biển 5 số xe máy (29P1-12345) hoặc 5 số 2 chữ cái (29LD-12345)
        num_start = 4

    for i in range(num_start, n):
        if not chars[i].isdigit() and chars[i] in LETTER_TO_DIGIT:
            chars[i] = LETTER_TO_DIGIT[chars[i]]

    return "".join(chars)


def normalize_plate(plate: str, *, auto_correct: bool = True) -> str:
    """
    Chuẩn hóa chuỗi biển số xe: chuyển thành chữ in hoa,
    xóa bỏ các ký tự không phải là chữ cái hoặc số (khoảng trắng, dấu chấm, dấu gạch),
    và tự động sửa lỗi ký tự OCR theo quy luật biển số xe Việt Nam.
    """
    if not plate:
        return ""
    cleaned = re.sub(r"[^A-Z0-9]", "", plate.upper())
    if auto_correct:
        # ``0`` and ``1`` in the series position are highly ambiguous: either
        # can be a misread letter, or the OCR may have dropped the real series
        # character entirely (for example ``61-04392``).  Guessing here turns
        # uncertain OCR into a plausible but incorrect plate, so leave these
        # values untouched for the review/candidate-selection layer.
        if len(cleaned) >= 3 and cleaned[2] in {"0", "1"}:
            return cleaned
        return correct_vietnamese_plate(cleaned)
    return cleaned


def requires_confirmation(confidence: float, threshold: float) -> bool:
    """Return whether a result below the configured confidence needs review."""
    return confidence < threshold


def clamp_bbox(
    bbox: tuple[int, int, int, int], img_width: int, img_height: int
) -> tuple[int, int, int, int]:
    """
    Giới hạn tọa độ bounding box (kẹp giá trị) để đảm bảo không bị vượt ra khỏi kích thước ảnh.
    Định dạng bbox: (x1, y1, x2, y2)
    """
    if img_width <= 0 or img_height <= 0:
        return 0, 0, 0, 0

    raw_x1, raw_y1, raw_x2, raw_y2 = bbox
    x1, x2 = sorted((raw_x1, raw_x2))
    y1, y2 = sorted((raw_y1, raw_y2))
    x1 = max(0, min(x1, img_width - 1))
    y1 = max(0, min(y1, img_height - 1))
    x2 = max(0, min(x2, img_width))
    y2 = max(0, min(y2, img_height))
    if x2 < x1:
        x2 = x1
    if y2 < y1:
        y2 = y1
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
