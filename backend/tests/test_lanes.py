from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.lanes.models import Lane


@pytest.fixture
def admin_token(client: TestClient) -> str:
    """Login as admin and return token."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin-test-password"},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture
def operator_token(client: TestClient) -> str:
    """Login as operator and return token."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "operator", "password": "operator-test-password"},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


class TestCreateLane:
    """Test cases for POST /lanes/"""

    def test_create_lane_success(self, client: TestClient, admin_token: str):
        """Admin can create a new lane."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        payload = {
            "name": "LANE_TEST_01",
            "direction": "IN",
            "video_source": "rtsp://test/camera1",
            "is_active": True,
        }
        response = client.post("/api/v1/lanes/", json=payload, headers=headers)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["name"] == "LANE_TEST_01"
        assert data["direction"] == "IN"
        assert data["is_active"] is True
        assert data["allowed_vehicle_type"] == "ALL"
        assert data["camera_id"] is None
        assert data["barrier_id"] is None
        assert data["building_id"] is None
        assert isinstance(UUID(data["id"]), UUID)  # id là UUID

    def test_create_lane_with_extended_fields(self, client: TestClient, admin_token: str):
        """Admin can create a lane with allowed_vehicle_type, camera_id, barrier_id, building_id."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        payload = {
            "name": "LANE_CAR_ONLY",
            "direction": "IN",
            "video_source": "rtsp://test/cam_car",
            "allowed_vehicle_type": "CAR",
            "camera_id": "CAM_IN_01",
            "barrier_id": "BARRIER_IN_01",
            "building_id": "11111111-1111-1111-1111-111111111111",
        }
        response = client.post("/api/v1/lanes/", json=payload, headers=headers)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["name"] == "LANE_CAR_ONLY"
        assert data["allowed_vehicle_type"] == "CAR"
        assert data["camera_id"] == "CAM_IN_01"
        assert data["barrier_id"] == "BARRIER_IN_01"
        assert data["building_id"] == "11111111-1111-1111-1111-111111111111"

    def test_create_lane_unauthenticated(self, client: TestClient):
        """Non-authenticated user cannot create lane."""
        response = client.post(
            "/api/v1/lanes/",
            json={"name": "LANE_UNAUTH", "direction": "IN", "video_source": "rtsp://test"},
        )
        assert response.status_code == 401

    def test_create_lane_forbidden_operator(self, client: TestClient, operator_token: str):
        """Operator cannot create lane."""
        headers = {"Authorization": f"Bearer {operator_token}"}
        payload = {
            "name": "LANE_FORBIDDEN",
            "direction": "OUT",
            "video_source": "rtsp://test",
        }
        response = client.post("/api/v1/lanes/", json=payload, headers=headers)
        assert response.status_code == 403

    def test_create_lane_duplicate_name(self, client: TestClient, admin_token: str):
        """Cannot create lane with duplicate name."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        payload = {"name": "LANE_IN_01", "direction": "IN", "video_source": "rtsp://dup"}
        response = client.post("/api/v1/lanes/", json=payload, headers=headers)
        assert response.status_code == 409
        assert response.status_code == 409
        assert "tồn tại" in response.json()["message"].lower()


class TestListLanes:
    """Test cases for GET /lanes/ and GET /lanes/active"""

    def test_list_lanes_admin(self, client: TestClient, admin_token: str):
        """Admin can list all lanes."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.get("/api/v1/lanes/", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have at least 2 seeded lanes
        assert len(data) >= 2

    def test_list_lanes_unauthenticated(self, client: TestClient):
        """Non-authenticated user cannot list lanes."""
        response = client.get("/api/v1/lanes/")
        assert response.status_code == 401

    def test_list_active_lanes(self, client: TestClient, admin_token: str):
        """Can list active lanes."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.get("/api/v1/lanes/active", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # All returned lanes should be active
        for lane in data:
            assert lane["is_active"] is True


class TestGetLane:
    """Test cases for GET /lanes/{lane_id}"""

    def test_get_lane_by_id(self, client: TestClient, admin_token: str, db_session: Session):
        """Admin can get lane by ID."""
        # Get existing lane from DB
        lane = db_session.query(Lane).first()
        assert lane is not None

        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.get(f"/api/v1/lanes/{lane.id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(lane.id)
        assert data["name"] == lane.name

    def test_get_lane_not_found(self, client: TestClient, admin_token: str):
        """Returns 404 for non-existent lane."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/v1/lanes/{fake_uuid}", headers=headers)
        assert response.status_code == 404

    def test_get_lane_unauthenticated(self, client: TestClient):
        """Non-authenticated user cannot get lane."""
        response = client.get("/api/v1/lanes/some-uuid")
        assert response.status_code == 401


