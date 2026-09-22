from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.alpr.errors import ALPRNotReadyError
from app.alpr.schema import ALPRResult, BoundingBox
from app.api.endpoints.alpr import get_alpr_service, router

# Tạo app FastAPI ảo để test router
app = FastAPI()
app.include_router(router, prefix="/api/v1/alpr")


# --- Mocks ---
class MockSuccessService:
    def process_detection(self, image_bytes: bytes, lane_id: str) -> ALPRResult:
        if lane_id == "invalid_lane":
            raise ValueError("Lane inactive")
        return ALPRResult(
            plate_number="29A12345",
            bbox=BoundingBox(x1=0, y1=0, x2=10, y2=10),
            confidence=0.9,
            processing_time_ms=100,
            requires_confirmation=False,
        )


class MockNotReadyService:
    def process_detection(self, image_bytes: bytes, lane_id: str) -> ALPRResult:
        raise ALPRNotReadyError("Mock Not Ready")


# --- Tests ---


def test_create_detection_success():
    # Ghi đè dependency
    app.dependency_overrides[get_alpr_service] = MockSuccessService
    client = TestClient(app)

    # Fake file ảnh
    file_data = {"image": ("test.jpg", b"fakebytes", "image/jpeg")}
    data = {"lane_id": "lane_1"}

    response = client.post("/api/v1/alpr/detections", data=data, files=file_data)

    assert response.status_code == 200
    res_json = response.json()
    assert res_json["plate_number"] == "29A12345"
    assert res_json["confidence"] == 0.9


def test_create_detection_invalid_image_type():
    app.dependency_overrides[get_alpr_service] = MockSuccessService
    client = TestClient(app)

    # Fake file txt thay vì ảnh
    file_data = {"image": ("test.txt", b"fakebytes", "text/plain")}
    data = {"lane_id": "lane_1"}

    response = client.post("/api/v1/alpr/detections", data=data, files=file_data)

    assert response.status_code == 422
    assert "chỉ hỗ trợ JPEG và PNG" in response.json()["detail"]


def test_create_detection_invalid_lane():
    app.dependency_overrides[get_alpr_service] = MockSuccessService
    client = TestClient(app)

    file_data = {"image": ("test.jpg", b"fakebytes", "image/jpeg")}
    data = {"lane_id": "invalid_lane"}  # Gây ra ValueError

    response = client.post("/api/v1/alpr/detections", data=data, files=file_data)

    assert response.status_code == 404
    assert "Lane inactive" in response.json()["detail"]


def test_create_detection_not_ready():
    app.dependency_overrides[get_alpr_service] = MockNotReadyService
    client = TestClient(app)

    file_data = {"image": ("test.jpg", b"fakebytes", "image/jpeg")}
    data = {"lane_id": "lane_1"}

    response = client.post("/api/v1/alpr/detections", data=data, files=file_data)

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "ALPR_NOT_READY"
