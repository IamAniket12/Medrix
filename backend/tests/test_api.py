"""
Test API endpoints.
"""

import pytest
from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert data["status"] == "running"


def test_health_check(client: TestClient):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data


def test_documents_test_endpoint(client: TestClient):
    """Test documents test endpoint."""
    response = client.get("/api/v1/documents/test")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "config" in data
