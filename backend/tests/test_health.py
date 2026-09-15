"""API foundation tests."""

from fastapi.testclient import TestClient

from backend.app.main import app


def test_health_endpoint_is_available_without_mongo() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "HAVCAN API"
    assert payload["database"] == "not_configured"