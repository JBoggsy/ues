"""Integration tests for POST /simulator/time/advance endpoint.

Tests verify that the time advance endpoint correctly moves simulation time
forward by a specified duration and executes events in that time window.
"""

from datetime import datetime, timedelta

import pytest

from tests.api.helpers import (
    make_event_request,
    location_event_data,
    email_event_data,
    sms_event_data,
)


class TestPostTimeAdvance:
    """Tests for POST /simulator/time/advance endpoint."""
    
    def test_advance_moves_time_forward(self, client_with_engine):
        """Test that POST /simulator/time/advance advances simulation time."""
        client, _ = client_with_engine
        
        # Get initial time
        initial_response = client.get("/simulator/time")
        initial_time = datetime.fromisoformat(initial_response.json()["current_time"])
        
        # Advance by 1 hour
        response = client.post(
            "/simulator/time/advance",
            json={"seconds": 3600}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Verify time advanced by exactly 1 hour
        new_time = datetime.fromisoformat(data["current_time"])
        time_diff = new_time - initial_time
        assert abs(time_diff.total_seconds() - 3600) < 1
    
    def test_advance_with_zero_duration_rejected(self, client_with_engine):
        """Test that POST /simulator/time/advance rejects zero duration."""
        client, _ = client_with_engine
        
        # Try to advance by 0 seconds
        response = client.post(
            "/simulator/time/advance",
            json={"seconds": 0}
        )
        
        # Should reject with validation error (422 from Pydantic or 400 from business logic)
        assert response.status_code in [400, 422]
        assert "detail" in response.json()
    
    def test_advance_with_negative_duration_rejected(self, client_with_engine):
        """Test that POST /simulator/time/advance rejects negative duration."""
        client, _ = client_with_engine
        
        # Try to advance by negative seconds
        response = client.post(
            "/simulator/time/advance",
            json={"seconds": -100}
        )
        
        # Should reject with validation error
        assert response.status_code in [400, 422]
        assert "detail" in response.json()
    
    def test_advance_executes_events_in_window(self, client_with_engine):
        """Test that POST /simulator/time/advance executes events in the time window."""
        client, _ = client_with_engine
        
        # Get initial time
        initial_response = client.get("/simulator/time")
        initial_time = datetime.fromisoformat(initial_response.json()["current_time"])
        
        # Create events at different times within next hour
        event_time_1 = initial_time + timedelta(minutes=10)
        event_time_2 = initial_time + timedelta(minutes=30)
        event_time_3 = initial_time + timedelta(minutes=50)
        
        event1_request = make_event_request(
            event_time_1,
            "location",
            location_event_data(latitude=37.7749, longitude=-122.4194),
        )
        event2_request = make_event_request(
            event_time_2,
            "email",
            email_event_data(subject="Test Email"),
        )
        event3_request = make_event_request(
            event_time_3,
            "sms",
            sms_event_data(body="Test SMS"),
        )
        
        # Create the events
        response1 = client.post("/events", json=event1_request)
        response2 = client.post("/events", json=event2_request)
        response3 = client.post("/events", json=event3_request)
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 200
        
        event1_id = response1.json()["event_id"]
        event2_id = response2.json()["event_id"]
        event3_id = response3.json()["event_id"]
        
        # Advance by 1 hour (covers all 3 events)
        advance_response = client.post(
            "/simulator/time/advance",
            json={"seconds": 3600}
        )
        
        assert advance_response.status_code == 200
        
        # Verify all 3 events were executed
        event1_check = client.get(f"/events/{event1_id}")
        event2_check = client.get(f"/events/{event2_id}")
        event3_check = client.get(f"/events/{event3_id}")
        
        # Events should be executed or failed (not pending)
        assert event1_check.json()["status"] in ["executed", "failed"]
        assert event2_check.json()["status"] in ["executed", "failed"]
        assert event3_check.json()["status"] in ["executed", "failed"]
    
    def test_advance_does_not_execute_future_events(self, client_with_engine):
        """Test that POST /simulator/time/advance doesn't execute events beyond the window."""
        client, _ = client_with_engine
        
        # Get initial time
        initial_response = client.get("/simulator/time")
        initial_time = datetime.fromisoformat(initial_response.json()["current_time"])
        
        # Create event 2 hours in the future
        future_event_time = initial_time + timedelta(hours=2)
        event_request = make_event_request(
            future_event_time,
            "location",
            location_event_data(latitude=40.7128, longitude=-74.0060),
        )
        
        create_response = client.post("/events", json=event_request)
        assert create_response.status_code == 200
        event_id = create_response.json()["event_id"]
        
        # Advance by only 1 hour (not enough to reach event)
        advance_response = client.post(
            "/simulator/time/advance",
            json={"seconds": 3600}
        )
        
        assert advance_response.status_code == 200
        
        # Verify event is still pending
        event_check = client.get(f"/events/{event_id}")
        assert event_check.json()["status"] == "pending"
    
    def test_advance_with_large_duration(self, client_with_engine):
        """Test that POST /simulator/time/advance works with large durations."""
        client, _ = client_with_engine
        
        # Get initial time
        initial_response = client.get("/simulator/time")
        initial_time = datetime.fromisoformat(initial_response.json()["current_time"])
        
        # Advance by 1 week (604800 seconds)
        response = client.post(
            "/simulator/time/advance",
            json={"seconds": 604800}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify time advanced by 1 week
        new_time = datetime.fromisoformat(data["current_time"])
        time_diff = new_time - initial_time
        assert abs(time_diff.total_seconds() - 604800) < 1
    
    def test_advance_multiple_times_sequential(self, client_with_engine):
        """Test that POST /simulator/time/advance can be called multiple times."""
        client, _ = client_with_engine
        
        # Get initial time
        initial_response = client.get("/simulator/time")
        initial_time = datetime.fromisoformat(initial_response.json()["current_time"])
        
        # Advance 3 times by 10 minutes each
        for _ in range(3):
            response = client.post(
                "/simulator/time/advance",
                json={"seconds": 600}
            )
            assert response.status_code == 200
        
        # Get final time
        final_response = client.get("/simulator/time")
        final_time = datetime.fromisoformat(final_response.json()["current_time"])
        
        # Verify total advancement is 30 minutes
        time_diff = final_time - initial_time
        assert abs(time_diff.total_seconds() - 1800) < 1
    
    def test_advance_when_paused_fails(self, client_with_engine):
        """Test that POST /simulator/time/advance fails when simulation is paused."""
        client, _ = client_with_engine
        
        # Pause the simulation
        pause_response = client.post("/simulator/time/pause")
        assert pause_response.status_code == 200
        
        # Try to advance time while paused
        response = client.post(
            "/simulator/time/advance",
            json={"seconds": 100}
        )
        
        # Should fail with 400 error
        assert response.status_code == 400
        assert "paused" in response.json()["detail"].lower()
    
    def test_advance_with_fractional_seconds(self, client_with_engine):
        """Test that POST /simulator/time/advance accepts fractional seconds."""
        client, _ = client_with_engine
        
        # Get initial time
        initial_response = client.get("/simulator/time")
        initial_time = datetime.fromisoformat(initial_response.json()["current_time"])
        
        # Advance by 1.5 seconds
        response = client.post(
            "/simulator/time/advance",
            json={"seconds": 1.5}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify time advanced by 1.5 seconds
        new_time = datetime.fromisoformat(data["current_time"])
        time_diff = new_time - initial_time
        assert abs(time_diff.total_seconds() - 1.5) < 0.1
    
    def test_advance_returns_consistent_time_state(self, client_with_engine):
        """Test that POST /simulator/time/advance returns consistent time state."""
        client, _ = client_with_engine
        
        # Advance time
        advance_response = client.post(
            "/simulator/time/advance",
            json={"seconds": 500}
        )
        
        assert advance_response.status_code == 200
        advance_data = advance_response.json()
        
        # Get time state separately
        state_response = client.get("/simulator/time")
        state_data = state_response.json()
        
        # Both should report the same current_time
        assert advance_data["current_time"] == state_data["current_time"]
        
        # Verify all expected fields present
        assert "current_time" in advance_data
        assert "time_scale" in advance_data
        assert "is_paused" in advance_data
        assert "auto_advance" in advance_data
