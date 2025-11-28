"""Integration tests for time navigation endpoints.

Tests verify:
- POST /simulator/time/set - Jump to specific time
- POST /simulator/time/skip-to-next - Skip to next event
"""

from datetime import datetime, timedelta

import pytest

from tests.api.helpers import (
    make_event_request,
    location_event_data,
    email_event_data,
    sms_event_data,
)


class TestPostTimeSet:
    """Tests for POST /simulator/time/set endpoint."""
    
    def test_set_jumps_to_specific_time(self, client_with_engine):
        """Test that POST /simulator/time/set moves to specified time."""
        client, _ = client_with_engine
        
        # Get initial time
        initial_response = client.get("/simulator/time")
        initial_time = datetime.fromisoformat(initial_response.json()["current_time"])
        
        # Set time to 2 hours in the future
        target_time = initial_time + timedelta(hours=2)
        response = client.post(
            "/simulator/time/set",
            json={"target_time": target_time.isoformat()}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Verify time set correctly
        assert "current_time" in data
        assert "previous_time" in data
        current_time = datetime.fromisoformat(data["current_time"])
        previous_time = datetime.fromisoformat(data["previous_time"])
        
        assert abs((current_time - target_time).total_seconds()) < 1
        assert abs((previous_time - initial_time).total_seconds()) < 1
    
    def test_set_rejects_past_time(self, client_with_engine):
        """Test that POST /simulator/time/set rejects attempts to go backwards."""
        client, _ = client_with_engine
        
        # Get initial time
        initial_response = client.get("/simulator/time")
        initial_time = datetime.fromisoformat(initial_response.json()["current_time"])
        
        # Try to set time to 1 hour in the past
        past_time = initial_time - timedelta(hours=1)
        response = client.post(
            "/simulator/time/set",
            json={"target_time": past_time.isoformat()}
        )
        
        # Should reject with 400 error
        assert response.status_code == 400
        assert "backwards" in response.json()["detail"].lower()
    
    def test_set_marks_events_as_skipped(self, client_with_engine):
        """Test that POST /simulator/time/set marks skipped events appropriately."""
        client, _ = client_with_engine
        
        # Get initial time
        initial_response = client.get("/simulator/time")
        initial_time = datetime.fromisoformat(initial_response.json()["current_time"])
        
        # Create events at different times in the jump window
        event_time_1 = initial_time + timedelta(minutes=30)
        event_time_2 = initial_time + timedelta(hours=1)
        
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
        
        response1 = client.post("/events", json=event1_request)
        response2 = client.post("/events", json=event2_request)
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        event1_id = response1.json()["event_id"]
        event2_id = response2.json()["event_id"]
        
        # Jump past both events
        target_time = initial_time + timedelta(hours=2)
        set_response = client.post(
            "/simulator/time/set",
            json={"target_time": target_time.isoformat()}
        )
        
        assert set_response.status_code == 200
        data = set_response.json()
        
        # Verify response shows skipped events
        assert data["skipped_events"] == 2
        assert data["executed_events"] == 0
        
        # Verify events are marked as skipped
        event1_check = client.get(f"/events/{event1_id}")
        event2_check = client.get(f"/events/{event2_id}")
        
        assert event1_check.json()["status"] == "skipped"
        assert event2_check.json()["status"] == "skipped"
    
    def test_set_does_not_skip_future_events(self, client_with_engine):
        """Test that POST /simulator/time/set doesn't affect events after target time."""
        client, _ = client_with_engine
        
        # Get initial time
        initial_response = client.get("/simulator/time")
        initial_time = datetime.fromisoformat(initial_response.json()["current_time"])
        
        # Create event beyond jump target
        future_event_time = initial_time + timedelta(hours=3)
        event_request = make_event_request(
            future_event_time,
            "location",
            location_event_data(latitude=40.7128, longitude=-74.0060),
        )
        
        create_response = client.post("/events", json=event_request)
        assert create_response.status_code == 200
        event_id = create_response.json()["event_id"]
        
        # Jump to 2 hours (before the event)
        target_time = initial_time + timedelta(hours=2)
        set_response = client.post(
            "/simulator/time/set",
            json={"target_time": target_time.isoformat()}
        )
        
        assert set_response.status_code == 200
        assert set_response.json()["skipped_events"] == 0
        
        # Verify event is still pending
        event_check = client.get(f"/events/{event_id}")
        assert event_check.json()["status"] == "pending"
    
    def test_set_with_same_time_is_noop(self, client_with_engine):
        """Test that POST /simulator/time/set to current time is harmless."""
        client, _ = client_with_engine
        
        # Get current time
        initial_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(initial_response.json()["current_time"])
        
        # Set to same time
        response = client.post(
            "/simulator/time/set",
            json={"target_time": current_time.isoformat()}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should show no events skipped
        assert data["skipped_events"] == 0
        assert data["executed_events"] == 0
    
    def test_set_validates_time_format(self, client_with_engine):
        """Test that POST /simulator/time/set rejects invalid time formats."""
        client, _ = client_with_engine
        
        # Try various invalid time formats
        invalid_formats = [
            "not-a-date",
            "2024-13-01T00:00:00Z",  # Invalid month
            "2024-01-32T00:00:00Z",  # Invalid day
            "2024-01-01T25:00:00Z",  # Invalid hour
            "",  # Empty string
            "yesterday",  # Natural language
            "true",  # Boolean string
        ]
        
        for invalid_time in invalid_formats:
            response = client.post(
                "/simulator/time/set",
                json={"target_time": invalid_time}
            )
            
            # Should reject with 422 validation error
            assert response.status_code == 422, \
                f"Expected 422 for invalid time '{invalid_time}', got {response.status_code}: {response.json()}"
    
    def test_set_validates_missing_target_time(self, client_with_engine):
        """Test that POST /simulator/time/set requires target_time field."""
        client, _ = client_with_engine
        
        # Try request with missing target_time
        response = client.post("/simulator/time/set", json={})
        
        # Should reject with validation error
        assert response.status_code == 422
        assert "target_time" in response.json()["detail"][0]["loc"]
    
    def test_set_validates_null_target_time(self, client_with_engine):
        """Test that POST /simulator/time/set rejects null target_time."""
        client, _ = client_with_engine
        
        # Try request with null target_time
        response = client.post(
            "/simulator/time/set",
            json={"target_time": None}
        )
        
        # Should reject with validation error
        assert response.status_code == 422


class TestPostTimeSkipToNext:
    """Tests for POST /simulator/time/skip-to-next endpoint."""
    
    def test_skip_to_next_moves_to_next_event(self, client_with_engine):
        """Test that POST /simulator/time/skip-to-next jumps to next scheduled event."""
        client, _ = client_with_engine
        
        # Get initial time
        initial_response = client.get("/simulator/time")
        initial_time = datetime.fromisoformat(initial_response.json()["current_time"])
        
        # Create an event in the future
        event_time = initial_time + timedelta(hours=1)
        event_request = make_event_request(
            event_time,
            "location",
            location_event_data(latitude=37.7749, longitude=-122.4194),
        )
        create_response = client.post("/events", json=event_request)
        assert create_response.status_code == 200
        
        # Skip to next event
        response = client.post("/simulator/time/skip-to-next")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Verify time moved to event time
        assert "current_time" in data
        assert "events_executed" in data
        current_time = datetime.fromisoformat(data["current_time"])
        assert abs((current_time - event_time).total_seconds()) < 1
    
    def test_skip_to_next_when_no_events(self, client_with_engine):
        """Test that POST /simulator/time/skip-to-next returns 404 when queue is empty."""
        client, _ = client_with_engine
        
        # Queue should be empty (no events created)
        response = client.post("/simulator/time/skip-to-next")
        
        # Should return 404
        assert response.status_code == 404
        assert "no pending events" in response.json()["detail"].lower()
    
    def test_skip_to_next_executes_events(self, client_with_engine):
        """Test that POST /simulator/time/skip-to-next executes events at target time."""
        client, _ = client_with_engine
        
        # Get initial time
        initial_response = client.get("/simulator/time")
        initial_time = datetime.fromisoformat(initial_response.json()["current_time"])
        
        # Create event
        event_time = initial_time + timedelta(minutes=30)
        event_request = make_event_request(
            event_time,
            "location",
            location_event_data(latitude=37.7749, longitude=-122.4194),
        )
        create_response = client.post("/events", json=event_request)
        assert create_response.status_code == 200
        event_id = create_response.json()["event_id"]
        
        # Skip to next event
        skip_response = client.post("/simulator/time/skip-to-next")
        assert skip_response.status_code == 200
        
        # Verify events_executed count
        assert skip_response.json()["events_executed"] >= 1
        
        # Verify event was executed (or at least attempted)
        event_check = client.get(f"/events/{event_id}")
        assert event_check.json()["status"] in ["executed", "failed"]
    
    def test_skip_to_next_multiple_times(self, client_with_engine):
        """Test that POST /simulator/time/skip-to-next works for consecutive skips."""
        client, _ = client_with_engine
        
        # Get initial time
        initial_response = client.get("/simulator/time")
        initial_time = datetime.fromisoformat(initial_response.json()["current_time"])
        
        # Create 3 events at different times
        event_times = [
            initial_time + timedelta(hours=1),
            initial_time + timedelta(hours=2),
            initial_time + timedelta(hours=3),
        ]
        
        for event_time in event_times:
            event_request = make_event_request(
                event_time,
                "location",
                location_event_data(latitude=37.7749, longitude=-122.4194),
            )
            response = client.post("/events", json=event_request)
            assert response.status_code == 200
        
        # Skip 3 times
        for i, expected_time in enumerate(event_times):
            skip_response = client.post("/simulator/time/skip-to-next")
            assert skip_response.status_code == 200
            
            # Verify we're at the expected time
            current_time = datetime.fromisoformat(skip_response.json()["current_time"])
            assert abs((current_time - expected_time).total_seconds()) < 1
        
        # Fourth skip should fail (no more events)
        final_skip = client.post("/simulator/time/skip-to-next")
        assert final_skip.status_code == 404
    
    def test_skip_to_next_with_multiple_events_at_same_time(self, client_with_engine):
        """Test that POST /simulator/time/skip-to-next executes all events at target time."""
        client, _ = client_with_engine
        
        # Get initial time
        initial_response = client.get("/simulator/time")
        initial_time = datetime.fromisoformat(initial_response.json()["current_time"])
        
        # Create 3 events at the same time
        event_time = initial_time + timedelta(hours=1)
        event_ids = []
        
        for modality, data_func in [
            ("location", lambda: location_event_data(latitude=37.7749, longitude=-122.4194)),
            ("email", lambda: email_event_data(subject="Test")),
            ("sms", lambda: sms_event_data(body="Test SMS")),
        ]:
            event_request = make_event_request(event_time, modality, data_func())
            response = client.post("/events", json=event_request)
            assert response.status_code == 200
            event_ids.append(response.json()["event_id"])
        
        # Skip to next event
        skip_response = client.post("/simulator/time/skip-to-next")
        assert skip_response.status_code == 200
        
        # Verify all 3 events were executed
        assert skip_response.json()["events_executed"] == 3
        
        # Verify each event status
        for event_id in event_ids:
            event_check = client.get(f"/events/{event_id}")
            assert event_check.json()["status"] in ["executed", "failed"]
    
    def test_skip_to_next_returns_next_event_info(self, client_with_engine):
        """Test that POST /simulator/time/skip-to-next returns info about remaining events."""
        client, _ = client_with_engine
        
        # Get initial time
        initial_response = client.get("/simulator/time")
        initial_time = datetime.fromisoformat(initial_response.json()["current_time"])
        
        # Create 2 events
        event_time_1 = initial_time + timedelta(hours=1)
        event_time_2 = initial_time + timedelta(hours=2)
        
        for event_time in [event_time_1, event_time_2]:
            event_request = make_event_request(
                event_time,
                "location",
                location_event_data(latitude=37.7749, longitude=-122.4194),
            )
            response = client.post("/events", json=event_request)
            assert response.status_code == 200
        
        # Skip to first event
        skip_response = client.post("/simulator/time/skip-to-next")
        assert skip_response.status_code == 200
        data = skip_response.json()
        
        # Should indicate there's another event
        assert "next_event_time" in data
        assert data["next_event_time"] is not None
        next_time = datetime.fromisoformat(data["next_event_time"])
        assert abs((next_time - event_time_2).total_seconds()) < 1
        
        # Skip to second event
        skip_response2 = client.post("/simulator/time/skip-to-next")
        assert skip_response2.status_code == 200
        
        # Should indicate no more events
        assert skip_response2.json()["next_event_time"] is None
