from fastapi.testclient import TestClient
from pathlib import Path

from app.main import app

CLIENT = TestClient(app)
SAMPLE_CSV = Path(__file__).resolve().parents[1] / "sample_transactions_simple.csv"


def register_and_login(client: TestClient, email: str, username: str, password: str) -> str:
    # register
    resp = client.post("/api/v1/auth/register", json={"email": email, "username": username, "password": password})
    assert resp.status_code == 201
    # login (OAuth2 form)
    resp = client.post("/api/v1/auth/login", data={"username": username, "password": password})
    assert resp.status_code == 200
    body = resp.json()
    return body["access_token"]


def test_upload_and_provenance_flow():
    token = register_and_login(CLIENT, "uploader@example.com", "uploader", "StrongPass123!")
    headers = {"Authorization": f"Bearer {token}"}

    with open(SAMPLE_CSV, "rb") as f:
        files = {"file": ("sample.csv", f, "text/csv")}
        resp = CLIENT.post("/api/v1/uploads/excel", headers=headers, files=files)

    assert resp.status_code == 201
    body = resp.json()
    assert "inserted_rows" in body
    assert body["inserted_rows"] >= 0

    # list uploads
    resp = CLIENT.get("/api/v1/uploads", headers=headers)
    assert resp.status_code == 200
    uploads = resp.json().get("uploads", [])
    assert len(uploads) >= 1
    upload_id = uploads[0]["id"]

    # status
    resp = CLIENT.get(f"/api/v1/uploads/{upload_id}/status", headers=headers)
    assert resp.status_code == 200
    status_body = resp.json()
    assert "status" in status_body

    # download
    resp = CLIENT.get(f"/api/v1/uploads/{upload_id}/download", headers=headers)
    assert resp.status_code == 200
    assert resp.content is not None
