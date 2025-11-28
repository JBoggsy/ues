"""Integration tests for pause/resume time control endpoints.

Tests verify:
- POST /simulator/time/pause - Pause simulation
- POST /simulator/time/resume - Resume simulation
"""

from datetime import datetime, timedelta

import pytest

from tests.api.helpers import (
    make_event_request,
    location_event_data,
)


class TestPostTimePause:
    """Tests for POST /simulator/time/pause endpoint."""
    
    def test_pause_stops_time_advancement(self, client_with_engine):
        """Test that POST /simulator/time/pause pauses the simulation."""
        client, _ = client_with_engine
        
        # Pause the simulation
        response = client.post("/simulator/time/pause")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["is_paused"] is True
        
        # Verify state reflects paused
        state_response = client.get("/simulator/time")
        assert state_response.json()["is_paused"] is True
    
    def test_pause_is_idempotent(self, client_with_engine):
        """Test that POST /simulator/time/pause can be called multiple times safely."""
        client, _ = client_with_engine
        
        # Pause once
        response1 = client.post("/simulator/time/pause")
        assert response1.status_code == 200
        assert response1.json()["is_paused"] is True
        
        # Pause again (should succeed, not error)
        response2 = client.post("/simulator/time/pause")
        assert response2.status_code == 200
        assert response2.json()["is_paused"] is True
        
        # Verify still paused
        state_response = client.get("/simulator/time")
        assert state_response.json()["is_paused"] is True
    
    def test_pause_prevents_time_advance(self, client_with_engine):
        """Test that POST /simulator/time/pause prevents time advancement."""
        client, _ = client_with_engine
        
        # Pause the simulation
        pause_response = client.post("/simulator/time/pause")
        assert pause_response.status_code == 200
        
        # Try to advance time
        advance_response = client.post(
            "/simulator/time/advance",
            json={"seconds": 100}
        )
        
        # Should fail because simulation is paused
        assert advance_response.status_code == 400
        assert "paused" in advance_response.json()["detail"].lower()
    
    def test_pause_does_not_change_current_time(self, client_with_engine):
        """Test that POST /simulator/time/pause doesn't change current time."""
        client, _ = client_with_engine
        
        # Get time before pause
        before_response = client.get("/simulator/time")
        before_time = datetime.fromisoformat(before_response.json()["current_time"])
        
        # Pause
        pause_response = client.post("/simulator/time/pause")
        assert pause_response.status_code == 200
        
        # Get time after pause
        after_response = client.get("/simulator/time")
        after_time = datetime.fromisoformat(after_response.json()["current_time"])
        
        # Time should be unchanged
        assert before_time == after_time
    
    def test_pause_with_pending_events(self, client_with_engine):
        """Test that POST /simulator/time/pause works with pending events in queue."""
        client, _ = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create a future event
        event_time = current_time + timedelta(hours=1)
        event_request = make_event_request(
            event_time,
            "location",
            location_event_data(latitude=40.7128, longitude=-74.0060),
        )
        
        create_response = client.post("/events", json=event_request)
        assert create_response.status_code == 200
        event_id = create_response.json()["event_id"]
        
        # Pause simulation
        pause_response = client.post("/simulator/time/pause")
        assert pause_response.status_code == 200
        
        # Verify event is still pending (not executed)
        event_check = client.get(f"/events/{event_id}")
        assert event_check.json()["status"] == "pending"


class TestPostTimeResume:
    """Tests for POST /simulator/time/resume endpoint."""
    
    def test_resume_restarts_time_advancement(self, client_with_engine):
        """Test that POST /simulator/time/resume resumes a paused simulation."""
        client, _ = client_with_engine
        
        # Pause first
        client.post("/simulator/time/pause")
        
        # Resume the simulation
        response = client.post("/simulator/time/resume")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["is_paused"] is False
        
        # Verify state reflects resumed
        state_response = client.get("/simulator/time")
        assert state_response.json()["is_paused"] is False
    
    def test_resume_is_idempotent(self, client_with_engine):
        """Test that POST /simulator/time/resume can be called multiple times safely."""
        client, _ = client_with_engine
        
        # Start unpaused (default state)
        state_response = client.get("/simulator/time")
        assert state_response.json()["is_paused"] is False
        
        # Resume when already running (should succeed, not error)
        response1 = client.post("/simulator/time/resume")
        assert response1.status_code == 200
        assert response1.json()["is_paused"] is False
        
        # Resume again
        response2 = client.post("/simulator/time/resume")
        assert response2.status_code == 200
        assert response2.json()["is_paused"] is False
    
    def test_resume_allows_time_advance(self, client_with_engine):
        """Test that POST /simulator/time/resume allows time advancement again."""
        client, _ = client_with_engine
        
        # Pause simulation
        client.post("/simulator/time/pause")
        
        # Verify advance fails while paused
        advance_fail = client.post("/simulator/time/advance", json={"seconds": 50})
        assert advance_fail.status_code == 400
        
        # Resume
        resume_response = client.post("/simulator/time/resume")
        assert resume_response.status_code == 200
        
        # Now advance should work
        advance_success = client.post("/simulator/time/advance", json={"seconds": 50})
        assert advance_success.status_code == 200
    
    def test_resume_does_not_change_current_time(self, client_with_engine):
        """Test that POST /simulator/time/resume doesn't change current time."""
        client, _ = client_with_engine
        
        # Pause
        client.post("/simulator/time/pause")
        
        # Get time before resume
        before_response = client.get("/simulator/time")
        before_time = datetime.fromisoformat(before_response.json()["current_time"])
        
        # Resume
        resume_response = client.post("/simulator/time/resume")
        assert resume_response.status_code == 200
        
        # Get time after resume
        after_response = client.get("/simulator/time")
        after_time = datetime.fromisoformat(after_response.json()["current_time"])
        
        # Time should be unchanged
        assert before_time == after_time
    
    def test_pause_resume_cycle(self, client_with_engine):
        """Test that pause/resume cycle works correctly."""
        client, _ = client_with_engine
        
        # Get initial time
        initial_response = client.get("/simulator/time")
        initial_time = datetime.fromisoformat(initial_response.json()["current_time"])
        
        # Advance 100 seconds
        client.post("/simulator/time/advance", json={"seconds": 100})
        
        # Pause
        pause_response = client.post("/simulator/time/pause")
        assert pause_response.status_code == 200
        
        # Get time while paused
        paused_response = client.get("/simulator/time")
        paused_time = datetime.fromisoformat(paused_response.json()["current_time"])
        assert paused_time > initial_time
        
        # Resume
        resume_response = client.post("/simulator/time/resume")
        assert resume_response.status_code == 200
        
        # Advance another 100 seconds
        advance2_response = client.post("/simulator/time/advance", json={"seconds": 100})
        assert advance2_response.status_code == 200
        
        # Verify total advancement is 200 seconds
        final_response = client.get("/simulator/time")
        final_time = datetime.fromisoformat(final_response.json()["current_time"])
        total_diff = final_time - initial_time
        assert abs(total_diff.total_seconds() - 200) < 1
