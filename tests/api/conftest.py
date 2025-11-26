"""Shared fixtures for API integration tests.

This module provides common fixtures used across all API test files,
including TestClient setup and SimulationEngine dependency injection.
"""

import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_simulation_engine
from main import app


@pytest.fixture
def client_with_engine(fresh_engine):
    """Provide a TestClient with a fresh SimulationEngine injected.
    
    This fixture combines the TestClient with a fresh engine, using FastAPI's
    dependency override system to inject our test engine instead of the global one.
    It also starts the simulation in manual mode (auto_advance=False) before each
    test and stops it during cleanup.
    
    Args:
        fresh_engine: A pytest fixture providing a fresh SimulationEngine.
    
    Yields:
        A tuple of (TestClient, SimulationEngine) for testing.
        
    Example:
        def test_something(client_with_engine):
            client, engine = client_with_engine
            response = client.get("/some/endpoint")
            assert response.status_code == 200
    """
    # Override the dependency to return our test engine
    app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine
    
    # Create the test client
    client = TestClient(app)
    
    # Start the simulation before each test (manual mode for precise control)
    response = client.post("/simulation/start", json={"auto_advance": False})
    assert response.status_code == 200, f"Failed to start simulation: {response.json()}"
    
    yield client, fresh_engine
    
    # Cleanup: Stop simulation and clear dependency overrides
    try:
        client.post("/simulation/stop")
    except Exception:
        pass  # Ignore errors during cleanup
    
    app.dependency_overrides.clear()
