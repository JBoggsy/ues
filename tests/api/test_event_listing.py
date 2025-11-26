"""Integration tests for event listing and filtering.

This module tests the GET /events endpoint, which allows clients to:
- List all events in the queue
- Filter events by status, modality, and time range
- Paginate results with limit and offset
- Combine multiple filters
"""

from datetime import datetime, timedelta

from tests.api.helpers import (
    make_event_request,
    email_event_data,
    sms_event_data,
    chat_event_data,
)


class TestGetEvents:
    """Tests for GET /events endpoint."""
    
    def test_get_events_empty_queue(self, client_with_engine):
        """Test that GET /events returns empty list when no events exist."""
        client, engine = client_with_engine
        
        # Query all events
        response = client.get("/events")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "events" in data
        assert "total" in data
        assert "pending" in data
        assert "executed" in data
        assert "failed" in data
        assert "skipped" in data
        
        # Verify counts
        assert data["events"] == []
        assert data["total"] == 0
        assert data["pending"] == 0
        assert data["executed"] == 0
        assert data["failed"] == 0
        assert data["skipped"] == 0
    
    def test_get_events_returns_created_event(self, client_with_engine):
        """Test that GET /events returns events that were created."""
        client, engine = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create an event
        event_time = current_time + timedelta(hours=1)
        create_response = client.post(
            "/events",
            json=make_event_request(
                event_time,
                "email",
                email_event_data(subject="Test Email", body_text="This is a test"),
            ),
        )
        assert create_response.status_code == 200
        created_event = create_response.json()
        
        # List all events
        list_response = client.get("/events")
        assert list_response.status_code == 200
        data = list_response.json()
        
        # Verify the created event is in the list
        assert data["total"] == 1
        assert data["pending"] == 1
        assert len(data["events"]) == 1
        
        # Verify event details
        event = data["events"][0]
        assert event["event_id"] == created_event["event_id"]
        assert event["modality"] == "email"
        assert event["status"] == "pending"
        assert event["priority"] == 50  # default priority
    
    def test_get_events_returns_multiple_events(self, client_with_engine):
        """Test that GET /events returns all events when multiple exist."""
        client, engine = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create multiple events with different modalities
        events_to_create = [
            make_event_request(
                current_time + timedelta(hours=1),
                "email",
                email_event_data(
                    from_address="sender1@example.com",
                    subject="Email 1",
                    body_text="First email",
                ),
            ),
            make_event_request(
                current_time + timedelta(hours=2),
                "sms",
                sms_event_data(
                    from_number="+1234567890",
                    to_numbers=["+0987654321"],
                    body="Text message",
                ),
            ),
            make_event_request(
                current_time + timedelta(hours=3),
                "chat",
                chat_event_data(role="user", content="Hello assistant"),
            ),
        ]
        
        created_ids = []
        for event_data in events_to_create:
            response = client.post("/events", json=event_data)
            assert response.status_code == 200
            created_ids.append(response.json()["event_id"])
        
        # List all events
        list_response = client.get("/events")
        assert list_response.status_code == 200
        data = list_response.json()
        
        # Verify counts
        assert data["total"] == 3
        assert data["pending"] == 3
        assert len(data["events"]) == 3
        
        # Verify all created events are present
        returned_ids = [e["event_id"] for e in data["events"]]
        assert set(returned_ids) == set(created_ids)
    
    def test_get_events_filter_by_status(self, client_with_engine):
        """Test that GET /events can filter by status."""
        client, engine = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create a pending event
        pending_time = current_time + timedelta(hours=1)
        client.post(
            "/events",
            json=make_event_request(
                pending_time,
                "email",
                email_event_data(subject="Pending Email", body_text="This is pending"),
            ),
        )
        
        # Filter by pending status
        response = client.get("/events", params={"status": "pending"})
        assert response.status_code == 200
        data = response.json()
        
        # Should return the pending event
        assert data["total"] == 1
        assert data["events"][0]["status"] == "pending"
        
        # Filter by executed status (should be empty)
        response = client.get("/events", params={"status": "executed"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["events"]) == 0
    
    def test_get_events_filter_by_modality(self, client_with_engine):
        """Test that GET /events can filter by modality."""
        client, engine = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create events with different modalities
        client.post(
            "/events",
            json=make_event_request(
                current_time + timedelta(hours=1),
                "email",
                email_event_data(subject="Email", body_text="Email content"),
            ),
        )
        
        client.post(
            "/events",
            json=make_event_request(
                current_time + timedelta(hours=2),
                "sms",
                sms_event_data(body="SMS content"),
            ),
        )
        
        # Filter by email modality
        response = client.get("/events", params={"modality": "email"})
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 1
        assert data["events"][0]["modality"] == "email"
        
        # Filter by sms modality
        response = client.get("/events", params={"modality": "sms"})
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 1
        assert data["events"][0]["modality"] == "sms"
    
    def test_get_events_filter_by_time_range(self, client_with_engine):
        """Test that GET /events can filter by time range."""
        client, engine = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create events at different times
        early_time = current_time + timedelta(hours=1)
        middle_time = current_time + timedelta(hours=5)
        late_time = current_time + timedelta(hours=10)
        
        for event_time in [early_time, middle_time, late_time]:
            client.post(
                "/events",
                json=make_event_request(
                    event_time,
                    "chat",
                    chat_event_data(content=f"Message at {event_time}"),
                ),
            )
        
        # Filter to get events between hours 3 and 7
        start_filter = current_time + timedelta(hours=3)
        end_filter = current_time + timedelta(hours=7)
        
        response = client.get(
            "/events",
            params={
                "start_time": start_filter.isoformat(),
                "end_time": end_filter.isoformat(),
            },
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should only return the middle event
        assert data["total"] == 1
        returned_time = datetime.fromisoformat(data["events"][0]["scheduled_time"])
        assert abs((returned_time - middle_time).total_seconds()) < 1
    
    def test_get_events_pagination_with_limit(self, client_with_engine):
        """Test that GET /events supports pagination with limit parameter."""
        client, engine = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create 5 events
        for i in range(5):
            client.post(
                "/events",
                json=make_event_request(
                    current_time + timedelta(hours=i),
                    "chat",
                    chat_event_data(content=f"Message {i}"),
                ),
            )
        
        # Get first 2 events
        response = client.get("/events", params={"limit": 2})
        assert response.status_code == 200
        data = response.json()
        
        # Should return 2 events, but total should be 5
        assert len(data["events"]) == 2
        assert data["total"] == 5
    
    def test_get_events_pagination_with_offset(self, client_with_engine):
        """Test that GET /events supports pagination with offset parameter."""
        client, engine = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create 5 events
        for i in range(5):
            client.post(
                "/events",
                json=make_event_request(
                    current_time + timedelta(hours=i),
                    "chat",
                    chat_event_data(content=f"Message {i}"),
                ),
            )
        
        # Get all events first
        all_response = client.get("/events")
        all_events = all_response.json()["events"]
        
        # Get events with offset=2
        offset_response = client.get("/events", params={"offset": 2})
        offset_data = offset_response.json()
        
        # Should skip first 2 events, returning last 3
        assert len(offset_data["events"]) == 3
        assert offset_data["total"] == 5  # Total matching events BEFORE pagination
        
        # Verify we got events starting from index 2
        assert offset_data["events"][0]["event_id"] == all_events[2]["event_id"]
    
    def test_get_events_combined_filters(self, client_with_engine):
        """Test that GET /events can combine multiple filters."""
        client, engine = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create events with different modalities and times
        for i in range(3):
            # Email events
            client.post(
                "/events",
                json=make_event_request(
                    current_time + timedelta(hours=i),
                    "email",
                    email_event_data(
                        operation="receive",
                        from_address=f"sender{i}@example.com",
                        to_addresses=["user@example.com"],
                        subject=f"Email {i}",
                        body_text="Content",
                    ),
                ),
            )
            # SMS events
            client.post(
                "/events",
                json=make_event_request(
                    current_time + timedelta(hours=i),
                    "sms",
                    sms_event_data(
                        action="receive_message",
                        from_number=f"+123456789{i}",
                        to_numbers=["+0987654321"],
                        body=f"SMS {i}",
                    ),
                ),
            )
        
        # Filter by modality=email AND time range (hours 1-3)
        start_filter = current_time + timedelta(hours=0.5)
        end_filter = current_time + timedelta(hours=2.5)
        
        response = client.get(
            "/events",
            params={
                "modality": "email",
                "start_time": start_filter.isoformat(),
                "end_time": end_filter.isoformat(),
            },
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should return 2 email events (at hours 1 and 2)
        assert data["total"] == 2
        for event in data["events"]:
            assert event["modality"] == "email"
    
    def test_get_events_invalid_status(self, client_with_engine):
        """Test that GET /events returns error for invalid status."""
        client, engine = client_with_engine
        
        response = client.get("/events", params={"status": "invalid_status"})
        
        # Should return 400 Bad Request
        assert response.status_code == 400
        assert "Invalid status" in response.json()["detail"]
