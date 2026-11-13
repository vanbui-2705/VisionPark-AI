from uuid import uuid4

from tests.conftest import login


def test_created_account_receives_its_assigned_building(client, admin_token):
    system = {"Authorization": f"Bearer {admin_token}"}
    code = f"ASSIGN-{uuid4().hex[:8]}"
    building = client.post(
        "/api/v1/buildings",
        json={"code": code, "name": "Assigned building", "address": "Test"},
        headers=system,
    )
    assert building.status_code == 201, building.text
    building_id = building.json()["id"]

    created = client.post(
        "/api/v1/users",
        json={
            "username": "assigned-operator",
            "display_name": "Assigned operator",
            "password": "assigned-test-password",
            "role": "OPERATOR",
            "building_id": building_id,
            "active": True,
        },
        headers=system,
    )
    assert created.status_code == 201, created.text
    user_id = created.json()["id"]

    login_result = login(client, "assigned-operator", "assigned-test-password")
    assigned = {"Authorization": f"Bearer {login_result['access_token']}"}
    users = client.get("/api/v1/users", headers=system)
    detail = client.get(f"/api/v1/users/{user_id}", headers=system)
    me = client.get("/api/v1/auth/me", headers=assigned)
    buildings = client.get("/api/v1/buildings", headers=assigned)

    assert users.status_code == 200, users.text
    assert detail.status_code == 200, detail.text
    assert me.status_code == 200, me.text
    assert buildings.status_code == 200, buildings.text
    assert {
        "create_response": created.json().get("building_id"),
        "list_response": next(
            item["building_id"] for item in users.json() if item["id"] == user_id
        ),
        "detail_response": detail.json().get("building_id"),
        "login_response": login_result["user"].get("building_id"),
        "current_user": me.json().get("building_id"),
        "visible_buildings": [item["id"] for item in buildings.json()],
    } == {
        "create_response": building_id,
        "list_response": building_id,
        "detail_response": building_id,
        "login_response": building_id,
        "current_user": building_id,
        "visible_buildings": [building_id],
    }
