from fastapi.testclient import TestClient

from app.core.readiness import ReadinessStatus, RuntimeALPRProbe


class ReadyALPRProbe:
    def readiness(self) -> ReadinessStatus:
        return ReadinessStatus(
            ready=True,
            message="Mock ALPR provider is ready.",
            provider="mock",
            version="mock-v1",
        )


class ReadyRuntime:
    def is_ready(self) -> tuple[bool, str]:
        return True, "ALPR runtime is ready."


def test_liveness_does_not_depend_on_database_or_alpr(client: TestClient) -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_readiness_reports_wired_mock_as_ready(client: TestClient) -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["database"]["status"] == "ready"
    assert response.json()["alpr"]["status"] == "ready"
    assert response.json()["alpr"]["provider"] == "mock"


def test_readiness_is_ready_when_all_dependencies_are_ready(
    client: TestClient,
) -> None:
    client.app.state.alpr_readiness_probe = ReadyALPRProbe()
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["alpr"]["version"] == "mock-v1"


def test_runtime_adapter_exposes_provider_and_version(client: TestClient) -> None:
    client.app.state.alpr_readiness_probe = RuntimeALPRProbe(
        ReadyRuntime(), provider="mock", version="mock-alpr-0.1.0"
    )
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["alpr"]["provider"] == "mock"
    assert response.json()["alpr"]["version"] == "mock-alpr-0.1.0"
