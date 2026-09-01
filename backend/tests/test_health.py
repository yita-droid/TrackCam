"""
Stage 2 smoke tests — app boots, CORS is configured, and /health responds
correctly whether or not a real Postgres instance is reachable.

These tests do NOT require a GPU or any AI model, per the project's testing
requirements. They also don't require a live Postgres — check_database_connection()
is designed to fail gracefully, so /health should return 200 with
status="degraded" rather than raising, even with no DB running.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"]
    assert body["docs"] == "/docs"


def test_health_endpoint_reports_status():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert "database" in body
    assert "connected" in body["database"]


def test_docs_available():
    response = client.get("/docs")
    assert response.status_code == 200


def test_cors_header_present_for_frontend_origin():
    response = client.get(
        "/health",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
