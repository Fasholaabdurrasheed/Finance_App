from fastapi.testclient import TestClient
from pathlib import Path
from uuid import uuid4
import tempfile

from app.main import app

CLIENT = TestClient(app)


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
    unique_id = uuid4().hex[:8]
    token = register_and_login(
        CLIENT,
        f"uploader-{unique_id}@example.com",
        f"uploader_{unique_id}",
        "StrongPass123!",
    )
    headers = {"Authorization": f"Bearer {token}"}

    sample_csv = (
        "date,amount,description,category\n"
        "2026-05-01,1000,Salary,Allowance\n"
        "2026-05-02,-50,Lunch,Food\n"
    )

    with tempfile.NamedTemporaryFile(mode="w+b", suffix=".csv", delete=False) as temp_file:
        temp_file.write(sample_csv.encode("utf-8"))
        temp_file.flush()
        temp_path = Path(temp_file.name)

    try:
        with open(temp_path, "rb") as f:
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
    finally:
        if temp_path.exists():
            temp_path.unlink()
