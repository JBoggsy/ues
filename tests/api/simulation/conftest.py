"""Pytest fixtures for simulation API tests.

Provides authenticated test clients for simulation endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from ues.api.auth import initialize_api_key_registry, shutdown_api_key_registry
from ues.api.dependencies import get_simulation_engine
from ues.main import app


@pytest.fixture
def client_without_start(fresh_engine):
    """Provide a TestClient with a fresh SimulationEngine that is NOT started.
    
    Unlike client_with_engine, this fixture does NOT start the simulation,
    allowing tests to verify the start endpoint behavior.
    
    Yields:
        A tuple of (TestClient, SimulationEngine) for testing.
    """
    app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine
    admin_secret, _ = initialize_api_key_registry()
    client = TestClient(app)
    client.headers["X-API-Key"] = admin_secret
    
    yield client, fresh_engine
    
    # Cleanup: Stop simulation if running and clear dependency overrides
    try:
        if fresh_engine.is_running:
            client.post("/simulation/stop")
    except Exception:
        pass
    
    shutdown_api_key_registry()
    app.dependency_overrides.clear()
