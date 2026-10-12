from uuid import UUID

import pytest
from sqlalchemy import select

from app.modules.audit_logs.models import AuditLog
from app.modules.buildings.models import ParkingLot
from app.modules.lanes.models import Lane
from tests.conftest import login


def auth(client, username, password):
    return {"Authorization": f"Bearer {login(client, username, password)['access_token']}"}


def provision(client, system, code="P3"):
    building = client.post(
        "/api/v1/buildings", json={"code": code, "name": code, "address": "Test"}, headers=system
    )
    assert building.status_code == 201, building.text
    building_id = building.json()["id"]
    response = client.post(
        f"/api/v1/buildings/{building_id}/admins",
        json={"username": f"admin-{code.lower()}", "display_name": "Building admin"},
        headers=system,
    )
    assert response.status_code == 201, response.text
    temporary = response.json()["temporary_password"]
    headers = auth(client, f"admin-{code.lower()}", temporary)
    return building_id, temporary, headers


@pytest.fixture
def building_admin(client, admin_token):
    system = {"Authorization": f"Bearer {admin_token}"}
    building_id, temporary, headers = provision(client, system)
    result = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": temporary, "new_password": "new-private-password"},
        headers=headers,
    )
    assert result.status_code == 200, result.text
    return building_id, auth(client, "admin-p3", "new-private-password"), system


def settings(client, headers, building_id=None):
    result = client.get(
        "/api/v1/settings/lot",
        params={"building_id": building_id} if building_id else None,
        headers=headers,
    )
    assert result.status_code == 200, result.text
    return result.json()


def save(client, headers, config):
    return client.put(
        "/api/v1/settings/lot",
        json={"revision": config["revision"], "settings": config["settings"]},
        headers=headers,
    )


def test_provisioning_requires_password_change_and_lock_revokes_access(
    client, admin_token, db_session
):
    system = {"Authorization": f"Bearer {admin_token}"}
    building_id, temporary, headers = provision(client, system)
    assert client.get("/api/v1/auth/me", headers=headers).json()["must_change_password"] is True
    blocked = client.get("/api/v1/settings/lot", headers=headers)
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "PASSWORD_CHANGE_REQUIRED"
    unchanged = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": temporary, "new_password": temporary},
        headers=headers,
    )
    assert unchanged.status_code == 422
    changed = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": temporary, "new_password": "new-private-password"},
        headers=headers,
    )
    assert changed.status_code == 200
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    headers = auth(client, "admin-p3", "new-private-password")
    assert client.get("/api/v1/auth/me", headers=headers).json()["must_change_password"] is False
    assert (
        client.patch(
            f"/api/v1/buildings/{building_id}", json={"is_active": False}, headers=system
        ).status_code
        == 200
    )
    assert client.get("/api/v1/settings/lot", headers=headers).status_code == 403
    audits = db_session.scalars(
        select(AuditLog).where(AuditLog.building_id == UUID(building_id))
    ).all()
    assert {"CREATE_BUILDING", "CREATE_USER", "UPDATE_BUILDING"} <= {a.action for a in audits}
    assert temporary not in str([(a.old_value, a.new_value) for a in audits])
    assert all(a.user_id is not None for a in audits)


