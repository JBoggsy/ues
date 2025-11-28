"""Integration tests for specialized event query endpoints.

This module tests endpoints for querying event queue state:
- GET /events/next - Peek at the next event to be executed
- GET /events/summary - Get queue statistics and counts
"""

from datetime import datetime, timedelta

from tests.api.helpers import (
    make_event_request,
    email_event_data,
    sms_event_data,
    chat_event_data,
    location_event_data,
)


class TestGetEventsNext:
    """Tests for GET /events/next endpoint."""
    
    def test_get_events_next_returns_earliest(self, client_with_engine):
        """Test that GET /events/next returns the earliest pending event."""
        client, _ = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create three events at different times
        event_time_1 = current_time + timedelta(hours=3)
        event_time_2 = current_time + timedelta(hours=1)  # Earliest
        event_time_3 = current_time + timedelta(hours=2)
        
        client.post("/events", json=make_event_request(event_time_1, "email", email_event_data()))
        create_response_2 = client.post("/events", json=make_event_request(event_time_2, "sms", sms_event_data()))
        client.post("/events", json=make_event_request(event_time_3, "chat", chat_event_data()))
        
        expected_event_id = create_response_2.json()["event_id"]
        
        # Get next event
        response = client.get("/events/next")
        
        assert response.status_code == 200
        data = response.json()
        assert data["event_id"] == expected_event_id
        assert data["modality"] == "sms"
        assert datetime.fromisoformat(data["scheduled_time"]) == event_time_2
    
    def test_get_events_next_empty_queue(self, client_with_engine):
        """Test that GET /events/next returns 404 when queue is empty."""
        client, _ = client_with_engine
        
        # Queue should be empty initially
        response = client.get("/events/next")
        
        assert response.status_code == 404
        assert "no pending events" in response.json()["detail"].lower()
    
    def test_get_events_next_skips_executed(self, client_with_engine):
        """Test that GET /events/next skips already-executed events.
        
        Note: This test may fail if event execution is broken/incomplete.
        """
        client, _ = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create an immediate event (will be executed first)
        client.post(
            "/events/immediate",
            json={"modality": "location", "data": location_event_data()},
        )
        
        # Create a future event
        future_time = current_time + timedelta(hours=2)
        future_response = client.post(
            "/events",
            json=make_event_request(future_time, "email", email_event_data()),
        )
        future_event_id = future_response.json()["event_id"]
        
        # Advance time to execute the immediate event
        client.post("/simulator/time/advance", json={"seconds": 1})
        
        # Get next event - should return the future one, not the executed one
        response = client.get("/events/next")
        
        assert response.status_code == 200
        assert response.json()["event_id"] == future_event_id
    
    def test_get_events_next_respects_priority(self, client_with_engine):
        """Test that GET /events/next considers priority for simultaneous events."""
        client, _ = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create three events at the same time with different priorities
        event_time = current_time + timedelta(hours=1)
        
        client.post(
            "/events",
            json={
                **make_event_request(event_time, "email", email_event_data()),
                "priority": 30,
            },
        )
        high_priority_response = client.post(
            "/events",
            json={
                **make_event_request(event_time, "sms", sms_event_data()),
                "priority": 90,  # Highest priority
            },
        )
        client.post(
            "/events",
            json={
                **make_event_request(event_time, "chat", chat_event_data()),
                "priority": 60,
            },
        )
        
        expected_event_id = high_priority_response.json()["event_id"]
        
        # Get next event - should return highest priority
        response = client.get("/events/next")
        
        assert response.status_code == 200
        assert response.json()["event_id"] == expected_event_id
        assert response.json()["priority"] == 90
    
    def test_get_events_next_does_not_modify_queue(self, client_with_engine):
        """Test that GET /events/next is read-only (doesn't remove event)."""
        client, _ = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create an event
        event_time = current_time + timedelta(hours=1)
        create_response = client.post(
            "/events",
            json=make_event_request(event_time, "email", email_event_data()),
        )
        event_id = create_response.json()["event_id"]
        
        # Call GET /events/next multiple times
        response_1 = client.get("/events/next")
        response_2 = client.get("/events/next")
        
        # Should return same event both times
        assert response_1.status_code == 200
        assert response_2.status_code == 200
        assert response_1.json()["event_id"] == event_id
        assert response_2.json()["event_id"] == event_id
        
        # Event should still be in the queue
        get_response = client.get(f"/events/{event_id}")
        assert get_response.status_code == 200
        assert get_response.json()["status"] == "pending"


