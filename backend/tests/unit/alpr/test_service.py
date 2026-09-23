import pytest
from app.alpr.schema import ALPRResult, BoundingBox
from app.alpr.errors import ALPRNotReadyError
from app.alpr.service import ALPRApplicationService

# --- Mock classes ---

class MockLaneChecker:
    def check_active_lane(self, lane_id: str) -> bool:
        return lane_id == "lane_1"

class MockImageStorage:
    def save_image(self, image_bytes: bytes, lane_id: str) -> str:
        return f"s3://bucket/{lane_id}/image.jpg"

class MockDetectionRecorder:
    def __init__(self):
        self.recorded = []
        
    def record_detection(self, lane_id: str, image_key: str, result: ALPRResult) -> str:
        self.recorded.append((lane_id, image_key, result))
        return "det_123"

class MockALPRRuntime:
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        
    def is_ready(self):
        return (not self.should_fail, "Ok" if not self.should_fail else "Fail")
        
    def detect_and_read(self, image_bytes: bytes) -> ALPRResult:
        if self.should_fail:
            raise ALPRNotReadyError("Model not loaded")
        return ALPRResult(
            plate_number="30A12345",
            bbox=BoundingBox(x1=0, y1=0, x2=10, y2=10),
            confidence=0.9,
            processing_time_ms=100,
            requires_confirmation=False
        )

# --- Tests ---

def test_process_detection_success():
    runtime = MockALPRRuntime()
    lane_checker = MockLaneChecker()
    storage = MockImageStorage()
    recorder = MockDetectionRecorder()
    
    service = ALPRApplicationService(runtime, lane_checker, storage, recorder)
    
    # Run
    result = service.process_detection(b"fake_image_bytes", "lane_1")
    
    # Assert
    assert result.plate_number == "30A12345"
    assert len(recorder.recorded) == 1
    
    recorded_lane, recorded_key, recorded_result = recorder.recorded[0]
    assert recorded_lane == "lane_1"
    assert recorded_key == "s3://bucket/lane_1/image.jpg"
    assert recorded_result.plate_number == "30A12345"

def test_process_detection_invalid_lane():
    runtime = MockALPRRuntime()
    lane_checker = MockLaneChecker()
    storage = MockImageStorage()
    recorder = MockDetectionRecorder()
    
    service = ALPRApplicationService(runtime, lane_checker, storage, recorder)
    
    with pytest.raises(ValueError, match="không tồn tại hoặc đang không hoạt động"):
        service.process_detection(b"fake_image_bytes", "lane_99")

def test_process_detection_runtime_error():
    runtime = MockALPRRuntime(should_fail=True)
    lane_checker = MockLaneChecker()
    storage = MockImageStorage()
    recorder = MockDetectionRecorder()
    
    service = ALPRApplicationService(runtime, lane_checker, storage, recorder)
    
    with pytest.raises(ALPRNotReadyError):
        service.process_detection(b"fake_image_bytes", "lane_1")
