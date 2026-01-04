import pytest
from fastapi.testclient import TestClient
from main import app
from dependencies import get_current_user

@pytest.fixture
def client():
    # Override dependencies if needed (e.g. auth)
    # For now, we return a simple client. 
    # Mocks can be applied in specific tests or here as needed.
    with TestClient(app) as c:
        yield c

@pytest.fixture
def mock_auth_user(client):
    """
    Overrides the get_current_user dependency to bypass auth.
    """
    app.dependency_overrides[get_current_user] = lambda: "test@example.com"
    yield
    app.dependency_overrides = {}
