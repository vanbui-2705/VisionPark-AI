import pytest
import numpy as np
from app.alpr.utils import normalize_plate, clamp_bbox, crop_plate

def test_normalize_plate():
    assert normalize_plate(" 29A-123.45 ") == "29A12345"
    assert normalize_plate("29a12345") == "29A12345"
    assert normalize_plate("") == ""
    assert normalize_plate("O1I0") == "O1I0" # Đảm bảo chữ O, số 1, chữ I, số 0 không bị xóa

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

def test_crop_plate():
    # Tạo một bức ảnh giả 10x10
    image = np.arange(100).reshape((10, 10))
    
    # Crop vùng 2x2 từ góc trên trái
    bbox = (0, 0, 2, 2)
    cropped = crop_plate(image, bbox)
    
    assert cropped.shape == (2, 2)
    assert np.array_equal(cropped, np.array([[0, 1], [10, 11]]))
