import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    "method,path,code,status",
    [
        ("get", "/missing", "NOT_FOUND", 404),
        ("post", "/health/live", "METHOD_NOT_ALLOWED", 405),
        ("get", "/api/v1/auth/me", "UNAUTHENTICATED", 401),
    ],
)
def test_http_errors_use_shared_contract(client, method, path, code, status):
    response = getattr(client, method)(path, headers={"X-Correlation-ID": "contract-check"})
    assert response.status_code == status
    assert response.json()["code"] == code
    assert set(response.json()) == {"code", "message", "details", "correlation_id"}
    assert response.json()["correlation_id"] == response.headers["X-Correlation-ID"]
    if status == 405:
        assert "GET" in response.headers["allow"]


def test_unexpected_error_has_correlation_header(app):
    @app.get("/failure")
    def failure():
        raise RuntimeError("private implementation detail")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/failure", headers={"X-Correlation-ID": "failure-check"})
    assert response.status_code == 500
    assert response.headers["X-Correlation-ID"] == response.json()["correlation_id"]
    assert "private implementation" not in response.text


def test_cors_exposes_correlation_id(client):
    response = client.get("/health/live", headers={"Origin": "http://localhost:5173"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "X-Correlation-ID" in response.headers["access-control-expose-headers"]
