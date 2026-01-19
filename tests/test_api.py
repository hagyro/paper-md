"""API endpoint tests."""

import pytest
from fastapi.testclient import TestClient

from paper_md.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_convert_no_file(client):
    """Test convert endpoint without file."""
    response = client.post("/convert")
    assert response.status_code == 422  # Validation error


def test_convert_non_pdf(client):
    """Test convert endpoint with non-PDF file."""
    response = client.post(
        "/convert",
        files={"file": ("test.txt", b"not a pdf", "text/plain")},
    )
    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


def test_status_not_found(client):
    """Test status endpoint with invalid job ID."""
    response = client.get("/status/invalid-job-id")
    assert response.status_code == 404


def test_result_not_found(client):
    """Test result endpoint with invalid job ID."""
    response = client.get("/result/invalid-job-id")
    assert response.status_code == 404