class TestUpdateLane:
    """Test cases for PATCH /lanes/{lane_id}"""

    def test_update_lane_name(self, client: TestClient, admin_token: str, db_session: Session):
        """Admin can update lane name."""
        lane = db_session.query(Lane).filter_by(name="LANE_IN_01").first()
        assert lane is not None

        headers = {"Authorization": f"Bearer {admin_token}"}
        payload = {"name": "LANE_IN_UPDATED"}
        response = client.patch(f"/api/v1/lanes/{lane.id}", json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "LANE_IN_UPDATED"

    def test_update_lane_inactive(self, client: TestClient, admin_token: str, db_session: Session):
        """Admin can update is_active status."""
        lane = db_session.query(Lane).filter_by(name="LANE_OUT_01").first()
        assert lane is not None

        headers = {"Authorization": f"Bearer {admin_token}"}
        payload = {"is_active": False}
        response = client.patch(f"/api/v1/lanes/{lane.id}", json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

    def test_update_lane_not_found(self, client: TestClient, admin_token: str):
        """Returns 404 for updating non-existent lane."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = client.patch(
            f"/api/v1/lanes/{fake_uuid}",
            json={"name": "FAKE"},
            headers=headers,
        )
        assert response.status_code == 404

    def test_update_lane_duplicate_name(
        self, client: TestClient, admin_token: str, db_session: Session
    ):
        """Cannot update to duplicate name."""
        lane1 = db_session.query(Lane).filter_by(name="LANE_IN_01").first()
        lane2 = db_session.query(Lane).filter_by(name="LANE_OUT_01").first()
        assert lane1 and lane2

        headers = {"Authorization": f"Bearer {admin_token}"}
        # Try to update LANE_OUT_01 to have same name as LANE_IN_01
        payload = {"name": "LANE_IN_01"}
        response = client.patch(f"/api/v1/lanes/{lane2.id}", json=payload, headers=headers)
        assert response.status_code == 409

    def test_update_lane_extended_fields(
        self, client: TestClient, admin_token: str, db_session: Session
    ):
        """Admin can update lane allowed_vehicle_type, camera_id, barrier_id, building_id."""
        lane = db_session.query(Lane).filter_by(name="LANE_IN_01").first()
        assert lane is not None

        headers = {"Authorization": f"Bearer {admin_token}"}
        payload = {
            "allowed_vehicle_type": "MOTORBIKE",
            "camera_id": "CAM_UPDATED",
            "barrier_id": "BARRIER_UPDATED",
            "building_id": "22222222-2222-2222-2222-222222222222",
        }
        response = client.patch(f"/api/v1/lanes/{lane.id}", json=payload, headers=headers)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["allowed_vehicle_type"] == "MOTORBIKE"
        assert data["camera_id"] == "CAM_UPDATED"
        assert data["barrier_id"] == "BARRIER_UPDATED"
        assert data["building_id"] == "22222222-2222-2222-2222-222222222222"


class TestDeactivateLane:
    """Test cases for POST /lanes/{lane_id}/deactivate"""

    def test_deactivate_lane(self, client: TestClient, admin_token: str, db_session: Session):
        """Admin can deactivate a lane."""
        lane = db_session.query(Lane).filter_by(name="LANE_IN_01").first()
        assert lane and lane.is_active
        db_session.commit()
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.post(f"/api/v1/lanes/{lane.id}/deactivate", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

    def test_deactivate_lane_not_found(self, client: TestClient, admin_token: str):
        """Returns 404 for deactivating non-existent lane."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = client.post(f"/api/v1/lanes/{fake_uuid}/deactivate", headers=headers)
        assert response.status_code == 404

    def test_deactivate_lane_unauthenticated(self, client: TestClient, db_session: Session):
        """Non-authenticated user cannot deactivate lane."""
        lane = db_session.query(Lane).first()
        assert lane is not None
        response = client.post(f"/api/v1/lanes/{lane.id}/deactivate")
        assert response.status_code == 401
