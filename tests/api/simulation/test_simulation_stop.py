"""Integration tests for POST /simulation/stop endpoint.

Tests verify that the simulation stop endpoint correctly stops
the simulation, returns execution summary, handles graceful shutdown,
and reports proper error conditions.
"""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_simulation_engine
from main import app
from tests.api.helpers import make_event_request, location_event_data


@pytest.fixture
def client_without_start(fresh_engine):
    """Provide a TestClient with a fresh SimulationEngine that is NOT started.
    
    Unlike client_with_engine, this fixture does NOT start the simulation,
    allowing tests to verify behavior with unstarted simulation.
    
    Yields:
        A tuple of (TestClient, SimulationEngine) for testing.
    """
    app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine
    client = TestClient(app)
    
    yield client, fresh_engine
    
    # Cleanup
    try:
        if fresh_engine.is_running:
            client.post("/simulation/stop")
    except Exception:
        pass
    
    app.dependency_overrides.clear()


class TestPostSimulationStop:
    """Tests for POST /simulation/stop endpoint."""

    # ===== Success Cases =====

    def test_stop_simulation_returns_success_response(self, client_with_engine):
        """Test that POST /simulation/stop returns a successful response.
        
        Verifies:
        - Response status code is 200
        - Response contains expected fields (status, final_time, etc.)
        """
        client, engine = client_with_engine
        
        response = client.post("/simulation/stop")
        
        assert response.status_code == 200
        data = response.json()
        assert "simulation_id" in data
        assert "status" in data
        assert "final_time" in data
        assert "total_events" in data
        assert "events_executed" in data
        assert "events_failed" in data

    def test_stop_simulation_returns_simulation_id(self, client_with_engine):
        """Test that POST /simulation/stop returns the simulation_id.
        
        Verifies:
        - simulation_id field is present in response
        - simulation_id matches the running simulation's ID
        """
        client, engine = client_with_engine
        
        # Get the simulation_id from status before stopping
        status_response = client.get("/simulation/status")
        # Note: status endpoint doesn't return simulation_id, so we check from engine
        
        response = client.post("/simulation/stop")
        
        assert response.status_code == 200
        data = response.json()
        assert data["simulation_id"]  # Non-empty string
        assert data["simulation_id"] == engine.simulation_id

    def test_stop_simulation_returns_stopped_status(self, client_with_engine):
        """Test that POST /simulation/stop indicates stopped status.
        
        Verifies:
        - status field in response is "stopped"
        """
        client, engine = client_with_engine
        
        response = client.post("/simulation/stop")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stopped"

    def test_stop_simulation_returns_final_time(self, client_with_engine):
        """Test that POST /simulation/stop returns the final simulation time.
        
        Verifies:
        - final_time field is present
        - final_time is valid ISO 8601 format
        - final_time reflects the time when simulation stopped
        """
        client, engine = client_with_engine
        
        response = client.post("/simulation/stop")
        
        assert response.status_code == 200
        data = response.json()
        assert "final_time" in data
        
        # Verify it's valid ISO 8601 format
        final_time = datetime.fromisoformat(data["final_time"])
        assert final_time.tzinfo is not None  # Timezone-aware

    def test_stop_simulation_returns_event_counts(self, client_with_engine):
        """Test that POST /simulation/stop returns event statistics.
        
        Verifies:
        - total_events count is present
        - events_executed count is present
        - events_failed count is present
        - Counts are non-negative integers
        """
        client, engine = client_with_engine
        
        response = client.post("/simulation/stop")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data["total_events"], int)
        assert isinstance(data["events_executed"], int)
        assert isinstance(data["events_failed"], int)
        
        assert data["total_events"] >= 0
        assert data["events_executed"] >= 0
        assert data["events_failed"] >= 0

    def test_stop_simulation_event_counts_accurate(self, client_with_engine):
        """Test that POST /simulation/stop returns accurate event counts.
        
        Verifies:
        - After creating and executing some events, counts are accurate
        - events_executed matches actual executed event count
        """
        client, engine = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create an event in the near future
        event_time = current_time + timedelta(seconds=1)
        request = make_event_request(event_time, "location", location_event_data())
        
        create_response = client.post("/events", json=request)
        assert create_response.status_code == 200
        
        # Advance time to execute the event
        advance_response = client.post("/simulator/time/advance", json={"seconds": 2})
        assert advance_response.status_code == 200
        
        # Stop and check counts
        response = client.post("/simulation/stop")
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_events"] >= 1
        # Event should be executed (location events work)
        assert data["events_executed"] >= 1

    def test_stop_simulation_prevents_further_operations(self, client_with_engine):
        """Test that POST /simulation/stop prevents further time operations.
        
        Verifies:
        - After stopping, time advance operations fail appropriately
        """
        client, engine = client_with_engine
        
        # Stop the simulation
        stop_response = client.post("/simulation/stop")
        assert stop_response.status_code == 200
        
        # Try to advance time - should fail
        advance_response = client.post("/simulator/time/advance", json={"seconds": 10})
        assert advance_response.status_code == 400
        assert "not running" in advance_response.json()["detail"].lower()

    def test_stop_simulation_allows_restart(self, client_with_engine):
        """Test that POST /simulation/stop allows the simulation to be restarted.
        
        Verifies:
        - After stopping, POST /simulation/start succeeds
        - Simulation is running after restart
        
        Note: Same engine retains the same simulation_id.
        """
        client, engine = client_with_engine
        
        # Stop the simulation
        stop_response = client.post("/simulation/stop")
        assert stop_response.status_code == 200
        
        # Restart the simulation
        start_response = client.post("/simulation/start", json={})
        assert start_response.status_code == 200
        
        # Verify it's running
        status_response = client.get("/simulation/status")
        assert status_response.json()["is_running"] is True

    # ===== Error Cases =====

    def test_stop_simulation_when_not_running(self, client_without_start):
        """Test that POST /simulation/stop handles not-running state gracefully.
        
        Note: Uses client_without_start to avoid auto-start.
        
        Verifies:
        - Response status code is 200
        - Response has simulation_id and status fields populated
        - Other fields (final_time, total_events, etc.) are None
        """
        client, engine = client_without_start
        
        response = client.post("/simulation/stop")
        
        assert response.status_code == 200
        data = response.json()
        
        # Required fields are present
        assert data["simulation_id"] == engine.simulation_id
        assert data["status"] == "stopped"
        
        # Optional fields are None when simulation wasn't running
        assert data["final_time"] is None
        assert data["total_events"] is None
        assert data["events_executed"] is None
        assert data["events_failed"] is None

    # ===== Auto-advance Mode =====

    def test_stop_simulation_stops_auto_advance(self, client_without_start):
        """Test that POST /simulation/stop stops auto-advance mode.
        
        Verifies:
        - Simulation started with auto_advance=True
        - POST /simulation/stop successfully stops it
        - Status shows is_running=False after stop
        """
        client, engine = client_without_start
        
        # Start with auto-advance
        start_response = client.post("/simulation/start", json={
            "auto_advance": True,
            "time_scale": 1.0
        })
        assert start_response.status_code == 200
        
        # Stop the simulation
        stop_response = client.post("/simulation/stop")
        assert stop_response.status_code == 200
        assert stop_response.json()["status"] == "stopped"
        
        # Verify it's actually stopped
        status_response = client.get("/simulation/status")
        assert status_response.json()["is_running"] is False

    # ===== State Verification =====

    def test_stop_simulation_final_time_matches_last_state(self, client_with_engine):
        """Test that final_time in stop response matches last known time.
        
        Verifies:
        - Advance time, then stop
        - final_time matches the time after advancement
        """
        client, engine = client_with_engine
        
        # Get initial time
        initial_response = client.get("/simulator/time")
        initial_time = datetime.fromisoformat(initial_response.json()["current_time"])
        
        # Advance time by 1 hour
        advance_response = client.post("/simulator/time/advance", json={"seconds": 3600})
        assert advance_response.status_code == 200
        
        # Get current time after advance
        time_response = client.get("/simulator/time")
        expected_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Stop and verify final_time
        stop_response = client.post("/simulation/stop")
        assert stop_response.status_code == 200
        
        final_time = datetime.fromisoformat(stop_response.json()["final_time"])
        assert final_time == expected_time

    def test_stop_simulation_preserves_executed_events(self, client_with_engine):
        """Test that stopping preserves already-executed events.
        
        Verifies:
        - Events executed before stop remain in executed state
        - Event can still be queried after stop
        """
        client, engine = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create an event
        event_time = current_time + timedelta(seconds=1)
        request = make_event_request(event_time, "location", location_event_data())
        
        create_response = client.post("/events", json=request)
        assert create_response.status_code == 200
        event_id = create_response.json()["event_id"]
        
        # Execute the event
        advance_response = client.post("/simulator/time/advance", json={"seconds": 2})
        assert advance_response.status_code == 200
        
        # Stop the simulation
        stop_response = client.post("/simulation/stop")
        assert stop_response.status_code == 200
        
        # Verify event is still accessible and shows executed status
        event_response = client.get(f"/events/{event_id}")
        assert event_response.status_code == 200
        event_data = event_response.json()
        assert event_data["status"] in ["executed", "failed"]

    def test_stop_simulation_with_pending_events(self, client_with_engine):
        """Test that POST /simulation/stop handles pending events correctly.
        
        Verifies:
        - Pending events remain pending after stop
        - total_events includes pending events in count
        """
        client, engine = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create an event far in the future (won't execute)
        event_time = current_time + timedelta(hours=24)
        request = make_event_request(event_time, "location", location_event_data())
        
        create_response = client.post("/events", json=request)
        assert create_response.status_code == 200
        event_id = create_response.json()["event_id"]
        
        # Stop without advancing time
        stop_response = client.post("/simulation/stop")
        assert stop_response.status_code == 200
        data = stop_response.json()
        
        # Verify the event is counted
        assert data["total_events"] >= 1
        
        # Verify the event is still pending
        event_response = client.get(f"/events/{event_id}")
        assert event_response.status_code == 200
        assert event_response.json()["status"] == "pending"

    def test_stop_simulation_idempotent_when_already_stopped(self, client_with_engine):
        """Test that stopping an already-stopped simulation is handled gracefully.
        
        Verifies:
        - First stop succeeds with full data
        - Second stop succeeds with None values for execution data
        """
        client, engine = client_with_engine
        
        # First stop - should succeed with full data
        first_response = client.post("/simulation/stop")
        assert first_response.status_code == 200
        first_data = first_response.json()
        assert first_data["final_time"] is not None
        assert first_data["total_events"] is not None
        
        # Second stop - should succeed but with None values
        second_response = client.post("/simulation/stop")
        assert second_response.status_code == 200
        second_data = second_response.json()
        assert second_data["simulation_id"] == engine.simulation_id
        assert second_data["status"] == "stopped"
        assert second_data["final_time"] is None
        assert second_data["total_events"] is None
        assert second_data["events_executed"] is None
        assert second_data["events_failed"] is None
