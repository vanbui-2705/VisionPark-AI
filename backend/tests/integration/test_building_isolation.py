from uuid import uuid4

import jwt
import pytest
from sqlalchemy import func, select, text

from app.core.errors import AppError
from app.core.security import create_access_token, hash_password
from app.database.session import database
from app.modules.alpr.models import Detection
from app.modules.audit_logs.models import AuditLog
from app.modules.buildings.models import Building, ParkingLot, UserBuilding
from app.modules.checkin.models import ParkingTransaction
from app.modules.lanes.models import Lane
from app.modules.users.models import Role, User
from tests.conftest import login


@pytest.fixture
def second_building(client, db_session):
    building = Building(code="SECOND", name="Second building")
    db_session.add(building)
    db_session.flush()
    db_session.add(ParkingLot(building_id=building.id))
    role = db_session.scalar(select(Role).where(Role.name == "OPERATOR"))
    user = User(
        username="operator-b",
        display_name="Operator B",
        role=role,
        password_hash=hash_password("operator-b-password"),
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    db_session.add(UserBuilding(user_id=user.id, building_id=building.id))
    lane = Lane(name="B-IN", direction="IN", video_source="test", building_id=building.id)
    db_session.add(lane)
    db_session.flush()
    detection = Detection(lane_id=lane.id, building_id=building.id, image_key="private-b.jpg")
    db_session.add(detection)
    db_session.flush()
    transaction = ParkingTransaction(
        building_id=building.id,
        lane_id=lane.id,
        detection_id=detection.id,
        license_plate="B12345",
        normalized_plate="B12345",
        source="MANUAL_ENTRY",
        idempotency_key="b-key",
        request_fingerprint="b" * 64,
    )
    audit = AuditLog(
        building_id=building.id,
        user_id=user.id,
        action="CREATE_CHECKIN",
        entity_type="ParkingTransaction",
        entity_id=str(uuid4()),
    )
    db_session.add_all([transaction, audit])
    db_session.commit()
    return building, user, lane, detection, transaction, audit


def headers_b(client):
    token = login(client, "operator-b", "operator-b-password")["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_token_and_lane_queries_are_bound_to_server_membership(
    client,
    second_building,
    operator_headers,
    settings,
):
    building, _user, lane, *_ = second_building
    token = login(client, "operator-b", "operator-b-password")["access_token"]
    claims = jwt.decode(token, settings.jwt_secret_key.get_secret_value(), algorithms=["HS256"])
    assert claims["building_id"] == str(building.id)
    for endpoint in ("/api/v1/lanes/", "/api/v1/lanes/active"):
        a = client.get(endpoint + f"?building_id={building.id}", headers=operator_headers)
        b = client.get(endpoint, headers={"Authorization": f"Bearer {token}"})
        assert a.status_code == b.status_code == 200
        assert str(lane.id) not in {row["id"] for row in a.json()}
        assert {row["id"] for row in b.json()} == {str(lane.id)}
    assert client.get(f"/api/v1/lanes/{lane.id}", headers=operator_headers).status_code == 404


def test_cross_building_detail_checkin_and_history_are_rejected(
    client,
    second_building,
    operator_headers,
):
    _building, _user, lane, detection, transaction, audit = second_building
    for endpoint in (
        f"/api/v1/parking/transactions/{transaction.id}",
        f"/api/v1/alpr/detections/{detection.id}",
    ):
        assert client.get(endpoint, headers=operator_headers).status_code == 404
        assert client.get(endpoint, headers=headers_b(client)).status_code == 200
    result = client.post(
        "/api/v1/parking/check-in",
        headers=operator_headers,
        json={
            "lane_id": str(lane.id),
            "license_plate": "A99999",
            "idempotency_key": "cross-building",
        },
    )
    assert result.status_code == 404
    summary = client.get("/api/v1/parking/summary", headers=operator_headers)
    assert summary.json()["total"] == 0
    history = client.get("/api/v1/parking/transactions?paginated=true", headers=operator_headers)
    assert history.json()["total"] == 0
    audits = client.get(
        f"/api/v1/audit-logs/?resource_id={audit.entity_id}&paginated=true",
        headers=operator_headers,
    )
    assert audits.status_code == 200
    assert audits.json()["total"] == 0
    own_audits = client.get(
        f"/api/v1/audit-logs/?resource_id={audit.entity_id}&paginated=true",
        headers=headers_b(client),
    )
    assert own_audits.status_code == 200
    assert own_audits.json()["total"] == 1


def test_building_b_write_and_audit_use_the_same_building(client, second_building, db_session):
    building, _user, lane, *_ = second_building
    result = client.post(
        "/api/v1/parking/check-in",
        headers=headers_b(client),
        json={
            "lane_id": str(lane.id),
            "license_plate": "B99999",
            "idempotency_key": "new-b-checkin",
        },
    )
    assert result.status_code == 201, result.text
    transaction = db_session.scalar(
        select(ParkingTransaction).where(ParkingTransaction.idempotency_key == "new-b-checkin")
    )
    assert transaction.building_id == building.id
    audit = db_session.scalar(select(AuditLog).where(AuditLog.entity_id == str(transaction.id)))
    assert audit.building_id == building.id


def test_membership_revocation_and_inactive_building_invalidate_existing_token(
    client,
    second_building,
    db_session,
):
    building, user, *_ = second_building
    headers = headers_b(client)
    building.is_active = False
    db_session.commit()
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 403
    building.is_active = True
    membership = db_session.scalar(select(UserBuilding).where(UserBuilding.user_id == user.id))
    db_session.delete(membership)
    db_session.commit()
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 403


def test_signed_claim_cannot_grant_unassigned_building(
    client, second_building, db_session, settings
):
    building, *_ = second_building
    user = db_session.scalar(select(User).where(User.username == "operator"))
    token = create_access_token(
        user.id, settings, token_version=user.token_version, building_id=building.id
    )
    result = client.get("/api/v1/lanes/", headers={"Authorization": f"Bearer {token}"})
    assert result.status_code == 403
    assert result.json()["code"] == "BUILDING_ACCESS_DENIED"


def test_shared_session_covers_counts_aliases_identity_cache_and_write_guards(second_building):
    from sqlalchemy.orm import aliased

    building, _user, lane, *_ = second_building
    with database.create_session() as session:
        cached = session.get(Lane, lane.id)
        other = session.scalar(select(Lane).where(Lane.id != lane.id))
        session.info["building_id"] = building.id
        assert session.get(Lane, other.id) is None
        assert session.get(Lane, cached.id) is cached
        lane_alias = aliased(Lane)
        assert session.scalar(select(func.count()).select_from(lane_alias)) == 1
        with pytest.raises(AppError, match="shared ORM"):
            session.execute(text("SELECT * FROM lanes"))
        session.add(
            Lane(
                name="forbidden", direction="IN", video_source="test", building_id=other.building_id
            )
        )
        with pytest.raises(AppError):
            session.flush()
        session.rollback()


def test_legacy_system_administrator_can_see_both_buildings(client, second_building, admin_token):
    _building, _user, lane, *_ = second_building
    result = client.get("/api/v1/lanes/", headers={"Authorization": f"Bearer {admin_token}"})
    assert result.status_code == 200
    assert str(lane.id) in {row["id"] for row in result.json()}


def test_each_building_can_use_the_same_plate_and_key(
    client, second_building, operator_headers, db_session
):
    building, _user, lane_b, *_ = second_building
    lane_a = db_session.scalar(
        select(Lane).where(Lane.building_id != building.id, Lane.direction == "IN")
    )
    for lane, headers in ((lane_a, operator_headers), (lane_b, headers_b(client))):
        response = client.post(
            "/api/v1/parking/check-in",
            headers=headers,
            json={
                "lane_id": str(lane.id),
                "license_plate": "SHARED123",
                "idempotency_key": "shared-key",
            },
        )
        assert response.status_code == 201, response.text
        retry = client.post(
            "/api/v1/parking/check-in",
            headers=headers,
            json={
                "lane_id": str(lane.id),
                "license_plate": "SHARED123",
                "idempotency_key": "shared-key",
            },
        )
        assert retry.status_code == 201
        assert retry.json()["transaction"]["id"] == response.json()["transaction"]["id"]
    rows = list(
        db_session.scalars(
            select(ParkingTransaction).where(ParkingTransaction.idempotency_key == "shared-key")
        )
    )
    assert len(rows) == 2
    assert len({row.building_id for row in rows}) == 2


def test_system_admin_writes_use_the_selected_lanes_building(
    client, second_building, admin_token, db_session
):
    building, _user, lane, *_ = second_building
    response = client.post(
        "/api/v1/parking/check-in",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"lane_id": str(lane.id), "license_plate": "ADMINB123", "idempotency_key": "admin-b"},
    )
    assert response.status_code == 201, response.text
    transaction = db_session.scalar(
        select(ParkingTransaction).where(ParkingTransaction.idempotency_key == "admin-b")
    )
    assert transaction.building_id == building.id
    audit = db_session.scalar(select(AuditLog).where(AuditLog.entity_id == str(transaction.id)))
    assert audit.building_id == building.id


