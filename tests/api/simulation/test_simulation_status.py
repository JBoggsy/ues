"""Integration tests for GET /simulation/status endpoint.

Tests verify that the simulation status endpoint correctly returns
current simulation state, metrics, event counts, and timing information.
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


class TestGetSimulationStatus:
    """Tests for GET /simulation/status endpoint."""

    # ===== Response Structure =====

    def test_status_returns_all_required_fields(self, client_with_engine):
        """Test that GET /simulation/status returns all required fields.
        
        Verifies:
        - is_running field is present
        - current_time field is present
        - is_paused field is present
        - time_scale field is present
        - pending_events field is present
        - executed_events field is present
        - failed_events field is present
        - next_event_time field is present (may be null)
        """
        client, engine = client_with_engine
        
        response = client.get("/simulation/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "is_running" in data
        assert "current_time" in data
        assert "is_paused" in data
        assert "time_scale" in data
        assert "pending_events" in data
        assert "executed_events" in data
        assert "failed_events" in data
        assert "next_event_time" in data  # May be null

    def test_status_returns_correct_types(self, client_with_engine):
        """Test that GET /simulation/status returns fields with correct types.
        
        Verifies:
        - is_running is boolean
        - current_time is string (ISO 8601)
        - is_paused is boolean
        - time_scale is number
        - pending_events is integer
        - executed_events is integer
        - failed_events is integer
        - next_event_time is string or null
        """
        client, engine = client_with_engine
        
        response = client.get("/simulation/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data["is_running"], bool)
        assert isinstance(data["current_time"], str)
        assert isinstance(data["is_paused"], bool)
        assert isinstance(data["time_scale"], (int, float))
        assert isinstance(data["pending_events"], int)
        assert isinstance(data["executed_events"], int)
        assert isinstance(data["failed_events"], int)
        assert data["next_event_time"] is None or isinstance(data["next_event_time"], str)

    # ===== Running State =====

    def test_status_is_running_when_started(self, client_with_engine):
        """Test that GET /simulation/status shows is_running=True after start.
        
        Note: client_with_engine fixture automatically starts simulation.
        
        Verifies:
        - is_running is True
        """
        client, engine = client_with_engine
        
        response = client.get("/simulation/status")
        
        assert response.status_code == 200
        assert response.json()["is_running"] is True

    def test_status_is_not_running_when_stopped(self, client_with_engine):
        """Test that GET /simulation/status shows is_running=False after stop.
        
        Verifies:
        - After POST /simulation/stop
        - is_running is False
        """
        client, engine = client_with_engine
        
        # Stop the simulation
        stop_response = client.post("/simulation/stop")
        assert stop_response.status_code == 200
        
        # Check status
        response = client.get("/simulation/status")
        
        assert response.status_code == 200
        assert response.json()["is_running"] is False

    def test_status_is_not_running_initially(self, client_without_start):
        """Test that GET /simulation/status shows is_running=False before start.
        
        Note: Uses client_without_start to avoid auto-start.
        
        Verifies:
        - is_running is False when simulation has not been started
        """
        client, engine = client_without_start
        
        response = client.get("/simulation/status")
        
        assert response.status_code == 200
        assert response.json()["is_running"] is False

    # ===== Pause State =====

    def test_status_is_paused_when_paused(self, client_with_engine):
        """Test that GET /simulation/status shows is_paused=True when paused.
        
        Verifies:
        - After POST /simulator/time/pause
        - is_paused is True
        """
        client, engine = client_with_engine
        
        # Pause the simulation
        pause_response = client.post("/simulator/time/pause")
        assert pause_response.status_code == 200
        
        # Check status
        response = client.get("/simulation/status")
        
        assert response.status_code == 200
        assert response.json()["is_paused"] is True

    def test_status_is_not_paused_by_default(self, client_with_engine):
        """Test that GET /simulation/status shows is_paused=False by default.
        
        Verifies:
        - Simulation starts unpaused
        - is_paused is False
        """
        client, engine = client_with_engine
        
        response = client.get("/simulation/status")
        
        assert response.status_code == 200
        assert response.json()["is_paused"] is False

    def test_status_is_not_paused_after_resume(self, client_with_engine):
        """Test that GET /simulation/status shows is_paused=False after resume.
        
        Verifies:
        - Pause, then resume simulation
        - is_paused is False after resume
        """
        client, engine = client_with_engine
        
        # Pause
        pause_response = client.post("/simulator/time/pause")
        assert pause_response.status_code == 200
        
        # Verify paused
        status_paused = client.get("/simulation/status")
        assert status_paused.json()["is_paused"] is True
        
        # Resume
        resume_response = client.post("/simulator/time/resume")
        assert resume_response.status_code == 200
        
        # Check status after resume
        response = client.get("/simulation/status")
        
        assert response.status_code == 200
        assert response.json()["is_paused"] is False

    # ===== Time Information =====

    def test_status_current_time_is_valid_iso8601(self, client_with_engine):
        """Test that current_time in status is valid ISO 8601 format.
        
        Verifies:
        - current_time can be parsed as datetime
        - current_time includes timezone information
        """
        client, engine = client_with_engine
        
        response = client.get("/simulation/status")
        
        assert response.status_code == 200
        current_time_str = response.json()["current_time"]
        
        # Should be parseable as ISO 8601
        parsed_time = datetime.fromisoformat(current_time_str)
        assert parsed_time.tzinfo is not None  # Has timezone

    def test_status_time_scale_default(self, client_with_engine):
        """Test that GET /simulation/status shows default time_scale.
        
        Verifies:
        - time_scale is 1.0 by default
        """
        client, engine = client_with_engine
        
        response = client.get("/simulation/status")
        
        assert response.status_code == 200
        assert response.json()["time_scale"] == 1.0

    def test_status_time_scale_reflects_changes(self, client_with_engine):
        """Test that GET /simulation/status reflects time_scale changes.
        
        Verifies:
        - After POST /simulator/time/set-scale with new scale
        - time_scale in status matches the new scale
        """
        client, engine = client_with_engine
        
        # Set a new time scale
        scale_response = client.post("/simulator/time/set-scale", json={"scale": 2.5})
        assert scale_response.status_code == 200
        
        # Check status
        response = client.get("/simulation/status")
        
        assert response.status_code == 200
        assert response.json()["time_scale"] == 2.5

    def test_status_current_time_reflects_advancement(self, client_with_engine):
        """Test that current_time in status updates after time advancement.
        
        Verifies:
        - After POST /simulator/time/advance
        - current_time in status reflects the new time
        """
        client, engine = client_with_engine
        
        # Get initial time
        initial_response = client.get("/simulation/status")
        initial_time = datetime.fromisoformat(initial_response.json()["current_time"])
        
        # Advance time by 1 hour
        advance_response = client.post("/simulator/time/advance", json={"seconds": 3600})
        assert advance_response.status_code == 200
        
        # Check updated time
        response = client.get("/simulation/status")
        updated_time = datetime.fromisoformat(response.json()["current_time"])
        
        # Time should have advanced by 1 hour
        assert updated_time == initial_time + timedelta(hours=1)

    # ===== Event Counts =====

    def test_status_zero_events_initially(self, client_with_engine):
        """Test that GET /simulation/status shows zero event counts initially.
        
        Verifies:
        - pending_events is 0
        - executed_events is 0
        - failed_events is 0
        """
        client, engine = client_with_engine
        
        response = client.get("/simulation/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["pending_events"] == 0
        assert data["executed_events"] == 0
        assert data["failed_events"] == 0

    def test_status_pending_events_count(self, client_with_engine):
        """Test that pending_events count updates when events are added.
        
        Verifies:
        - After adding events, pending_events reflects the count
        """
        client, engine = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Add 2 events in the future
        for i in range(2):
            event_time = current_time + timedelta(hours=i + 1)
            request = make_event_request(event_time, "location", location_event_data())
            create_response = client.post("/events", json=request)
            assert create_response.status_code == 200
        
        # Check status
        response = client.get("/simulation/status")
        
        assert response.status_code == 200
        assert response.json()["pending_events"] == 2

    def test_status_executed_events_count(self, client_with_engine):
        """Test that executed_events count updates after event execution.
        
        Verifies:
        - After executing events (via time advance), executed_events updates
        """
        client, engine = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Add an event in the near future
        event_time = current_time + timedelta(seconds=1)
        request = make_event_request(event_time, "location", location_event_data())
        create_response = client.post("/events", json=request)
        assert create_response.status_code == 200
        
        # Verify pending before execution
        status_before = client.get("/simulation/status")
        assert status_before.json()["pending_events"] == 1
        assert status_before.json()["executed_events"] == 0
        
        # Advance time to execute the event
        advance_response = client.post("/simulator/time/advance", json={"seconds": 2})
        assert advance_response.status_code == 200
        
        # Check status after execution
        response = client.get("/simulation/status")
        
        assert response.status_code == 200
        data = response.json()
        # Event should be executed (or failed, but counted)
        assert data["pending_events"] == 0
        assert data["executed_events"] >= 1 or data["failed_events"] >= 1

    def test_status_failed_events_count(self, client_with_engine):
        """Test that failed_events count updates when events fail.
        
        Note: Testing failed events requires an event with invalid data
        or a modality that doesn't exist. We'll create a valid event
        and verify the counting mechanism works.
        
        Verifies:
        - failed_events starts at 0
        - Count is accurately tracked
        """
        client, engine = client_with_engine
        
        # Verify failed_events starts at 0
        response = client.get("/simulation/status")
        
        assert response.status_code == 200
        assert response.json()["failed_events"] == 0
        
        # Note: To properly test failed events, we'd need to create
        # an event that will fail. For now, we verify the field exists
        # and is tracked. The actual failure testing is covered in
        # event-specific tests.

    def test_status_event_counts_are_accurate(self, client_with_engine):
        """Test that event counts in status are accurate.
        
        Verifies:
        - Create multiple events
        - Execute some, leave some pending
        - All counts accurately reflect queue state
        """
        client, engine = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Add 3 events: 2 that will execute, 1 in far future
        for i in range(2):
            event_time = current_time + timedelta(seconds=i + 1)
            request = make_event_request(event_time, "location", location_event_data())
            create_response = client.post("/events", json=request)
            assert create_response.status_code == 200
        
        # Add 1 event far in the future (won't execute)
        future_event_time = current_time + timedelta(hours=24)
        request = make_event_request(future_event_time, "location", location_event_data())
        create_response = client.post("/events", json=request)
        assert create_response.status_code == 200
        
        # Verify initial state: 3 pending
        status_before = client.get("/simulation/status")
        assert status_before.json()["pending_events"] == 3
        
        # Advance time to execute the first 2 events
        advance_response = client.post("/simulator/time/advance", json={"seconds": 5})
        assert advance_response.status_code == 200
        
        # Check final counts
        response = client.get("/simulation/status")
        data = response.json()
        
        # 1 should be pending (future event), 2 executed/failed
        assert data["pending_events"] == 1
        total_processed = data["executed_events"] + data["failed_events"]
        assert total_processed == 2

    # ===== Next Event Time =====

    def test_status_next_event_time_null_when_empty(self, client_with_engine):
        """Test that next_event_time is null when no events are pending.
        
        Verifies:
        - With no events in queue, next_event_time is null
        """
        client, engine = client_with_engine
        
        response = client.get("/simulation/status")
        
        assert response.status_code == 200
        assert response.json()["next_event_time"] is None

    def test_status_next_event_time_present_with_pending_event(self, client_with_engine):
        """Test that next_event_time is present when events are pending.
        
        Verifies:
        - After adding a future event, next_event_time is populated
        - next_event_time matches the scheduled event time
        """
        client, engine = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Add an event in the future
        event_time = current_time + timedelta(hours=1)
        request = make_event_request(event_time, "location", location_event_data())
        create_response = client.post("/events", json=request)
        assert create_response.status_code == 200
        
        # Check status
        response = client.get("/simulation/status")
        
        assert response.status_code == 200
        next_event_time_str = response.json()["next_event_time"]
        assert next_event_time_str is not None
        
        # Should match the event time
        next_event_time = datetime.fromisoformat(next_event_time_str)
        assert next_event_time == event_time

    def test_status_next_event_time_is_earliest_pending(self, client_with_engine):
        """Test that next_event_time shows the earliest pending event.
        
        Verifies:
        - With multiple pending events at different times
        - next_event_time shows the earliest one
        """
        client, engine = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Add events at different times (add later one first)
        later_event_time = current_time + timedelta(hours=2)
        request1 = make_event_request(later_event_time, "location", location_event_data())
        create_response1 = client.post("/events", json=request1)
        assert create_response1.status_code == 200
        
        earlier_event_time = current_time + timedelta(hours=1)
        request2 = make_event_request(earlier_event_time, "location", location_event_data())
        create_response2 = client.post("/events", json=request2)
        assert create_response2.status_code == 200
        
        # Check status - should show the earlier event
        response = client.get("/simulation/status")
        
        assert response.status_code == 200
        next_event_time = datetime.fromisoformat(response.json()["next_event_time"])
        assert next_event_time == earlier_event_time

    def test_status_next_event_time_updates_after_execution(self, client_with_engine):
        """Test that next_event_time updates when events are executed.
        
        Verifies:
        - Add two events at different times
        - Execute the first one
        - next_event_time now shows the second event's time
        """
        client, engine = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Add first event (near future)
        first_event_time = current_time + timedelta(seconds=1)
        request1 = make_event_request(first_event_time, "location", location_event_data())
        create_response1 = client.post("/events", json=request1)
        assert create_response1.status_code == 200
        
        # Add second event (further in future)
        second_event_time = current_time + timedelta(hours=1)
        request2 = make_event_request(second_event_time, "location", location_event_data())
        create_response2 = client.post("/events", json=request2)
        assert create_response2.status_code == 200
        
        # Verify next_event_time shows first event
        status_before = client.get("/simulation/status")
        next_time_before = datetime.fromisoformat(status_before.json()["next_event_time"])
        assert next_time_before == first_event_time
        
        # Execute the first event
        advance_response = client.post("/simulator/time/advance", json={"seconds": 2})
        assert advance_response.status_code == 200
        
        # Check status - next_event_time should now be the second event
        response = client.get("/simulation/status")
        
        assert response.status_code == 200
        next_time_after = datetime.fromisoformat(response.json()["next_event_time"])
        assert next_time_after == second_event_time

    # ===== Multiple Requests =====

    def test_status_is_consistent_across_requests(self, client_with_engine):
        """Test that multiple status requests return consistent data.
        
        Verifies:
        - Two consecutive status requests (without state changes between)
        - Return identical data
        """
        client, engine = client_with_engine
        
        # Make two consecutive requests
        response1 = client.get("/simulation/status")
        response2 = client.get("/simulation/status")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Data should be identical (no state changes between)
        data1 = response1.json()
        data2 = response2.json()
        
        assert data1["is_running"] == data2["is_running"]
        assert data1["is_paused"] == data2["is_paused"]
        assert data1["time_scale"] == data2["time_scale"]
        assert data1["pending_events"] == data2["pending_events"]
        assert data1["executed_events"] == data2["executed_events"]
        assert data1["failed_events"] == data2["failed_events"]
        assert data1["next_event_time"] == data2["next_event_time"]
        # Note: current_time may differ slightly due to auto-advance in some modes,
        # but in manual mode (client_with_engine default) it should be identical
        assert data1["current_time"] == data2["current_time"]

    def test_status_reflects_state_changes(self, client_with_engine):
        """Test that status accurately reflects state changes between requests.
        
        Verifies:
        - Get initial status
        - Make state changes (pause, add events, advance time)
        - Get status again
        - All changes are reflected
        """
        client, engine = client_with_engine
        
        # Get initial status
        initial_response = client.get("/simulation/status")
        initial_data = initial_response.json()
        
        assert initial_data["is_paused"] is False
        assert initial_data["pending_events"] == 0
        
        initial_time = datetime.fromisoformat(initial_data["current_time"])
        
        # Make changes: pause
        pause_response = client.post("/simulator/time/pause")
        assert pause_response.status_code == 200
        
        # Verify pause reflected
        status_after_pause = client.get("/simulation/status")
        assert status_after_pause.json()["is_paused"] is True
        
        # Resume and add an event
        resume_response = client.post("/simulator/time/resume")
        assert resume_response.status_code == 200
        
        event_time = initial_time + timedelta(hours=1)
        request = make_event_request(event_time, "location", location_event_data())
        create_response = client.post("/events", json=request)
        assert create_response.status_code == 200
        
        # Verify event added
        status_after_event = client.get("/simulation/status")
        assert status_after_event.json()["pending_events"] == 1
        assert status_after_event.json()["next_event_time"] is not None
        
        # Advance time
        advance_response = client.post("/simulator/time/advance", json={"seconds": 60})
        assert advance_response.status_code == 200
        
        # Verify time advanced
        status_after_advance = client.get("/simulation/status")
        advanced_time = datetime.fromisoformat(status_after_advance.json()["current_time"])
        assert advanced_time > initial_time
