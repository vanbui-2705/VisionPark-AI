import pytest
from pydantic import ValidationError
from app.alpr.schema import BoundingBox, ALPRResult

def test_bounding_box_creation():
    bbox = BoundingBox(x1=10, y1=20, x2=100, y2=200)
    assert bbox.x1 == 10
    assert bbox.y1 == 20
    assert bbox.x2 == 100
    assert bbox.y2 == 200
    assert bbox.as_tuple == (10, 20, 100, 200)

def test_bounding_box_validation():
    # Thiếu trường bắt buộc
    with pytest.raises(ValidationError):
        BoundingBox(x1=10, y1=20, x2=100)
        
    # Sai kiểu dữ liệu
    with pytest.raises(ValidationError):
        BoundingBox(x1="muoi", y1=20, x2=100, y2=200)

def test_alpr_result_creation():
    bbox = BoundingBox(x1=10, y1=20, x2=100, y2=200)
    
    # Kết quả chuẩn
    res1 = ALPRResult(
        plate_number="29A12345",
        bbox=bbox,
        confidence=0.95,
        processing_time_ms=120,
        requires_confirmation=False
    )
    assert res1.plate_number == "29A12345"
    assert res1.requires_confirmation is False
    
    # Kết quả khi không thấy biển số
    res2 = ALPRResult(
        plate_number=None,
        bbox=None,
        confidence=0.0,
        processing_time_ms=50,
        requires_confirmation=True
    )
    assert res2.plate_number is None
    assert res2.requires_confirmation is True
