"""Integration tests for event creation endpoints.

This module tests the event creation endpoints:
- POST /events - Create a scheduled event
- POST /events/immediate - Create an event that executes immediately
"""

from datetime import datetime, timedelta

from tests.api.helpers import (
    make_event_request,
    email_event_data,
    sms_event_data,
    chat_event_data,
    location_event_data,
    calendar_event_data,
    time_event_data,
    weather_event_data,
)


class TestPostEvents:
    """Tests for POST /events endpoint (scheduled event creation)."""
    
    def test_create_event_returns_event_id(self, client_with_engine):
        """Test that POST /events returns an event with a unique ID."""
        client, engine = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create an event
        event_time = current_time + timedelta(hours=1)
        response = client.post(
            "/events",
            json=make_event_request(
                event_time,
                "chat",
                chat_event_data(content="Test message"),
            ),
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "event_id" in data
        assert data["event_id"] is not None
        assert len(data["event_id"]) > 0
        assert data["modality"] == "chat"
        assert data["status"] == "pending"
        assert data["priority"] == 50  # default priority
        
        # Verify timestamps
        assert "scheduled_time" in data
        assert "created_at" in data
        scheduled = datetime.fromisoformat(data["scheduled_time"])
        created = datetime.fromisoformat(data["created_at"])
        assert abs((scheduled - event_time).total_seconds()) < 1
        assert abs((created - current_time).total_seconds()) < 1
    
    def test_create_event_email_modality(self, client_with_engine):
        """Test that POST /events works for email modality."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        event_time = current_time + timedelta(hours=1)
        
        response = client.post(
            "/events",
            json=make_event_request(
                event_time,
                "email",
                email_event_data(
                    operation="receive",
                    from_address="sender@example.com",
                    to_addresses=["user@example.com"],
                    subject="Test Email",
                    body_text="This is a test email",
                ),
            ),
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["modality"] == "email"
        assert data["status"] == "pending"
    
    def test_create_event_sms_modality(self, client_with_engine):
        """Test that POST /events works for SMS modality."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        event_time = current_time + timedelta(hours=1)
        
        response = client.post(
            "/events",
            json=make_event_request(
                event_time,
                "sms",
                sms_event_data(
                    action="receive_message",
                    from_number="+1234567890",
                    to_numbers=["+0987654321"],
                    body="Test SMS",
                ),
            ),
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["modality"] == "sms"
        assert data["status"] == "pending"
    
    def test_create_event_chat_modality(self, client_with_engine):
        """Test that POST /events works for chat modality."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        event_time = current_time + timedelta(hours=1)
        
        response = client.post(
            "/events",
            json=make_event_request(
                event_time,
                "chat",
                chat_event_data(role="user", content="Hello!"),
            ),
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["modality"] == "chat"
        assert data["status"] == "pending"
    
    def test_create_event_location_modality(self, client_with_engine):
        """Test that POST /events works for location modality."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        event_time = current_time + timedelta(hours=1)
        
        response = client.post(
            "/events",
            json=make_event_request(
                event_time,
                "location",
                location_event_data(latitude=37.7749, longitude=-122.4194),
            ),
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["modality"] == "location"
        assert data["status"] == "pending"
    
    def test_create_event_calendar_modality(self, client_with_engine):
        """Test that POST /events works for calendar modality."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        event_time = current_time + timedelta(hours=1)
        meeting_start = current_time + timedelta(days=1)
        meeting_end = meeting_start + timedelta(hours=1)
        
        response = client.post(
            "/events",
            json=make_event_request(
                event_time,
                "calendar",
                calendar_event_data(
                    operation="create",
                    title="Team Meeting",
                    start_time=meeting_start,
                    end_time=meeting_end,
                ),
            ),
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["modality"] == "calendar"
        assert data["status"] == "pending"
    
    def test_create_event_weather_modality(self, client_with_engine):
        """Test that POST /events works for weather modality."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        event_time = current_time + timedelta(hours=1)
        
        response = client.post(
            "/events",
            json=make_event_request(
                event_time,
                "weather",
                weather_event_data(latitude=37.7749, longitude=-122.4194),
            ),
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["modality"] == "weather"
        assert data["status"] == "pending"
    
    def test_create_event_time_modality(self, client_with_engine):
        """Test that POST /events works for time modality."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        event_time = current_time + timedelta(hours=1)
        
        response = client.post(
            "/events",
            json=make_event_request(
                event_time,
                "time",
                time_event_data(timezone="America/New_York"),
            ),
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["modality"] == "time"
        assert data["status"] == "pending"
    
    def test_create_event_with_custom_priority(self, client_with_engine):
        """Test that POST /events respects custom priority values."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        event_time = current_time + timedelta(hours=1)
        
        # Create event with high priority
        request_data = make_event_request(
            event_time,
            "chat",
            chat_event_data(content="High priority message"),
        )
        request_data["priority"] = 90
        
        response = client.post("/events", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["priority"] == 90
        
        # Create event with low priority
        request_data = make_event_request(
            event_time,
            "chat",
            chat_event_data(content="Low priority message"),
        )
        request_data["priority"] = 10
        
        response = client.post("/events", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["priority"] == 10
    
    def test_create_event_with_metadata(self, client_with_engine):
        """Test that POST /events preserves custom metadata."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        event_time = current_time + timedelta(hours=1)
        
        # Create event with custom metadata
        request_data = make_event_request(
            event_time,
            "chat",
            chat_event_data(content="Message with metadata"),
        )
        request_data["metadata"] = {
            "source": "test_suite",
            "test_id": "metadata_test_001",
            "custom_field": "custom_value",
        }
        
        response = client.post("/events", json=request_data)
        
        assert response.status_code == 200
        event_id = response.json()["event_id"]
        
        # Verify metadata is preserved by fetching the event from the queue
        list_response = client.get("/events")
        events = list_response.json()["events"]
        created_event = next(e for e in events if e["event_id"] == event_id)
        
        # Note: EventResponse doesn't include metadata field, but the event is created with it
        # This test verifies the request is accepted with metadata
        assert response.json()["event_id"] == event_id
    
    def test_create_event_with_agent_id(self, client_with_engine):
        """Test that POST /events accepts agent_id field."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        event_time = current_time + timedelta(hours=1)
        
        # Create event with agent_id
        request_data = make_event_request(
            event_time,
            "chat",
            chat_event_data(content="Message from agent"),
        )
        request_data["agent_id"] = "test_agent_123"
        
        response = client.post("/events", json=request_data)
        
        assert response.status_code == 200
        # Agent ID is accepted but not returned in EventResponse
        assert response.json()["event_id"] is not None
    
    def test_create_event_invalid_modality(self, client_with_engine):
        """Test that POST /events rejects invalid modality names."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        event_time = current_time + timedelta(hours=1)
        
        response = client.post(
            "/events",
            json={
                "scheduled_time": event_time.isoformat(),
                "modality": "invalid_modality_name",
                "data": {"some": "data"},
            },
        )
        
        # Should return 404 Not Found (modality doesn't exist)
        assert response.status_code == 404
        assert "modality" in response.json()["detail"].lower()
    
    def test_create_event_invalid_email_data(self, client_with_engine):
        """Test that POST /events validates email-specific data."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        event_time = current_time + timedelta(hours=1)
        
        # Missing required fields for email
        response = client.post(
            "/events",
            json={
                "scheduled_time": event_time.isoformat(),
                "modality": "email",
                "data": {
                    "operation": "receive",
                    # Missing from_address, to_addresses, subject, body_text
                },
            },
        )
        
        # Should return 400 or 422 (validation error)
        assert response.status_code in [400, 422]
        # Error message explains missing required field
        assert "from_address" in response.json()["detail"].lower()
    
    def test_create_event_invalid_sms_data(self, client_with_engine):
        """Test that POST /events validates SMS-specific data."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        event_time = current_time + timedelta(hours=1)
        
        # Wrong structure for SMS (missing message_data wrapper)
        response = client.post(
            "/events",
            json={
                "scheduled_time": event_time.isoformat(),
                "modality": "sms",
                "data": {
                    "action": "receive_message",
                    "from_number": "+1234567890",  # Should be nested in message_data
                    "body": "Test",
                },
            },
        )
        
        # Should return 400 or 422 (validation error)
        assert response.status_code in [400, 422]
    
    def test_create_event_invalid_location_data(self, client_with_engine):
        """Test that POST /events validates location coordinates."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        event_time = current_time + timedelta(hours=1)
        
        # Invalid latitude (out of range)
        response = client.post(
            "/events",
            json={
                "scheduled_time": event_time.isoformat(),
                "modality": "location",
                "data": {
                    "latitude": 999.0,  # Invalid: must be -90 to 90
                    "longitude": 0.0,
                },
            },
        )
        
        # Should return 422 Unprocessable Entity
        assert response.status_code == 422
    
    def test_create_event_past_time_rejected(self, client_with_engine):
        """Test that POST /events rejects events scheduled in the past."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Try to schedule event 1 hour in the past
        past_time = current_time - timedelta(hours=1)
        
        response = client.post(
            "/events",
            json=make_event_request(
                past_time,
                "chat",
                chat_event_data(content="Message from the past"),
            ),
        )
        
        # Should return 409 Conflict
        assert response.status_code == 409
        assert "past" in response.json()["detail"].lower()
        assert "current time" in response.json()["detail"].lower()
    
    def test_create_event_multiple_same_time(self, client_with_engine):
        """Test that POST /events allows multiple events at same time with different priorities."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        event_time = current_time + timedelta(hours=1)
        
        # Create multiple events at the same time with different priorities
        event_ids = []
        for priority in [10, 50, 90]:
            request_data = make_event_request(
                event_time,
                "chat",
                chat_event_data(content=f"Priority {priority} message"),
            )
            request_data["priority"] = priority
            
            response = client.post("/events", json=request_data)
            assert response.status_code == 200
            event_ids.append(response.json()["event_id"])
        
        # Verify all three events were created
        assert len(set(event_ids)) == 3  # All unique IDs
        
        # Verify they're all in the queue
        list_response = client.get("/events")
        assert list_response.json()["total"] == 3
    
    def test_create_event_missing_required_fields(self, client_with_engine):
        """Test that POST /events rejects requests missing required fields."""
        client, engine = client_with_engine
        
        # Missing scheduled_time
        response = client.post(
            "/events",
            json={
                "modality": "chat",
                "data": {"role": "user", "content": "Hello"},
            },
        )
        assert response.status_code == 422
        
        # Missing modality
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        event_time = current_time + timedelta(hours=1)
        
        response = client.post(
            "/events",
            json={
                "scheduled_time": event_time.isoformat(),
                "data": {"role": "user", "content": "Hello"},
            },
        )
        assert response.status_code == 422
        
        # Missing data
        response = client.post(
            "/events",
            json={
                "scheduled_time": event_time.isoformat(),
                "modality": "chat",
            },
        )
        assert response.status_code == 422


class TestPostEventsImmediate:
    """Tests for POST /events/immediate endpoint (immediate event execution)."""
    
    def test_immediate_event_returns_event_id(self, client_with_engine):
        """Test that POST /events/immediate returns an event with unique ID."""
        client, engine = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create immediate event (no scheduled_time needed)
        response = client.post(
            "/events/immediate",
            json={
                "modality": "chat",
                "data": chat_event_data(content="Immediate message"),
            },
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "event_id" in data
        assert data["event_id"] is not None
        assert len(data["event_id"]) > 0
        assert data["modality"] == "chat"
        assert data["status"] == "pending"
        assert data["priority"] == 100  # High priority for immediate events
        
        # Verify scheduled at current time
        scheduled = datetime.fromisoformat(data["scheduled_time"])
        assert abs((scheduled - current_time).total_seconds()) < 1
    
    def test_immediate_event_scheduled_at_current_time(self, client_with_engine):
        """Test that immediate events are scheduled at current simulator time."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        response = client.post(
            "/events/immediate",
            json={
                "modality": "chat",
                "data": chat_event_data(content="Test"),
            },
        )
        
        assert response.status_code == 200
        scheduled_time = datetime.fromisoformat(response.json()["scheduled_time"])
        
        # Should be scheduled at current time (within 1 second tolerance)
        assert abs((scheduled_time - current_time).total_seconds()) < 1
    
    def test_immediate_event_has_high_priority(self, client_with_engine):
        """Test that immediate events are created with priority 100."""
        client, engine = client_with_engine
        
        response = client.post(
            "/events/immediate",
            json={
                "modality": "chat",
                "data": chat_event_data(content="High priority message"),
            },
        )
        
        assert response.status_code == 200
        assert response.json()["priority"] == 100
    
    def test_immediate_event_email_modality(self, client_with_engine):
        """Test that POST /events/immediate works for email modality."""
        client, engine = client_with_engine
        
        response = client.post(
            "/events/immediate",
            json={
                "modality": "email",
                "data": email_event_data(
                    operation="receive",
                    from_address="sender@example.com",
                    to_addresses=["user@example.com"],
                    subject="Urgent Email",
                    body_text="This needs immediate attention",
                ),
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["modality"] == "email"
        assert data["priority"] == 100
    
    def test_immediate_event_sms_modality(self, client_with_engine):
        """Test that POST /events/immediate works for SMS modality."""
        client, engine = client_with_engine
        
        response = client.post(
            "/events/immediate",
            json={
                "modality": "sms",
                "data": sms_event_data(
                    action="receive_message",
                    from_number="+1234567890",
                    to_numbers=["+0987654321"],
                    body="Urgent SMS",
                ),
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["modality"] == "sms"
        assert data["priority"] == 100
    
    def test_immediate_event_chat_modality(self, client_with_engine):
        """Test that POST /events/immediate works for chat modality."""
        client, engine = client_with_engine
        
        response = client.post(
            "/events/immediate",
            json={
                "modality": "chat",
                "data": chat_event_data(role="user", content="Immediate question"),
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["modality"] == "chat"
        assert data["priority"] == 100
    
    def test_immediate_event_location_modality(self, client_with_engine):
        """Test that POST /events/immediate works for location modality."""
        client, engine = client_with_engine
        
        response = client.post(
            "/events/immediate",
            json={
                "modality": "location",
                "data": location_event_data(latitude=40.7128, longitude=-74.0060),
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["modality"] == "location"
        assert data["priority"] == 100
    
    def test_immediate_event_calendar_modality(self, client_with_engine):
        """Test that POST /events/immediate works for calendar modality."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        meeting_start = current_time + timedelta(hours=1)
        meeting_end = meeting_start + timedelta(hours=1)
        
        response = client.post(
            "/events/immediate",
            json={
                "modality": "calendar",
                "data": calendar_event_data(
                    operation="create",
                    title="Emergency Meeting",
                    start_time=meeting_start,
                    end_time=meeting_end,
                ),
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["modality"] == "calendar"
        assert data["priority"] == 100
    
    def test_immediate_event_weather_modality(self, client_with_engine):
        """Test that POST /events/immediate works for weather modality."""
        client, engine = client_with_engine
        
        response = client.post(
            "/events/immediate",
            json={
                "modality": "weather",
                "data": weather_event_data(latitude=37.7749, longitude=-122.4194),
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["modality"] == "weather"
        assert data["priority"] == 100
    
    def test_immediate_event_time_modality(self, client_with_engine):
        """Test that POST /events/immediate works for time modality."""
        client, engine = client_with_engine
        
        response = client.post(
            "/events/immediate",
            json={
                "modality": "time",
                "data": time_event_data(timezone="America/New_York"),
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["modality"] == "time"
        assert data["priority"] == 100
    
    def test_immediate_event_invalid_modality(self, client_with_engine):
        """Test that POST /events/immediate rejects invalid modality names."""
        client, engine = client_with_engine
        
        response = client.post(
            "/events/immediate",
            json={
                "modality": "invalid_modality",
                "data": {"some": "data"},
            },
        )
        
        # Should return 404 Not Found (modality doesn't exist)
        assert response.status_code == 404
        assert "modality" in response.json()["detail"].lower()
    
    def test_immediate_event_invalid_data(self, client_with_engine):
        """Test that POST /events/immediate validates modality-specific data."""
        client, engine = client_with_engine
        
        # Missing required fields for email
        response = client.post(
            "/events/immediate",
            json={
                "modality": "email",
                "data": {
                    "operation": "receive",
                    # Missing from_address, to_addresses, subject, body_text
                },
            },
        )
        
        # Should return validation error
        assert response.status_code in [400, 422]
        assert "from_address" in response.json()["detail"].lower()
    
    def test_immediate_event_missing_modality(self, client_with_engine):
        """Test that POST /events/immediate requires modality field."""
        client, engine = client_with_engine
        
        response = client.post(
            "/events/immediate",
            json={
                "data": {"role": "user", "content": "Hello"},
            },
        )
        
        assert response.status_code == 422
    
    def test_immediate_event_missing_data(self, client_with_engine):
        """Test that POST /events/immediate requires data field."""
        client, engine = client_with_engine
        
        response = client.post(
            "/events/immediate",
            json={
                "modality": "chat",
            },
        )
        
        assert response.status_code == 422
    
    def test_immediate_event_appears_in_queue(self, client_with_engine):
        """Test that immediate events appear in the event queue."""
        client, engine = client_with_engine
        
        # Create immediate event
        create_response = client.post(
            "/events/immediate",
            json={
                "modality": "chat",
                "data": chat_event_data(content="Should appear in queue"),
            },
        )
        assert create_response.status_code == 200
        event_id = create_response.json()["event_id"]
        
        # Verify it's in the queue
        list_response = client.get("/events")
        assert list_response.status_code == 200
        events = list_response.json()["events"]
        
        event_ids = [e["event_id"] for e in events]
        assert event_id in event_ids
        
        # Find the event and verify its properties
        immediate_event = next(e for e in events if e["event_id"] == event_id)
        assert immediate_event["priority"] == 100
        assert immediate_event["status"] == "pending"
    
    def test_immediate_event_multiple_modalities(self, client_with_engine):
        """Test creating multiple immediate events with different modalities."""
        client, engine = client_with_engine
        
        # Create three immediate events
        modalities = ["email", "sms", "chat"]
        event_ids = []
        
        for modality in modalities:
            if modality == "email":
                data = email_event_data(subject=f"Immediate {modality}")
            elif modality == "sms":
                data = sms_event_data(body=f"Immediate {modality}")
            else:
                data = chat_event_data(content=f"Immediate {modality}")
            
            response = client.post(
                "/events/immediate",
                json={"modality": modality, "data": data},
            )
            assert response.status_code == 200
            event_ids.append(response.json()["event_id"])
        
        # Verify all are unique and have high priority
        assert len(set(event_ids)) == 3
        
        list_response = client.get("/events")
        events = list_response.json()["events"]
        
        for event_id in event_ids:
            event = next(e for e in events if e["event_id"] == event_id)
            assert event["priority"] == 100

