"""Integration tests for GET /calendar/state endpoint."""

from datetime import datetime, timedelta, timezone


class TestGetCalendarState:
    """Tests for GET /calendar/state endpoint."""

    def test_returns_correct_structure(self, client_with_engine):
        """Test that GET /calendar/state returns response with correct structure."""
        client, engine = client_with_engine
        
        response = client.get("/calendar/state")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields exist per CalendarStateResponse model
        assert "modality_type" in data
        assert data["modality_type"] == "calendar"
        assert "last_updated" in data
        assert "update_count" in data
        assert "default_calendar_id" in data
        assert "user_timezone" in data
        assert "calendars" in data
        assert "events" in data
        assert "calendar_count" in data
        assert "event_count" in data

    def test_returns_empty_state_initially(self, client_with_engine):
        """Test that state has no events when no calendar events created."""
        client, engine = client_with_engine
        
        response = client.get("/calendar/state")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have default "primary" calendar but no events
        assert data["event_count"] == 0
        assert data["events"] == {}
        assert data["calendar_count"] >= 1  # At least primary calendar
        assert "primary" in data["calendars"]

    def test_reflects_created_event(self, client_with_engine):
        """Test that state includes event after it's created."""
        client, engine = client_with_engine
        
        # Get current time via API
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create an event
        start = current_time + timedelta(hours=1)
        end = current_time + timedelta(hours=2)
        
        create_response = client.post(
            "/calendar/create",
            json={
                "title": "Test Meeting",
                "start": start.isoformat(),
                "end": end.isoformat(),
                "calendar_id": "primary",
            },
        )
        assert create_response.status_code == 200
        
        # Verify event appears in state
        state_response = client.get("/calendar/state")
        assert state_response.status_code == 200
        data = state_response.json()
        
        assert data["event_count"] == 1
        assert len(data["events"]) == 1
        
        # Get the event
        event = list(data["events"].values())[0]
        assert event["title"] == "Test Meeting"
        assert event["calendar_id"] == "primary"

    def test_includes_all_event_types(self, client_with_engine):
        """Test that state includes single and recurring events."""
        client, engine = client_with_engine
        
        # Get current time via API
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create a one-time event
        start1 = current_time + timedelta(hours=1)
        end1 = current_time + timedelta(hours=2)
        
        client.post(
            "/calendar/create",
            json={
                "title": "One-time Event",
                "start": start1.isoformat(),
                "end": end1.isoformat(),
            },
        )
        
        # Create a recurring event
        start2 = current_time + timedelta(hours=3)
        end2 = current_time + timedelta(hours=4)
        
        client.post(
            "/calendar/create",
            json={
                "title": "Weekly Meeting",
                "start": start2.isoformat(),
                "end": end2.isoformat(),
                "recurrence": {
                    "frequency": "weekly",
                    "interval": 1,
                    "days_of_week": ["monday"],
                    "end_type": "never",
                },
            },
        )
        
        # Verify both events appear in state
        state_response = client.get("/calendar/state")
        assert state_response.status_code == 200
        data = state_response.json()
        
        assert data["event_count"] == 2
        
        events = list(data["events"].values())
        titles = [e["title"] for e in events]
        assert "One-time Event" in titles
        assert "Weekly Meeting" in titles
        
        # Verify recurring event has recurrence field
        recurring = [e for e in events if e["title"] == "Weekly Meeting"][0]
        assert recurring.get("recurrence") is not None
        assert recurring["recurrence"]["frequency"] == "weekly"

    def test_includes_event_metadata(self, client_with_engine):
        """Test that state includes event metadata (attendees, reminders, etc.)."""
        client, engine = client_with_engine
        
        # Get current time via API
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        start = current_time + timedelta(hours=1)
        end = current_time + timedelta(hours=2)
        
        # Create event with metadata
        create_response = client.post(
            "/calendar/create",
            json={
                "title": "Meeting with Metadata",
                "start": start.isoformat(),
                "end": end.isoformat(),
                "description": "Important meeting",
                "location": "Conference Room A",
                "organizer": "organizer@example.com",
                "attendees": [
                    {"email": "attendee@example.com", "response": "accepted"},
                ],
                "reminders": [
                    {"minutes_before": 15, "type": "notification"},
                ],
                "conference_link": "https://meet.example.com/abc123",
            },
        )
        assert create_response.status_code == 200
        
        # Verify metadata in state
        state_response = client.get("/calendar/state")
        assert state_response.status_code == 200
        data = state_response.json()
        
        event = list(data["events"].values())[0]
        assert event["description"] == "Important meeting"
        assert event["location"] == "Conference Room A"
        assert event["organizer"] == "organizer@example.com"
        assert len(event["attendees"]) == 1
        assert event["attendees"][0]["email"] == "attendee@example.com"
        assert len(event["reminders"]) == 1
        assert event["reminders"][0]["minutes_before"] == 15
        assert event["conference_link"] == "https://meet.example.com/abc123"

    def test_current_time_matches_simulator_time(self, client_with_engine):
        """Test that state's last_updated is accurate after operations."""
        client, engine = client_with_engine
        
        # Get initial state
        state_response = client.get("/calendar/state")
        assert state_response.status_code == 200
        initial_data = state_response.json()
        initial_update_count = initial_data["update_count"]
        
        # Get current time via API
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create an event
        start = current_time + timedelta(hours=1)
        end = current_time + timedelta(hours=2)
        
        client.post(
            "/calendar/create",
            json={
                "title": "Test Event",
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
        )
        
        # Verify update_count incremented
        state_response = client.get("/calendar/state")
        assert state_response.status_code == 200
        data = state_response.json()
        
        assert data["update_count"] == initial_update_count + 1
        # last_updated should be a valid ISO datetime
        last_updated = datetime.fromisoformat(data["last_updated"])
        assert last_updated is not None