def test_cached_row_cannot_be_moved_between_buildings_or_modified_in_bulk(second_building):
    from sqlalchemy import update

    building, _user, _lane, *_ = second_building
    with database.create_session() as session:
        other = session.scalar(select(Lane).where(Lane.building_id != building.id))
        session.info["building_id"] = building.id
        with pytest.raises(AppError, match="shared ORM"):
            session.execute(select(Lane.__table__))
        with pytest.raises(AppError, match="unit of work"):
            session.execute(update(Lane).values(building_id=other.building_id))
        other.building_id = building.id
        with pytest.raises(AppError):
            session.flush()
        session.rollback()


def test_media_requires_authentication_and_building_ownership(
    client, second_building, operator_headers, settings
):
    from pathlib import Path

    _building, _user, lane, detection, *_ = second_building
    directory = Path(settings.local_storage_path) / str(lane.id)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / detection.image_key).write_bytes(b"private-image-fixture")
    url = f"/api/v1/alpr/media/{detection.image_key}"
    assert client.get(url).status_code == 401
    assert client.get(url, headers=operator_headers).status_code == 404
    response = client.get(url, headers=headers_b(client))
    assert response.status_code == 200
    assert response.content == b"private-image-fixture"
    assert response.headers["Cache-Control"] == "private, no-store"
