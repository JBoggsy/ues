"""Integration tests for time control routes.

These tests verify the behavior of all time-related API endpoints:
- GET /simulator/time - Get current time state
- POST /simulator/time/advance - Advance time by duration
- POST /simulator/time/set - Jump to specific time
- POST /simulator/time/skip-to-next - Skip to next event
- POST /simulator/time/pause - Pause simulation
- POST /simulator/time/resume - Resume simulation
- POST /simulator/time/set-scale - Change time scale
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_simulation_engine
from main import app
from models.simulation import SimulationEngine


@pytest.fixture
def client_with_engine(fresh_engine):
    """Provide a TestClient with a fresh SimulationEngine injected.
    
    This fixture combines the TestClient with a fresh engine, using FastAPI's
    dependency override system to inject our test engine instead of the global one.
    
    Args:
        fresh_engine: A pytest fixture providing a fresh SimulationEngine.
    
    Yields:
        A tuple of (TestClient, SimulationEngine) for testing.
    """
    # Override the dependency to return our test engine
    app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine
    
    # Create the test client
    client = TestClient(app)
    
    # Start the simulation before each test
    # Most time operations require a running simulation
    response = client.post("/simulation/start", json={"auto_advance": False})
    assert response.status_code == 200, f"Failed to start simulation: {response.json()}"
    
    yield client, fresh_engine
    
    # Cleanup: Stop simulation and clear dependency overrides
    try:
        client.post("/simulation/stop")
    except Exception:
        pass  # Ignore errors during cleanup
    
    app.dependency_overrides.clear()


class TestGetTime:
    """Tests for GET /simulator/time endpoint."""
    
    def test_get_time_returns_current_state(self, client_with_engine):
        """Test that GET /simulator/time returns the current time state."""
        client, engine = client_with_engine
        
        # Get time via API
        response = client.get("/simulator/time")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Check all expected fields are present
        assert "current_time" in data
        assert "time_scale" in data
        assert "is_paused" in data
        assert "auto_advance" in data
        
        # Verify data matches engine state
        assert data["time_scale"] == 1.0
        assert data["is_paused"] is False
        assert data["auto_advance"] is False
        
        # Verify time is parseable and timezone-aware
        current_time = datetime.fromisoformat(data["current_time"])
        assert current_time.tzinfo is not None
    
    def test_get_time_reflects_engine_state(self, client_with_engine):
        """Test that GET /simulator/time reflects actual engine state changes."""
        client, engine = client_with_engine
        
        # Get initial time
        initial_response = client.get("/simulator/time")
        initial_data = initial_response.json()
        initial_time = datetime.fromisoformat(initial_data["current_time"])
        
        # Advance time via API
        advance_response = client.post(
            "/simulator/time/advance",
            json={"seconds": 3600}  # Advance 1 hour
        )
        assert advance_response.status_code == 200
        
        # Get time again
        updated_response = client.get("/simulator/time")
        updated_data = updated_response.json()
        updated_time = datetime.fromisoformat(updated_data["current_time"])
        
        # Verify time advanced by 1 hour
        time_diff = updated_time - initial_time
        assert abs(time_diff.total_seconds() - 3600) < 1  # Allow 1 second tolerance
    
    def test_get_time_when_paused(self, client_with_engine):
        """Test that GET /simulator/time correctly shows paused state."""
        client, engine = client_with_engine
        
        # Pause the simulation
        pause_response = client.post("/simulator/time/pause")
        assert pause_response.status_code == 200
        
        # Get time state
        response = client.get("/simulator/time")
        data = response.json()
        
        # Verify is_paused is True
        assert data["is_paused"] is True
    
    def test_get_time_with_modified_time_scale(self, client_with_engine):
        """Test that GET /simulator/time reflects time scale changes."""
        client, engine = client_with_engine
        
        # Set time scale to 2.0
        scale_response = client.post(
            "/simulator/time/set-scale",
            json={"scale": 2.0}
        )
        assert scale_response.status_code == 200
        
        # Get time state
        response = client.get("/simulator/time")
        data = response.json()
        
        # Verify time_scale is 2.0
        assert data["time_scale"] == 2.0
    
    def test_get_time_returns_consistent_format(self, client_with_engine):
        """Test that GET /simulator/time always returns ISO 8601 formatted times."""
        client, engine = client_with_engine
        
        # Get time multiple times
        for _ in range(3):
            response = client.get("/simulator/time")
            assert response.status_code == 200
            data = response.json()
            
            # Verify ISO 8601 format by parsing
            time_str = data["current_time"]
            parsed_time = datetime.fromisoformat(time_str)
            
            # Verify timezone awareness
            assert parsed_time.tzinfo is not None
            
            # Verify we can round-trip the format
            assert parsed_time.isoformat() == time_str or \
                   parsed_time.isoformat().replace('+00:00', 'Z') == time_str


# Note: Additional test classes for other time routes will be added as we progress
# This initial set establishes the testing pattern and infrastructure needs.
