"""Shared fixtures for API integration tests.

This module provides common fixtures used across all API test files,
including TestClient setup and SimulationEngine dependency injection.
"""

import pytest
from fastapi.testclient import TestClient

from ues.api.auth import initialize_api_key_registry, shutdown_api_key_registry
from ues.api.dependencies import get_simulation_engine
from ues.main import app


@pytest.fixture
def client_with_engine(fresh_engine):
    """Provide a TestClient with a fresh SimulationEngine and admin API key.
    
    This fixture combines the TestClient with a fresh engine, using FastAPI's
    dependency override system to inject our test engine instead of the global one.
    It also initializes the API key registry and sets up admin authentication,
    starts the simulation in manual mode (auto_advance=False) before each test,
    and handles cleanup.
    
    Args:
        fresh_engine: A pytest fixture providing a fresh SimulationEngine.
    
    Yields:
        A tuple of (TestClient, SimulationEngine) for testing.
        The TestClient has the admin API key set in its default headers.
        
    Example:
        def test_something(client_with_engine):
            client, engine = client_with_engine
            response = client.get("/some/endpoint")
            assert response.status_code == 200
    """
    # Override the dependency to return our test engine
    app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine
    
    # Initialize API key registry and get admin key
    admin_secret, _admin_key = initialize_api_key_registry()
    
    # Create the test client with admin auth
    client = TestClient(app)
    client.headers["X-API-Key"] = admin_secret
    
    # Start the simulation before each test (manual mode for precise control)
    response = client.post("/simulation/start", json={"auto_advance": False})
    assert response.status_code == 200, f"Failed to start simulation: {response.json()}"
    
    yield client, fresh_engine
    
    # Cleanup: Stop simulation, shutdown registry, and clear dependency overrides
    try:
        client.post("/simulation/stop")
    except Exception:
        pass  # Ignore errors during cleanup
    
    shutdown_api_key_registry()
    app.dependency_overrides.clear()
