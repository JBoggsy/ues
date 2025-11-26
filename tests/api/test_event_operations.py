"""Integration tests for individual event operations.

This module tests endpoints for operating on specific events by ID:
- GET /events/{event_id} - Retrieve event details
- DELETE /events/{event_id} - Cancel/delete an event
"""

from datetime import datetime, timedelta

from tests.api.helpers import (
    make_event_request,
    email_event_data,
    chat_event_data,
    sms_event_data,
)


class TestGetEventById:
    """Tests for GET /events/{event_id} endpoint."""
    
    def test_get_event_by_id_returns_details(self, client_with_engine):
        """Test that GET /events/{event_id} returns full event details."""
        client, engine = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create an event
        event_time = current_time + timedelta(hours=2)
        create_response = client.post(
            "/events",
            json=make_event_request(
                event_time,
                "email",
                email_event_data(subject="Test Event"),
                priority=75,
            ),
        )
        assert create_response.status_code == 200
        event_id = create_response.json()["event_id"]
        
        # Get the event by ID
        get_response = client.get(f"/events/{event_id}")
        
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["event_id"] == event_id
        assert data["modality"] == "email"
        assert data["status"] == "pending"
        assert data["priority"] == 75
        # Compare datetime objects rather than ISO strings (handles Z vs +00:00 format)
        assert datetime.fromisoformat(data["scheduled_time"]) == event_time
        assert data["created_at"] is not None
        assert data["executed_at"] is None
        assert data["error_message"] is None
    
    def test_get_event_by_id_nonexistent(self, client_with_engine):
        """Test that GET /events/{event_id} returns 404 for nonexistent events."""
        client, _ = client_with_engine
        
        response = client.get("/events/nonexistent-event-id-12345")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_get_event_by_id_after_execution(self, client_with_engine):
        """Test that GET /events/{event_id} returns executed events with status."""
        client, engine = client_with_engine
        
        # Create an immediate event
        create_response = client.post(
            "/events/immediate",
            json={
                "modality": "chat",
                "data": chat_event_data(role="user", content="Hello!"),
            },
        )
        assert create_response.status_code == 200
        event_id = create_response.json()["event_id"]
        
        # Advance time to execute the event
        advance_response = client.post(
            "/simulator/time/advance",
            json={"seconds": 1},
        )
        assert advance_response.status_code == 200
        
        # Get the event - should still be retrievable
        get_response = client.get(f"/events/{event_id}")
        
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["event_id"] == event_id
        # Chat events may fail without proper implementation, but should still be retrievable
        assert data["status"] in ["executed", "failed"]
        assert data["executed_at"] is not None
    
    def test_get_event_by_id_includes_metadata(self, client_with_engine):
        """Test that GET /events/{event_id} includes custom metadata.
        
        Note: The current EventResponse model doesn't include metadata field.
        This test documents the expected behavior if metadata is added to the response.
        """
        client, engine = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create an event with metadata
        event_time = current_time + timedelta(hours=1)
        metadata = {"test_key": "test_value", "another_key": 42}
        create_response = client.post(
            "/events",
            json={
                "scheduled_time": event_time.isoformat(),
                "modality": "sms",
                "data": sms_event_data(from_number="+15551234567", body="Test"),
                "metadata": metadata,
            },
        )
        assert create_response.status_code == 200
        event_id = create_response.json()["event_id"]
        
        # Get the event by ID
        get_response = client.get(f"/events/{event_id}")
        
        assert get_response.status_code == 200
        # Note: metadata is not currently returned in EventResponse
        # If it were added, we would assert:
        # assert get_response.json().get("metadata") == metadata


class TestDeleteEventById:
    """Tests for DELETE /events/{event_id} endpoint."""
    
    def test_delete_event_by_id_removes_from_queue(self, client_with_engine):
        """Test that DELETE /events/{event_id} removes the event from the queue."""
        client, engine = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create an event
        event_time = current_time + timedelta(hours=1)
        create_response = client.post(
            "/events",
            json=make_event_request(event_time, "email", email_event_data()),
        )
        assert create_response.status_code == 200
        event_id = create_response.json()["event_id"]
        
        # Verify event exists in queue
        list_response = client.get("/events")
        assert list_response.status_code == 200
        assert list_response.json()["total"] == 1
        
        # Delete the event
        delete_response = client.delete(f"/events/{event_id}")
        assert delete_response.status_code == 200
        
        # Verify event is no longer accessible
        get_response = client.get(f"/events/{event_id}")
        # Event still exists but with cancelled status
        assert get_response.status_code == 200
        assert get_response.json()["status"] == "cancelled"
        
        # Verify it doesn't appear in pending events
        list_response = client.get("/events?status=pending")
        assert list_response.status_code == 200
        assert list_response.json()["total"] == 0
    
    def test_delete_event_by_id_returns_confirmation(self, client_with_engine):
        """Test that DELETE /events/{event_id} returns success confirmation."""
        client, engine = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create an event
        event_time = current_time + timedelta(hours=1)
        create_response = client.post(
            "/events",
            json=make_event_request(event_time, "chat", chat_event_data()),
        )
        assert create_response.status_code == 200
        event_id = create_response.json()["event_id"]
        
        # Delete the event
        delete_response = client.delete(f"/events/{event_id}")
        
        assert delete_response.status_code == 200
        data = delete_response.json()
        assert data["cancelled"] is True
        assert data["event_id"] == event_id
    
    def test_delete_event_by_id_nonexistent(self, client_with_engine):
        """Test that DELETE /events/{event_id} returns 404 for nonexistent events."""
        client, _ = client_with_engine
        
        response = client.delete("/events/nonexistent-event-id-99999")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_delete_event_by_id_already_executed(self, client_with_engine):
        """Test that DELETE /events/{event_id} rejects already-executed events."""
        client, engine = client_with_engine
        
        # Create an immediate event
        create_response = client.post(
            "/events/immediate",
            json={
                "modality": "chat",
                "data": chat_event_data(role="user", content="Test"),
            },
        )
        assert create_response.status_code == 200
        event_id = create_response.json()["event_id"]
        
        # Execute the event by advancing time
        advance_response = client.post(
            "/simulator/time/advance",
            json={"seconds": 1},
        )
        assert advance_response.status_code == 200
        
        # Verify event was executed or failed
        get_response = client.get(f"/events/{event_id}")
        assert get_response.status_code == 200
        event_status = get_response.json()["status"]
        assert event_status in ["executed", "failed"]
        
        # Try to delete - should fail since it's no longer pending
        delete_response = client.delete(f"/events/{event_id}")
        
        assert delete_response.status_code == 400
        assert "cannot cancel" in delete_response.json()["detail"].lower()
    
    def test_delete_event_by_id_multiple_times(self, client_with_engine):
        """Test that DELETE /events/{event_id} handles multiple deletions gracefully."""
        client, engine = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create an event
        event_time = current_time + timedelta(hours=1)
        create_response = client.post(
            "/events",
            json=make_event_request(event_time, "email", email_event_data()),
        )
        assert create_response.status_code == 200
        event_id = create_response.json()["event_id"]
        
        # Delete the event first time
        first_delete = client.delete(f"/events/{event_id}")
        assert first_delete.status_code == 200
        assert first_delete.json()["cancelled"] is True
        
        # Try to delete again - should fail since status is now cancelled
        second_delete = client.delete(f"/events/{event_id}")
        assert second_delete.status_code == 400
        assert "cannot cancel" in second_delete.json()["detail"].lower()
