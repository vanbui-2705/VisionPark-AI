from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.users.models import User
from tests.conftest import login


def test_login_and_me_return_public_user(client: TestClient) -> None:
    login_body = login(client, "ADMIN", "admin-test-password")
    assert login_body["token_type"] == "bearer"
    assert login_body["expires_in"] == 3600
    assert login_body["user"]["role"] == "ADMIN"
    assert "password_hash" not in login_body["user"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login_body['access_token']}"},
    )
    assert response.status_code == 200
    assert response.json()["username"] == "admin"
    assert "password_hash" not in response.json()


def test_wrong_password_uses_generic_error_contract(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrong"},
        headers={"X-Correlation-ID": "login-test-123"},
    )
    assert response.status_code == 401
    assert response.headers["X-Correlation-ID"] == "login-test-123"
    assert response.json() == {
        "code": "INVALID_CREDENTIALS",
        "message": "Username or password is incorrect.",
        "details": {},
        "correlation_id": "login-test-123",
    }


def test_inactive_user_cannot_login(client: TestClient, db_session: Session) -> None:
    operator = db_session.scalar(select(User).where(User.username == "operator"))
    assert operator is not None
    operator.is_active = False
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "operator", "password": "operator-test-password"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"


def test_me_requires_a_valid_bearer_token(client: TestClient) -> None:
    missing = client.get("/api/v1/auth/me")
    assert missing.status_code == 401
    assert missing.json()["code"] == "UNAUTHENTICATED"

    invalid = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-token"})
    assert invalid.status_code == 401
    assert invalid.json()["code"] == "UNAUTHENTICATED"


def test_rbac_allows_admin_and_rejects_operator(client: TestClient) -> None:
    admin = login(client, "admin", "admin-test-password")
    allowed = client.get(
        "/api/v1/test/admin-only",
        headers={"Authorization": f"Bearer {admin['access_token']}"},
    )
    assert allowed.status_code == 200

    operator = login(client, "operator", "operator-test-password")
    forbidden = client.get(
        "/api/v1/test/admin-only",
        headers={"Authorization": f"Bearer {operator['access_token']}"},
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "FORBIDDEN"
    assert forbidden.json()["details"] == {"required_roles": ["ADMIN"]}
