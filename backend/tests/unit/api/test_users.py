from fastapi.testclient import TestClient


def test_list_users_as_admin(client: TestClient, admin_token: str):
    res = client.get("/api/v1/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    usernames = [u["username"] for u in data]
    assert "admin" in usernames


def test_list_users_forbidden_for_operator(client: TestClient, operator_headers: dict[str, str]):
    res = client.get("/api/v1/users", headers=operator_headers)
    assert res.status_code == 403


def test_create_and_patch_user(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    create_payload = {
        "username": "newuser01",
        "display_name": "New User",
        "password": "secretpassword123",
        "role": "OPERATOR",
        "active": True,
    }
    create_res = client.post("/api/v1/users", json=create_payload, headers=headers)
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["username"] == "newuser01"
    assert created["role"] == "OPERATOR"
    user_id = created["id"]

    # Patch user
    patch_payload = {
        "display_name": "Updated Name",
        "role": "ACCOUNTANT",
        "active": False,
    }
    patch_res = client.patch(f"/api/v1/users/{user_id}", json=patch_payload, headers=headers)
    assert patch_res.status_code == 200
    patched = patch_res.json()
    assert patched["display_name"] == "Updated Name"
    assert patched["role"] == "ACCOUNTANT"
    assert patched["is_active"] is False


def test_create_user_conflict(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    payload = {
        "username": "admin",
        "display_name": "Admin Clone",
        "password": "somepassword123",
        "role": "ADMIN",
    }
    res = client.post("/api/v1/users", json=payload, headers=headers)
    assert res.status_code == 409


def test_list_roles(client: TestClient, operator_headers: dict[str, str]):
    res = client.get("/api/v1/roles", headers=operator_headers)
    assert res.status_code == 200
    roles = res.json()
    names = [r["name"] for r in roles]
    assert "ADMIN" in names
    assert "OPERATOR" in names
    assert "ACCOUNTANT" in names
    assert "TECHNICIAN" in names
