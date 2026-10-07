from sqlalchemy import select

from app.modules.audit_logs.models import AuditLog


def test_admin_user_management_and_operator_rbac(client, db_session, admin_token, operator_headers):
    headers = {"Authorization": f"Bearer {admin_token}"}
    payload = {
        "username": " New.Operator ",
        "display_name": "New Operator",
        "password": "test-password-2026",
        "email": " NEW@EXAMPLE.COM ",
        "role": "OPERATOR",
    }
    created = client.post("/api/v1/users", json=payload, headers=headers)
    assert created.status_code == 201, created.text
    user = created.json()
    assert user["username"] == "new.operator"
    assert user["email"] == "new@example.com"
    assert "password_hash" not in user
    assert "password" not in user
    assert client.get(f"/api/v1/users/{user['id']}", headers=headers).status_code == 200
    assert (
        len(client.get("/api/v1/users?q=new&active=true&role=OPERATOR", headers=headers).json())
        == 1
    )
    assert client.post("/api/v1/users", json=payload, headers=headers).status_code == 409
    updated = client.patch(
        f"/api/v1/users/{user['id']}", json={"active": False, "email": None}, headers=headers
    )
    assert updated.status_code == 200
    assert updated.json()["is_active"] is False
    assert updated.json()["email"] is None
    login = client.post(
        "/api/v1/auth/login", json={"username": "new.operator", "password": payload["password"]}
    )
    assert login.status_code == 401
    assert client.get("/api/v1/users", headers=operator_headers).status_code == 403
    assert (
        client.patch(
            f"/api/v1/users/{user['id']}", json={"role": "ADMIN"}, headers=operator_headers
        ).status_code
        == 403
    )
    assert client.get("/api/v1/roles", headers=headers).status_code == 200
    assert client.get("/api/v1/users").status_code == 401
    audit = db_session.scalars(select(AuditLog).where(AuditLog.entity_type == "User")).all()
    assert len(audit) == 2
    assert payload["password"] not in str([row.new_value for row in audit])


def test_admin_cannot_disable_or_demote_self(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    admin = client.get("/api/v1/auth/me", headers=headers).json()
    for payload in ({"active": False}, {"role": "OPERATOR"}):
        response = client.patch(f"/api/v1/users/{admin['id']}", json=payload, headers=headers)
        assert response.status_code == 409
        assert response.json()["code"] == "SELF_ACCESS_CHANGE"
    invalid = client.patch(
        f"/api/v1/users/{admin['id']}", json={"display_name": None}, headers=headers
    )
    assert invalid.status_code == 422


def test_public_registration_is_disabled_and_cannot_assign_admin(client):
    payload = {"username": "visitor", "display_name": "Visitor", "password": "Visitor123"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 403
    client.app.state.settings.public_registration_enabled = True
    assert (
        client.post("/api/v1/auth/register", json={**payload, "role": "ADMIN"}).status_code == 422
    )
    registered = client.post("/api/v1/auth/register", json=payload)
    assert registered.status_code == 201
    assert registered.json()["role"] == "OPERATOR"
