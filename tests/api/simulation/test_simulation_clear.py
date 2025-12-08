"""Integration tests for POST /simulation/clear endpoint.

Tests verify that the simulation clear endpoint correctly clears
all state, removes events, handles time reset, and properly reports
what was cleared.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_simulation_engine
from main import app
from tests.api.helpers import make_event_request, location_event_data, email_event_data


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


class TestPostSimulationClear:
    """Tests for POST /simulation/clear endpoint."""

    # ===== Success Cases =====

    def test_clear_returns_success_response(self, client_with_engine):
        """Test that POST /simulation/clear returns a successful response.
        
        Verifies:
        - Response status code is 200
        - Response contains status="cleared"
        - Response contains expected fields
        """
        client, engine = client_with_engine
        
        response = client.post("/simulation/clear")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cleared"
        assert "events_removed" in data
        assert "modalities_cleared" in data
        assert "current_time" in data

    def test_clear_returns_events_removed_count(self, client_with_engine):
        """Test that POST /simulation/clear returns count of removed events.
        
        Verifies:
        - events_removed field is present
        - events_removed is a non-negative integer
        """
        client, engine = client_with_engine
        
        response = client.post("/simulation/clear")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["events_removed"], int)
        assert data["events_removed"] >= 0

    def test_clear_returns_modalities_cleared_count(self, client_with_engine):
        """Test that POST /simulation/clear returns count of cleared modalities.
        
        Verifies:
        - modalities_cleared field is present
        - modalities_cleared matches the number of modalities in the environment
        """
        client, engine = client_with_engine
        
        response = client.post("/simulation/clear")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["modalities_cleared"], int)
        assert data["modalities_cleared"] == 7  # location, time, weather, chat, email, calendar, sms

    def test_clear_removes_all_events(self, client_with_engine):
        """Test that POST /simulation/clear removes all events from the queue.
        
        Verifies:
        - Add some events
        - After clear, events are removed from queue
        """
        client, engine = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create multiple events
        for i in range(3):
            event_time = current_time + timedelta(minutes=i + 1)
            request = make_event_request(event_time, "location", location_event_data())
            response = client.post("/events", json=request)
            assert response.status_code in (200, 201)
        
        # Verify events exist
        events_response = client.get("/events")
        assert len(events_response.json()["events"]) == 3
        
        # Clear
        response = client.post("/simulation/clear")
        assert response.status_code == 200
        assert response.json()["events_removed"] == 3
        
        # Verify events are gone - need to restart simulation first
        client.post("/simulation/start", json={"auto_advance": False})
        events_response = client.get("/events")
        assert len(events_response.json()["events"]) == 0

    def test_clear_clears_email_state(self, client_with_engine):
        """Test that clear resets email state to empty.
        
        Verifies:
        - Add an email
        - After clear, email state is empty
        """
        client, engine = client_with_engine
        
        # Receive an email
        response = client.post(
            "/email/receive",
            json={
                "from_address": "sender@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Test Email",
                "body_text": "Hello!",
            },
        )
        assert response.status_code == 200
        
        # Verify email exists (check the engine state directly)
        assert len(engine.environment.get_state("email").emails) > 0
        
        # Clear
        response = client.post("/simulation/clear")
        assert response.status_code == 200
        
        # Verify email state is empty (check engine state directly)
        # State was cleared and update_count reset
        assert len(engine.environment.get_state("email").emails) == 0
        assert engine.environment.get_state("email").update_count == 0

    def test_clear_clears_location_state(self, client_with_engine):
        """Test that clear resets location state to empty.
        
        Verifies:
        - Set a location
        - After clear, location state is empty
        """
        client, engine = client_with_engine
        
        # Set location
        response = client.post(
            "/location/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "address": "New York, NY",
            },
        )
        assert response.status_code == 200
        
        # Verify location is set (check engine directly)
        loc_state = engine.environment.get_state("location")
        assert loc_state.current_latitude == 40.7128
        
        # Clear
        response = client.post("/simulation/clear")
        assert response.status_code == 200
        
        # Verify location is cleared (check engine directly)
        loc_state = engine.environment.get_state("location")
        assert loc_state.current_latitude is None
        assert loc_state.current_longitude is None
        assert loc_state.update_count == 0

    def test_clear_preserves_time_when_no_reset_time_provided(self, client_with_engine):
        """Test that clear preserves current time when reset_time_to is not provided.
        
        Verifies:
        - Note the current time
        - Clear without reset_time_to
        - Time remains the same
        """
        client, engine = client_with_engine
        
        # Get current time from engine
        original_time = engine.environment.time_state.current_time
        
        # Clear without time reset
        response = client.post("/simulation/clear")
        assert response.status_code == 200
        assert response.json()["time_reset"] is None
        # Time should be preserved
        assert engine.environment.time_state.current_time == original_time

    def test_clear_resets_time_when_reset_time_to_provided(self, client_with_engine):
        """Test that clear resets time when reset_time_to is provided.
        
        Verifies:
        - Clear with reset_time_to
        - Time is set to the specified value
        """
        client, engine = client_with_engine
        
        new_time = datetime(2024, 6, 15, 9, 0, 0, tzinfo=timezone.utc)
        
        # Clear with time reset
        response = client.post(
            "/simulation/clear",
            json={"reset_time_to": new_time.isoformat()},
        )
        assert response.status_code == 200
        assert response.json()["time_reset"] is not None
        # Verify engine time was actually reset
        assert engine.environment.time_state.current_time == new_time

    def test_clear_works_when_simulation_not_running(self, client_without_start):
        """Test that clear works even when simulation is not running.
        
        Verifies:
        - Simulation is not started
        - Clear succeeds
        """
        client, engine = client_without_start
        
        response = client.post("/simulation/clear")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cleared"

    def test_clear_stops_running_simulation(self, client_with_engine):
        """Test that clear stops a running simulation.
        
        Verifies:
        - Simulation is running
        - After clear, simulation is stopped
        """
        client, engine = client_with_engine
        
        # Verify simulation is running
        assert engine.is_running is True
        
        # Clear
        response = client.post("/simulation/clear")
        assert response.status_code == 200
        
        # Verify simulation is stopped
        assert engine.is_running is False

    # ===== Error Cases =====

    def test_clear_with_invalid_time_format(self, client_with_engine):
        """Test that clear returns 400 for invalid datetime format.
        
        Verifies:
        - Invalid reset_time_to returns 400
        """
        client, engine = client_with_engine
        
        response = client.post(
            "/simulation/clear",
            json={"reset_time_to": "not-a-valid-datetime"},
        )
        
        assert response.status_code == 400
        assert "Invalid datetime format" in response.json()["detail"]


class TestClearStateIntegrity:
    """Tests to verify state integrity after clear."""

    def test_cleared_states_pass_validation(self, client_with_engine):
        """Test that all cleared states pass validation.
        
        Verifies:
        - After clear, environment validation passes
        """
        client, engine = client_with_engine
        
        # Add some data first
        client.post(
            "/email/receive",
            json={
                "from_address": "test@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Test",
                "body_text": "Test",
            },
        )
        
        # Clear
        response = client.post("/simulation/clear")
        assert response.status_code == 200
        
        # Restart and validate
        client.post("/simulation/start", json={"auto_advance": False})
        
        validate_response = client.post("/environment/validate")
        assert validate_response.status_code == 200
        assert validate_response.json()["valid"] is True

    def test_multiple_clears_are_idempotent(self, client_with_engine):
        """Test that multiple clear operations are idempotent.
        
        Verifies:
        - Clear multiple times in succession
        - Results are consistent
        """
        client, engine = client_with_engine
        
        # First clear
        response1 = client.post("/simulation/clear")
        assert response1.status_code == 200
        
        # Restart for second clear
        client.post("/simulation/start", json={"auto_advance": False})
        
        # Second clear
        response2 = client.post("/simulation/clear")
        assert response2.status_code == 200
        
        # Both should clear 0 events (already empty)
        assert response2.json()["events_removed"] == 0
        # Modalities count should be consistent
        assert response2.json()["modalities_cleared"] == response1.json()["modalities_cleared"]
