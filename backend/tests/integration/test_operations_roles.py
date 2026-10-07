from uuid import uuid4

from sqlalchemy import select

from app.core.security import hash_password
from app.modules.lanes.models import Lane, LaneDirection
from app.modules.users.models import Role, User
from app.modules.users.schemas import RoleName
from tests.conftest import login


def role_headers(client, db_session, role_name: RoleName) -> dict[str, str]:
    role = db_session.scalar(select(Role).where(Role.name == role_name.value))
    username = role_name.value.lower()
    db_session.add(
        User(
            username=username,
            display_name=username,
            password_hash=hash_password("role-test-password"),
            role=role,
            is_active=True,
        )
    )
    db_session.commit()
    token = login(client, username, "role-test-password")["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_accountant_can_read_parking_and_audit_but_cannot_operate(
    client, db_session, operator_headers
):
    lane = db_session.scalar(select(Lane).where(Lane.direction == LaneDirection.IN))
    created = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(lane.id), "license_plate": "29A12345"},
        headers={**operator_headers, "Idempotency-Key": "accountant-read-seed"},
    )
    assert created.status_code == 201, created.text
    transaction_id = created.json()["transaction"]["id"]
    headers = role_headers(client, db_session, RoleName.ACCOUNTANT)

    history = client.get("/api/v1/parking/transactions?paginated=true", headers=headers)
    assert history.status_code == 200
    assert history.json()["total"] == 1
    detail = client.get(f"/api/v1/parking/transactions/{transaction_id}", headers=headers)
    assert detail.status_code == 200
    summary = client.get("/api/v1/parking/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json() == {"total": 1, "parked": 1, "manual": 1}
    assert client.get("/api/v1/audit-logs/?paginated=true", headers=headers).status_code == 200

    forbidden_checkin = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(lane.id), "license_plate": "30A12345"},
        headers=headers,
    )
    assert forbidden_checkin.status_code == 403
    assert forbidden_checkin.json()["code"] == "FORBIDDEN"
    assert client.get("/api/v1/alpr/detections", headers=headers).status_code == 403
    assert client.get("/api/v1/users", headers=headers).status_code == 403
    assert client.get("/api/v1/parking/summary").status_code == 401


def test_technician_can_use_station_but_cannot_read_parking_or_audit(client, db_session):
    lane = db_session.scalar(select(Lane).where(Lane.direction == LaneDirection.IN))
    headers = role_headers(client, db_session, RoleName.TECHNICIAN)

    assert client.get("/api/v1/lanes/active", headers=headers).status_code == 200
    assert client.get("/api/v1/alpr/detections?paginated=true", headers=headers).status_code == 200
    missing_id = uuid4()
    assert client.get(f"/api/v1/alpr/detections/{missing_id}", headers=headers).status_code == 404
    assert (
        client.post(
            f"/api/v1/alpr/detections/{missing_id}/confirm",
            json={"confirmed_plate": "29A12345"},
            headers=headers,
        ).status_code
        == 404
    )
    invalid_image = client.post(
        "/api/v1/alpr/detections",
        data={"lane_id": str(lane.id)},
        files={"image": ("invalid.png", b"not-an-image", "image/png")},
        headers=headers,
    )
    assert invalid_image.status_code == 422

    checkin = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(lane.id), "license_plate": "30A12345"},
        headers={**headers, "Idempotency-Key": "technician-checkin"},
    )
    assert checkin.status_code == 201, checkin.text
    for path in ("/api/v1/parking/transactions", "/api/v1/parking/summary", "/api/v1/audit-logs/"):
        response = client.get(path, headers=headers)
        assert response.status_code == 403, path
        assert response.json()["code"] == "FORBIDDEN"
    assert client.get("/api/v1/users", headers=headers).status_code == 403
