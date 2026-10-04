<<<<<<< HEAD
import numpy as np

from app.alpr.utils import clamp_bbox, crop_plate, normalize_plate, requires_confirmation
=======
import cv2
import numpy as np
import pytest

from app.alpr.errors import ALPRInvalidImageError
from app.alpr.utils import (
    clamp_bbox,
    crop_plate,
    crop_with_quality,
    decode_image,
    normalize_plate,
    requires_confirmation,
    validate_image_input,
)


def encoded_image(extension: str) -> bytes:
    image = np.full((8, 12, 3), 220, dtype=np.uint8)
    ok, encoded = cv2.imencode(extension, image)
    assert ok
    return encoded.tobytes()


def test_validate_and_decode_jpeg_and_png():
    for content_type, extension in (("image/jpeg", ".jpg"), ("image/png", ".png")):
        image_bytes = encoded_image(extension)

        validate_image_input(image_bytes, content_type=content_type)
        decoded = decode_image(image_bytes)

        assert decoded.shape == (8, 12, 3)


def test_invalid_image_payloads_raise_typed_error():
    with pytest.raises(ALPRInvalidImageError, match="empty"):
        validate_image_input(b"")

    with pytest.raises(ALPRInvalidImageError, match="could not be decoded"):
        decode_image(b"not-an-image")

    with pytest.raises(ALPRInvalidImageError, match="exceeds"):
        validate_image_input(b"12345", max_bytes=4)


def test_validate_image_content_type():
    with pytest.raises(ALPRInvalidImageError, match="Unsupported image content type"):
        validate_image_input(encoded_image(".jpg"), content_type="text/plain")


def test_crop_with_quality_expands_and_clamps_bbox():
    image = np.zeros((100, 200, 3), dtype=np.uint8)
    image[20:60, 40:160] = 255

    crop, bbox, flags = crop_with_quality(image, (40, 20, 160, 60), margin=0.1)

    assert bbox == (28, 16, 172, 64)
    assert crop.shape == (48, 144, 3)
    assert "bbox_out_of_bounds" not in flags


def test_crop_with_quality_reports_small_dark_blurry_crop():
    image = np.zeros((20, 20, 3), dtype=np.uint8)

    crop, bbox, flags = crop_with_quality(image, (2, 2, 10, 8))

    assert crop.shape == (6, 8, 3)
    assert bbox[0] >= 0
    assert {"bbox_too_small", "crop_blurry"}.issubset(flags)
    assert "crop_dark" in flags


def test_crop_with_quality_reports_out_of_bounds_and_invalid_margin():
    image = np.full((80, 160, 3), 128, dtype=np.uint8)

    _, _, flags = crop_with_quality(image, (-10, 10, 190, 30))

    assert "bbox_out_of_bounds" in flags
    with pytest.raises(ValueError, match="margin"):
        crop_with_quality(image, (1, 1, 30, 15), margin=1.5)

>>>>>>> main


def test_normalize_plate():
    assert normalize_plate(" 29A-123.45 ") == "29A12345"
    assert normalize_plate("29a12345") == "29A12345"
    assert normalize_plate("") == ""
    assert normalize_plate("O1I0") == "O1I0"  # Đảm bảo chữ O, số 1, chữ I, số 0 không bị xóa


def test_confidence_policy():
    assert requires_confirmation(0.84, 0.85) is True
    assert requires_confirmation(0.85, 0.85) is False
    assert requires_confirmation(0.86, 0.85) is False


def test_clamp_bbox():
    img_width, img_height = 800, 600

    # Bbox hợp lệ nằm hoàn toàn trong ảnh
    assert clamp_bbox((100, 100, 200, 200), img_width, img_height) == (100, 100, 200, 200)

    # Bbox vượt ra ngoài viền trái/trên (âm)
    assert clamp_bbox((-50, -10, 200, 200), img_width, img_height) == (0, 0, 200, 200)

    # Bbox vượt ra ngoài viền phải/dưới
    assert clamp_bbox((700, 500, 900, 800), img_width, img_height) == (700, 500, 800, 600)

    # Bbox nằm hoàn toàn bên ngoài ảnh
    assert clamp_bbox((-200, -200, -100, -100), img_width, img_height) == (0, 0, 0, 0)
    assert clamp_bbox((900, 700, 1000, 800), img_width, img_height) == (799, 599, 800, 600)
    assert clamp_bbox((200, 180, 100, 80), img_width, img_height) == (100, 80, 200, 180)
    assert clamp_bbox((10, 10, 10, 50), img_width, img_height) == (10, 10, 10, 50)


def test_crop_plate():
    # Tạo một bức ảnh giả 10x10
    image = np.arange(100).reshape((10, 10))

    # Crop vùng 2x2 từ góc trên trái
    bbox = (0, 0, 2, 2)
    cropped = crop_plate(image, bbox)

    assert cropped.shape == (2, 2)
    assert np.array_equal(cropped, np.array([[0, 1], [10, 11]]))
