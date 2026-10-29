import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(autouse=True)
def offline_generation(monkeypatch):
    # Security tests must not depend on an inherited provider key or network access.
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c

def token(client, role="employee", tenant="alpha"):
    response = client.post("/login", json={"email": f"{role}@{tenant}.example", "password": "demo-password"})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]

def headers(client, role="employee", tenant="alpha"):
    return {"Authorization": "Bearer " + token(client, role, tenant)}