def test_building_admin_manages_staff_but_cannot_escalate_or_cross_building(
    client, building_admin, db_session
):
    building_id, headers, system = building_admin
    payload = {
        "username": "p3-staff",
        "display_name": "Staff",
        "password": "staff-test-password",
        "role": "OPERATOR",
    }
    created = client.post("/api/v1/users", json=payload, headers=headers)
    assert created.status_code == 201, created.text
    user_id = created.json()["id"]
    for role in ("SYSTEM_ADMIN", "BUILDING_ADMIN"):
        assert (
            client.post(
                "/api/v1/users",
                json={**payload, "username": "elevated", "role": role},
                headers=headers,
            ).status_code
            == 403
        )
        assert (
            client.patch(
                f"/api/v1/users/{user_id}", json={"role": role}, headers=headers
            ).status_code
            == 403
        )
    assert (
        client.post(
            "/api/v1/users", json={**payload, "building_id": building_id}, headers=headers
        ).status_code
        == 403
    )
    other_id, _, _ = provision(client, system, "OTHER")
    assert (
        client.get(
            "/api/v1/settings/lot", params={"building_id": other_id}, headers=headers
        ).status_code
        == 403
    )
    other_user = next(
        u
        for u in client.get("/api/v1/users", headers=system).json()
        if u["username"] == "admin-other"
    )
    assert (
        client.patch(
            f"/api/v1/users/{other_user['id']}", json={"active": False}, headers=headers
        ).status_code
        == 404
    )
    staff_headers = auth(client, payload["username"], payload["password"])
    assert (
        client.patch(
            f"/api/v1/users/{user_id}",
            json={"role": "ACCOUNTANT", "active": False},
            headers=headers,
        ).status_code
        == 200
    )
    assert client.get("/api/v1/auth/me", headers=staff_headers).status_code == 401
    audit = db_session.scalar(
        select(AuditLog).where(AuditLog.action == "UPDATE_USER", AuditLog.entity_id == user_id)
    )
    assert audit.building_id == UUID(building_id)
    assert audit.old_value["role"] == "OPERATOR" and audit.new_value["role"] == "ACCOUNTANT"


def test_setting_validates_capacity_quota_and_records_complete_audit(
    client, building_admin, db_session
):
    building_id, headers, _ = building_admin
    config = settings(client, headers)
    config["settings"]["capacities"]["CAR"].update(physical_capacity=10, safe_capacity=11)
    assert save(client, headers, config).status_code == 422
    config["settings"]["capacities"]["CAR"]["safe_capacity"] = 10
    config["settings"]["quotas"]["CAR"].update(residents=5, employees=6)
    assert save(client, headers, config).status_code == 422
    config["settings"]["quotas"]["CAR"]["employees"] = 3
    config["settings"]["ai"]["plate_confidence"] = 0.9
    result = save(client, headers, config)
    assert result.status_code == 200, result.text
    assert result.json()["revision"] == config["revision"] + 1
    assert save(client, headers, config).json()["code"] == "SETTINGS_CONFLICT"
    audit = db_session.scalar(select(AuditLog).where(AuditLog.action == "UPDATE_LOT_SETTINGS"))
    assert audit.building_id == UUID(building_id)
    assert audit.old_value["settings"]["ai"]["plate_confidence"] is None
    assert audit.new_value["settings"]["ai"]["plate_confidence"] == 0.9
    assert audit.created_at and audit.user_id


def make_ready(client, headers):
    config = settings(client, headers)
    config["settings"]["capacities"]["CAR"].update(physical_capacity=10, safe_capacity=10)
    assert save(client, headers, config).status_code == 200
    lanes = []
    for direction in ("IN", "OUT"):
        response = client.post(
            "/api/v1/lanes/",
            json={
                "name": f"P3-{direction}",
                "direction": direction,
                "video_source": "test",
                "allowed_vehicle_types": ["CAR"],
                "camera": f"camera-{direction}",
                "barrier": f"barrier-{direction}",
            },
            headers=headers,
        )
        assert response.status_code == 200, response.text
        lanes.append(response.json()["id"])
    return lanes


