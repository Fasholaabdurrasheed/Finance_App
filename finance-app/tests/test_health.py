from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_responds() -> None:
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert "detail" in body
    assert "db_connected" in body["detail"]
