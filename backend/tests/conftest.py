"""
Basic test configuration and fixtures.
"""

import pytest
from fastapi.testclient import TestClient
from src.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def settings():
    """Settings fixture for testing."""
    from src.core.config import get_settings

    return get_settings()
