"""Integration tests for calendar action endpoints."""

import re
from datetime import datetime, timedelta, timezone


def extract_calendar_event_id_from_message(message: str) -> str:
    """Extract calendar_event_id from the response message.
    
    Args:
        message: The response message containing calendar_event_id
        
    Returns:
        The extracted calendar event ID string
    """
    match = re.search(r"calendar_event_id: ([a-f0-9-]+)", message)
    if match:
        return match.group(1)
    raise ValueError(f"Could not extract calendar_event_id from message: {message}")


def get_calendar_event_id_from_state(client) -> str:
    """Get the most recently created calendar event ID from state.
    
    Args:
        client: The test client
        
    Returns:
        The event ID of the most recent calendar event
    """
    state = client.get("/calendar/state").json()
    events = list(state["events"].values())
    if not events:
        raise ValueError("No calendar events found in state")
    # Return the most recently created event
    events.sort(key=lambda e: e["created_at"], reverse=True)
    return events[0]["event_id"]


class TestPostCalendarCreate:
    """Tests for POST /calendar/create endpoint."""

    def test_create_event_succeeds(self, client_with_engine):
        """Test creating a calendar event creates event successfully."""
        client, engine = client_with_engine
        
        # Get current time via API
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        start = current_time + timedelta(hours=1)
        end = current_time + timedelta(hours=2)
        
        response = client.post(
            "/calendar/create",
            json={
                "title": "Test Meeting",
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "event_id" in data
        assert "status" in data
        assert data["status"] == "executed"
        assert "message" in data
        assert data["modality"] == "calendar"
        assert "scheduled_time" in data
        # The calendar_event_id is included in the message
        assert "calendar_event_id" in data["message"]

    def test_create_all_day_event(self, client_with_engine):
        """Test creating an all-day event."""
        client, engine = client_with_engine
        
        # Get current time via API
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # All-day events use dates, not times (but API accepts datetime)
        start = current_time + timedelta(days=1)
        end = current_time + timedelta(days=2)
        
        response = client.post(
            "/calendar/create",
            json={
                "title": "Vacation Day",
                "start": start.isoformat(),
                "end": end.isoformat(),
                "all_day": True,
            },
        )
        
        assert response.status_code == 200
        
        # Verify all_day flag in state
        state_response = client.get("/calendar/state")
        data = state_response.json()
        
        event = list(data["events"].values())[0]
        assert event["all_day"] is True
        assert event["title"] == "Vacation Day"

    def test_create_with_attendees(self, client_with_engine):
        """Test creating event with attendees."""
        client, engine = client_with_engine
        
        # Get current time via API
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        start = current_time + timedelta(hours=1)
        end = current_time + timedelta(hours=2)
        
        response = client.post(
            "/calendar/create",
            json={
                "title": "Team Meeting",
                "start": start.isoformat(),
                "end": end.isoformat(),
                "organizer": "organizer@example.com",
                "attendees": [
                    {
                        "email": "alice@example.com",
                        "display_name": "Alice Smith",
                        "optional": False,
                        "response": "accepted",
                    },
                    {
                        "email": "bob@example.com",
                        "display_name": "Bob Jones",
                        "optional": True,
                        "response": "tentative",
                    },
                ],
            },
        )
        
        assert response.status_code == 200
        
        # Verify attendees in state
        state_response = client.get("/calendar/state")
        data = state_response.json()
        
        event = list(data["events"].values())[0]
        assert len(event["attendees"]) == 2
        
        emails = [a["email"] for a in event["attendees"]]
        assert "alice@example.com" in emails
        assert "bob@example.com" in emails

    def test_create_with_reminders(self, client_with_engine):
        """Test creating event with reminders."""
        client, engine = client_with_engine
        
        # Get current time via API
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        start = current_time + timedelta(hours=1)
        end = current_time + timedelta(hours=2)
        
        response = client.post(
            "/calendar/create",
            json={
                "title": "Important Meeting",
                "start": start.isoformat(),
                "end": end.isoformat(),
                "reminders": [
                    {"minutes_before": 15, "type": "notification"},
                    {"minutes_before": 60, "type": "email"},
                ],
            },
        )
        
        assert response.status_code == 200
        
        # Verify reminders in state
        state_response = client.get("/calendar/state")
        data = state_response.json()
        
        event = list(data["events"].values())[0]
        assert len(event["reminders"]) == 2
        
        reminder_minutes = [r["minutes_before"] for r in event["reminders"]]
        assert 15 in reminder_minutes
        assert 60 in reminder_minutes

    def test_create_recurring_event(self, client_with_engine):
        """Test creating a recurring event."""
        client, engine = client_with_engine
        
        # Get current time via API
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        start = current_time + timedelta(hours=1)
        end = current_time + timedelta(hours=2)
        
        response = client.post(
            "/calendar/create",
            json={
                "title": "Weekly Standup",
                "start": start.isoformat(),
                "end": end.isoformat(),
                "recurrence": {
                    "frequency": "weekly",
                    "interval": 1,
                    "days_of_week": ["monday", "wednesday", "friday"],
                    "end_type": "never",
                },
            },
        )
        
        assert response.status_code == 200
        
        # Verify recurrence in state
        state_response = client.get("/calendar/state")
        data = state_response.json()
        
        event = list(data["events"].values())[0]
        assert event["recurrence"] is not None
        assert event["recurrence"]["frequency"] == "weekly"
        assert event["recurrence"]["interval"] == 1
        assert "monday" in event["recurrence"]["days_of_week"]

    def test_create_with_location(self, client_with_engine):
        """Test creating event with location."""
        client, engine = client_with_engine
        
        # Get current time via API
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        start = current_time + timedelta(hours=1)
        end = current_time + timedelta(hours=2)
        
        response = client.post(
            "/calendar/create",
            json={
                "title": "Offsite Meeting",
                "start": start.isoformat(),
                "end": end.isoformat(),
                "location": "123 Main Street, Conference Room A",
            },
        )
        
        assert response.status_code == 200
        
        # Verify location in state
        state_response = client.get("/calendar/state")
        data = state_response.json()
        
        event = list(data["events"].values())[0]
        assert event["location"] == "123 Main Street, Conference Room A"

    def test_create_validates_required_fields(self, client_with_engine):
        """Test that missing required fields returns 422 error."""
        client, engine = client_with_engine
        
        # Missing title
        response = client.post("/calendar/create", json={})
        assert response.status_code == 422
        
        # Missing start
        response = client.post(
            "/calendar/create",
            json={"title": "Test", "end": "2024-01-01T10:00:00Z"},
        )
        assert response.status_code == 422
        
        # Missing end
        response = client.post(
            "/calendar/create",
            json={"title": "Test", "start": "2024-01-01T09:00:00Z"},
        )
        assert response.status_code == 422

    def test_create_validates_time_range(self, client_with_engine):
        """Test that end time must be after start time."""
        client, engine = client_with_engine
        
        # Get current time via API
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        start = current_time + timedelta(hours=2)
        end = current_time + timedelta(hours=1)  # End before start
        
        response = client.post(
            "/calendar/create",
            json={
                "title": "Invalid Event",
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
        )
        
        # Should fail validation (400 from business rule, not 422 from Pydantic)
        assert response.status_code == 400

    def test_state_reflects_created_event(self, client_with_engine):
        """Test that state includes event after create action."""
        client, engine = client_with_engine
        
        # Get initial state
        initial_state = client.get("/calendar/state").json()
        initial_count = initial_state["event_count"]
        
        # Get current time via API
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        start = current_time + timedelta(hours=1)
        end = current_time + timedelta(hours=2)
        
        response = client.post(
            "/calendar/create",
            json={
                "title": "New Event",
                "start": start.isoformat(),
                "end": end.isoformat(),
                "description": "Event created via API",
            },
        )
        
        assert response.status_code == 200
        
        # Verify event appears in state
        final_state = client.get("/calendar/state").json()
        assert final_state["event_count"] == initial_count + 1
        
        # Find the new event
        event = list(final_state["events"].values())[0]
        assert event["title"] == "New Event"
        assert event["description"] == "Event created via API"


class TestPostCalendarUpdate:
    """Tests for POST /calendar/update endpoint."""

    def test_update_event_succeeds(self, client_with_engine):
        """Test updating a calendar event succeeds."""
        client, engine = client_with_engine
        
        # Get current time via API
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # First create an event
        start = current_time + timedelta(hours=1)
        end = current_time + timedelta(hours=2)
        
        create_response = client.post(
            "/calendar/create",
            json={
                "title": "Original Title",
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
        )
        assert create_response.status_code == 200
        calendar_event_id = get_calendar_event_id_from_state(client)
        
        # Now update it
        response = client.post(
            "/calendar/update",
            json={
                "event_id": calendar_event_id,
                "title": "Updated Title",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "executed"

    def test_update_event_time(self, client_with_engine):
        """Test updating event start/end times."""
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
                "title": "Movable Event",
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
        )
        calendar_event_id = get_calendar_event_id_from_state(client)
        
        # Update to new time
        new_start = current_time + timedelta(hours=3)
        new_end = current_time + timedelta(hours=4)
        
        update_response = client.post(
            "/calendar/update",
            json={
                "event_id": calendar_event_id,
                "start": new_start.isoformat(),
                "end": new_end.isoformat(),
            },
        )
        
        assert update_response.status_code == 200
        
        # Verify time changed in state
        state = client.get("/calendar/state").json()
        event = state["events"][calendar_event_id]
        
        updated_start = datetime.fromisoformat(event["start"])
        assert updated_start >= new_start - timedelta(seconds=1)
        assert updated_start <= new_start + timedelta(seconds=1)

    def test_update_event_title(self, client_with_engine):
        """Test updating event title and description."""
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
                "title": "Original Title",
                "start": start.isoformat(),
                "end": end.isoformat(),
                "description": "Original description",
            },
        )
        calendar_event_id = get_calendar_event_id_from_state(client)
        
        # Update title and description
        update_response = client.post(
            "/calendar/update",
            json={
                "event_id": calendar_event_id,
                "title": "New Title",
                "description": "New description",
            },
        )
        
        assert update_response.status_code == 200
        
        # Verify changes in state
        state = client.get("/calendar/state").json()
        event = state["events"][calendar_event_id]
        
        assert event["title"] == "New Title"
        assert event["description"] == "New description"

    def test_update_attendees(self, client_with_engine):
        """Test updating event attendees."""
        client, engine = client_with_engine
        
        # Get current time via API
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create an event with one attendee
        start = current_time + timedelta(hours=1)
        end = current_time + timedelta(hours=2)
        
        create_response = client.post(
            "/calendar/create",
            json={
                "title": "Meeting",
                "start": start.isoformat(),
                "end": end.isoformat(),
                "attendees": [{"email": "original@example.com"}],
            },
        )
        calendar_event_id = get_calendar_event_id_from_state(client)
        
        # Update with new attendees
        update_response = client.post(
            "/calendar/update",
            json={
                "event_id": calendar_event_id,
                "attendees": [
                    {"email": "new1@example.com"},
                    {"email": "new2@example.com"},
                ],
            },
        )
        
        assert update_response.status_code == 200
        
        # Verify attendees in state
        state = client.get("/calendar/state").json()
        event = state["events"][calendar_event_id]
        
        assert len(event["attendees"]) == 2
        emails = [a["email"] for a in event["attendees"]]
        assert "new1@example.com" in emails
        assert "new2@example.com" in emails

    def test_update_validates_required_fields(self, client_with_engine):
        """Test that missing event_id returns 422 error."""
        client, engine = client_with_engine
        
        # Missing event_id
        response = client.post(
            "/calendar/update",
            json={"title": "Updated Title"},
        )
        
        assert response.status_code == 422

    def test_state_reflects_updated_event(self, client_with_engine):
        """Test that state shows updated event details."""
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
                "title": "Before Update",
                "start": start.isoformat(),
                "end": end.isoformat(),
                "location": "Old Location",
            },
        )
        calendar_event_id = get_calendar_event_id_from_state(client)
        
        # Update multiple fields
        update_response = client.post(
            "/calendar/update",
            json={
                "event_id": calendar_event_id,
                "title": "After Update",
                "location": "New Location",
                "status": "tentative",
            },
        )
        
        assert update_response.status_code == 200
        
        # Verify all updates in state
        state = client.get("/calendar/state").json()
        event = state["events"][calendar_event_id]
        
        assert event["title"] == "After Update"
        assert event["location"] == "New Location"
        assert event["status"] == "tentative"


class TestPostCalendarDelete:
    """Tests for POST /calendar/delete endpoint."""

    def test_delete_event_succeeds(self, client_with_engine):
        """Test deleting a calendar event succeeds."""
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
                "title": "Event to Delete",
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
        )
        calendar_event_id = get_calendar_event_id_from_state(client)
        
        # Delete the event
        response = client.post(
            "/calendar/delete",
            json={"event_id": calendar_event_id},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "executed"

    def test_delete_recurring_event_single(self, client_with_engine):
        """Test deleting single instance of recurring event."""
        client, engine = client_with_engine
        
        # Get current time via API
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create a recurring event
        start = current_time + timedelta(hours=1)
        end = current_time + timedelta(hours=2)
        
        create_response = client.post(
            "/calendar/create",
            json={
                "title": "Recurring Event",
                "start": start.isoformat(),
                "end": end.isoformat(),
                "recurrence": {
                    "frequency": "daily",
                    "interval": 1,
                    "end_type": "never",
                },
            },
        )
        calendar_event_id = get_calendar_event_id_from_state(client)
        
        # Delete single occurrence using recurrence_id
        occurrence_date = (current_time + timedelta(days=3)).date().isoformat()
        
        response = client.post(
            "/calendar/delete",
            json={
                "event_id": calendar_event_id,
                "recurrence_scope": "this",
                "recurrence_id": occurrence_date,
            },
        )
        
        assert response.status_code == 200
        
        # The recurring event should still exist
        state = client.get("/calendar/state").json()
        assert calendar_event_id in state["events"]
        
        # The exception date should be recorded
        event = state["events"][calendar_event_id]
        assert occurrence_date in event["recurrence_exceptions"]

    def test_delete_recurring_event_all(self, client_with_engine):
        """Test deleting all instances of recurring event."""
        client, engine = client_with_engine
        
        # Get current time via API
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create a recurring event
        start = current_time + timedelta(hours=1)
        end = current_time + timedelta(hours=2)
        
        create_response = client.post(
            "/calendar/create",
            json={
                "title": "Recurring Event to Delete",
                "start": start.isoformat(),
                "end": end.isoformat(),
                "recurrence": {
                    "frequency": "weekly",
                    "interval": 1,
                    "days_of_week": ["monday"],
                    "end_type": "never",
                },
            },
        )
        calendar_event_id = get_calendar_event_id_from_state(client)
        
        # Delete all occurrences
        response = client.post(
            "/calendar/delete",
            json={
                "event_id": calendar_event_id,
                "recurrence_scope": "all",
            },
        )
        
        assert response.status_code == 200
        
        # Event should be removed entirely
        state = client.get("/calendar/state").json()
        assert calendar_event_id not in state["events"]

    def test_delete_validates_required_fields(self, client_with_engine):
        """Test that missing event_id returns 422 error."""
        client, engine = client_with_engine
        
        # Missing event_id
        response = client.post("/calendar/delete", json={})
        
        assert response.status_code == 422

    def test_state_reflects_deleted_event(self, client_with_engine):
        """Test that state no longer includes deleted event."""
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
                "title": "Event to be Deleted",
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
        )
        calendar_event_id = get_calendar_event_id_from_state(client)
        
        # Verify event exists
        state_before = client.get("/calendar/state").json()
        assert calendar_event_id in state_before["events"]
        count_before = state_before["event_count"]
        
        # Delete the event
        delete_response = client.post(
            "/calendar/delete",
            json={"event_id": calendar_event_id},
        )
        assert delete_response.status_code == 200
        
        # Verify event is gone
        state_after = client.get("/calendar/state").json()
        assert calendar_event_id not in state_after["events"]
        assert state_after["event_count"] == count_before - 1