class TestGetEventsSummary:
    """Tests for GET /events/summary endpoint."""
    
    def test_get_events_summary_empty_queue(self, client_with_engine):
        """Test that GET /events/summary returns zero counts for empty queue."""
        client, _ = client_with_engine
        
        response = client.get("/events/summary")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["pending"] == 0
        assert data["executed"] == 0
        assert data["failed"] == 0
        assert data["skipped"] == 0
        assert data["by_modality"] == {}
        assert data["next_event_time"] is None
    
    def test_get_events_summary_counts_by_status(self, client_with_engine):
        """Test that GET /events/summary correctly counts events by status.
        
        Note: This test may fail if event execution is broken/incomplete.
        """
        client, _ = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create pending events
        future_time_1 = current_time + timedelta(hours=1)
        future_time_2 = current_time + timedelta(hours=2)
        client.post("/events", json=make_event_request(future_time_1, "email", email_event_data()))
        client.post("/events", json=make_event_request(future_time_2, "sms", sms_event_data()))
        
        # Create immediate events that will be executed
        client.post("/events/immediate", json={"modality": "location", "data": location_event_data()})
        
        # Execute the immediate event
        client.post("/simulator/time/advance", json={"seconds": 1})
        
        # Get summary
        response = client.get("/events/summary")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["pending"] == 2
        # The immediate event may be executed or failed
        assert data["executed"] + data["failed"] == 1
    
    def test_get_events_summary_counts_by_modality(self, client_with_engine):
        """Test that GET /events/summary includes counts per modality."""
        client, _ = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create events for different modalities
        event_time = current_time + timedelta(hours=1)
        
        client.post("/events", json=make_event_request(event_time, "email", email_event_data()))
        client.post("/events", json=make_event_request(event_time + timedelta(minutes=1), "email", email_event_data()))
        client.post("/events", json=make_event_request(event_time + timedelta(minutes=2), "sms", sms_event_data()))
        client.post("/events", json=make_event_request(event_time + timedelta(minutes=3), "chat", chat_event_data()))
        client.post("/events", json=make_event_request(event_time + timedelta(minutes=4), "chat", chat_event_data()))
        client.post("/events", json=make_event_request(event_time + timedelta(minutes=5), "chat", chat_event_data()))
        
        # Get summary
        response = client.get("/events/summary")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 6
        assert data["by_modality"]["email"] == 2
        assert data["by_modality"]["sms"] == 1
        assert data["by_modality"]["chat"] == 3
    
    def test_get_events_summary_includes_next_event_time(self, client_with_engine):
        """Test that GET /events/summary includes next event time."""
        client, _ = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create events at different times
        earliest_time = current_time + timedelta(hours=1)
        later_time = current_time + timedelta(hours=3)
        
        client.post("/events", json=make_event_request(later_time, "email", email_event_data()))
        client.post("/events", json=make_event_request(earliest_time, "sms", sms_event_data()))
        
        # Get summary
        response = client.get("/events/summary")
        
        assert response.status_code == 200
        data = response.json()
        assert data["next_event_time"] is not None
        assert datetime.fromisoformat(data["next_event_time"]) == earliest_time
    
    def test_get_events_summary_after_execution(self, client_with_engine):
        """Test that GET /events/summary updates after events are executed.
        
        Note: This test may fail if event execution is broken/incomplete.
        """
        client, _ = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create events
        near_time = current_time + timedelta(seconds=30)
        far_time = current_time + timedelta(hours=2)
        
        client.post("/events", json=make_event_request(near_time, "location", location_event_data()))
        client.post("/events", json=make_event_request(far_time, "email", email_event_data()))
        
        # Initial summary - 2 pending
        response_1 = client.get("/events/summary")
        assert response_1.status_code == 200
        data_1 = response_1.json()
        assert data_1["total"] == 2
        assert data_1["pending"] == 2
        assert datetime.fromisoformat(data_1["next_event_time"]) == near_time
        
        # Advance time to execute first event
        client.post("/simulator/time/advance", json={"seconds": 60})
        
        # Updated summary - 1 pending, 1 executed or failed
        response_2 = client.get("/events/summary")
        assert response_2.status_code == 200
        data_2 = response_2.json()
        assert data_2["total"] == 2
        assert data_2["pending"] == 1
        assert data_2["executed"] + data_2["failed"] == 1
        # Next event time should now be the far_time event
        assert datetime.fromisoformat(data_2["next_event_time"]) == far_time