def test_entry_blocked_until_ready_closed_and_capacity_cannot_shrink_below_occupancy(
    client, building_admin, db_session
):
    building_id, headers, _ = building_admin
    initial = settings(client, headers)
    assert initial["readiness"]["ready"] is False
    assert "CAPACITY_REQUIRED" in initial["readiness"]["missing"]
    lane_id, _ = make_ready(client, headers)
    del client.app.state.effective_pricing
    request = {"lane_id": lane_id, "license_plate": "P3CAR123"}
    blocked = client.post(
        "/api/v1/parking/check-in", json=request, headers={**headers, "Idempotency-Key": "p3-entry"}
    )
    assert blocked.status_code == 409
    assert blocked.json()["details"]["missing"] == ["EFFECTIVE_PRICING_REQUIRED"]
    client.app.state.effective_pricing = lambda db, building_id, at: True
    assert settings(client, headers)["readiness"]["ready"] is True
    created = client.post(
        "/api/v1/parking/check-in", json=request, headers={**headers, "Idempotency-Key": "p3-entry"}
    )
    assert created.status_code == 201, created.text
    config = settings(client, headers)
    config["settings"]["capacities"]["CAR"]["safe_capacity"] = 0
    assert save(client, headers, config).json()["code"] == "CAPACITY_BELOW_OCCUPANCY"
    config["settings"]["capacities"]["CAR"]["safe_capacity"] = 10
    config["settings"]["information"]["status"] = "CLOSED"
    assert save(client, headers, config).status_code == 200
    replay = client.post(
        "/api/v1/parking/check-in", json=request, headers={**headers, "Idempotency-Key": "p3-entry"}
    )
    assert (
        replay.status_code == 201
        and replay.json()["transaction"]["id"] == created.json()["transaction"]["id"]
    )
    new = client.post(
        "/api/v1/parking/check-in",
        json={**request, "license_plate": "P3NEW123"},
        headers={**headers, "Idempotency-Key": "p3-new"},
    )
    assert new.json()["details"]["missing"] == ["LOT_CLOSED"]
    audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "CREATE_LANE", AuditLog.building_id == UUID(building_id)
        )
    )
    assert audit.new_value["camera"] and audit.new_value["allowed_vehicle_types"] == ["CAR"]


def test_copy_is_system_only_versioned_audited_and_preserves_target_identity(
    client, building_admin, db_session
):
    source_id, headers, system = building_admin
    target_id, _, _ = provision(client, system, "TARGET")
    config = settings(client, headers)
    config["settings"]["capacities"]["CAR"].update(physical_capacity=20, safe_capacity=12)
    config["settings"]["ai"]["vehicle_confidence"] = 0.91
    assert save(client, headers, config).status_code == 200
    source = settings(client, system, source_id)
    target = settings(client, system, target_id)
    payload = {
        "target_building_id": target_id,
        "source_revision": source["revision"],
        "target_revision": target["revision"],
    }
    path = f"/api/v1/buildings/{source_id}/copy-settings"
    assert client.post(path, json=payload, headers=headers).status_code == 403
    assert save(client, system, source).status_code == 403
    copied = client.post(path, json=payload, headers=system)
    assert copied.status_code == 200, copied.text
    assert copied.json()["settings"]["capacities"]["CAR"]["safe_capacity"] == 12
    assert copied.json()["settings"]["information"]["name"] == "TARGET"
    assert client.post(path, json=payload, headers=system).json()["code"] == "SETTINGS_CONFLICT"
    audit = db_session.scalar(select(AuditLog).where(AuditLog.action == "COPY_LOT_SETTINGS"))
    assert audit.building_id == UUID(target_id)
    assert audit.old_value["settings"]["capacities"]["CAR"]["safe_capacity"] == 0
    assert audit.new_value["copied_from_building_id"] == source_id


def test_reducing_settings_checks_real_occupancy_and_lane_changes_have_before_after(
    client, building_admin, db_session
):
    building_id, headers, _ = building_admin
    lane_id, _ = make_ready(client, headers)
    before = client.get(f"/api/v1/lanes/{lane_id}", headers=headers).json()
    response = client.patch(
        f"/api/v1/lanes/{lane_id}",
        json={"allowed_vehicle_types": ["CAR", "BICYCLE"], "camera": "replacement"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    audit = db_session.scalar(
        select(AuditLog).where(AuditLog.action == "UPDATE_LANE", AuditLog.entity_id == lane_id)
    )
    assert audit.old_value["camera"] == before["camera"]
    assert audit.new_value["camera"] == "replacement"
    assert (
        db_session.scalar(
            select(ParkingLot).where(ParkingLot.building_id == UUID(building_id))
        ).settings_revision
        == 1
    )
    assert db_session.get(Lane, UUID(lane_id)).allowed_vehicle_types == ["CAR", "BICYCLE"]
    assert client.post(f"/api/v1/lanes/{lane_id}/deactivate", headers=headers).status_code == 200
    db_session.expire_all()
    deactivated = db_session.scalar(
        select(AuditLog).where(AuditLog.action == "DEACTIVATE_LANE", AuditLog.entity_id == lane_id)
    )
    assert (
        deactivated.old_value["is_active"] is True and deactivated.new_value["is_active"] is False
    )
