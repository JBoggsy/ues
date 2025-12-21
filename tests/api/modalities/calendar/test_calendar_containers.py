"""Integration tests for calendar container management endpoints.

These tests cover the calendar container CRUD operations:
- GET /calendar/calendars - List all calendars
- POST /calendar/calendars/create - Create a new calendar
- POST /calendar/calendars/update - Update a calendar
- POST /calendar/calendars/delete - Delete a calendar
- POST /calendar/calendars/set-default - Set default calendar
"""

from datetime import datetime, timedelta


class TestGetCalendars:
    """Tests for GET /calendar/calendars endpoint."""

    def test_returns_correct_structure(self, client_with_engine):
        """Test that GET /calendar/calendars returns response with correct structure."""
        client, engine = client_with_engine

        response = client.get("/calendar/calendars")

        assert response.status_code == 200
        data = response.json()

        # Verify required fields exist per ListCalendarsResponse model
        assert "calendars" in data
        assert "count" in data
        assert "default_calendar_id" in data
        assert isinstance(data["calendars"], list)
        assert isinstance(data["count"], int)
        assert isinstance(data["default_calendar_id"], str)

    def test_returns_primary_calendar_by_default(self, client_with_engine):
        """Test that a fresh state has the primary calendar."""
        client, engine = client_with_engine

        response = client.get("/calendar/calendars")

        assert response.status_code == 200
        data = response.json()

        assert data["count"] >= 1
        assert data["default_calendar_id"] == "primary"

        # Find primary calendar in list
        calendar_ids = [c["calendar_id"] for c in data["calendars"]]
        assert "primary" in calendar_ids

    def test_calendar_info_structure(self, client_with_engine):
        """Test that each calendar has correct CalendarInfo structure."""
        client, engine = client_with_engine

        response = client.get("/calendar/calendars")

        assert response.status_code == 200
        data = response.json()

        assert len(data["calendars"]) > 0
        calendar = data["calendars"][0]

        # Verify CalendarInfo fields
        assert "calendar_id" in calendar
        assert "name" in calendar
        assert "color" in calendar
        assert "visible" in calendar
        assert "event_count" in calendar
        assert "created_at" in calendar
        assert "updated_at" in calendar


class TestPostCalendarsCreate:
    """Tests for POST /calendar/calendars/create endpoint."""

    def test_create_calendar_succeeds(self, client_with_engine):
        """Test creating a calendar succeeds with valid data."""
        client, engine = client_with_engine

        response = client.post(
            "/calendar/calendars/create",
            json={
                "calendar_id": "work",
                "name": "Work Calendar",
                "color": "#dc2626",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert "message" in data
        assert "Work Calendar" in data["message"]
        assert data["calendar"] is not None
        assert data["calendar"]["calendar_id"] == "work"
        assert data["calendar"]["name"] == "Work Calendar"
        assert data["calendar"]["color"] == "#dc2626"

    def test_created_calendar_appears_in_list(self, client_with_engine):
        """Test that created calendar appears in calendar list."""
        client, engine = client_with_engine

        # Create a new calendar
        client.post(
            "/calendar/calendars/create",
            json={
                "calendar_id": "family",
                "name": "Family",
                "color": "#16a34a",
            },
        )

        # Verify it appears in list
        response = client.get("/calendar/calendars")
        data = response.json()

        calendar_ids = [c["calendar_id"] for c in data["calendars"]]
        assert "family" in calendar_ids

    def test_create_duplicate_calendar_fails(self, client_with_engine):
        """Test that creating a calendar with existing ID fails."""
        client, engine = client_with_engine

        # Create first calendar
        client.post(
            "/calendar/calendars/create",
            json={
                "calendar_id": "duplicate-test",
                "name": "First Calendar",
            },
        )

        # Try to create duplicate
        response = client.post(
            "/calendar/calendars/create",
            json={
                "calendar_id": "duplicate-test",
                "name": "Second Calendar",
            },
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_create_calendar_with_visibility_false(self, client_with_engine):
        """Test creating a calendar with visible=False."""
        client, engine = client_with_engine

        response = client.post(
            "/calendar/calendars/create",
            json={
                "calendar_id": "hidden-cal",
                "name": "Hidden Calendar",
                "visible": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["calendar"]["visible"] is False

    def test_create_calendar_uses_default_color(self, client_with_engine):
        """Test creating a calendar without color uses default."""
        client, engine = client_with_engine

        response = client.post(
            "/calendar/calendars/create",
            json={
                "calendar_id": "default-color-cal",
                "name": "Default Color Calendar",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Default color is #4285f4
        assert data["calendar"]["color"] == "#4285f4"


class TestPostCalendarsUpdate:
    """Tests for POST /calendar/calendars/update endpoint."""

    def test_update_calendar_name(self, client_with_engine):
        """Test updating calendar name."""
        client, engine = client_with_engine

        # Create a calendar first
        client.post(
            "/calendar/calendars/create",
            json={
                "calendar_id": "update-name-test",
                "name": "Original Name",
            },
        )

        # Update the name
        response = client.post(
            "/calendar/calendars/update",
            json={
                "calendar_id": "update-name-test",
                "name": "Updated Name",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["calendar"]["name"] == "Updated Name"

    def test_update_calendar_color(self, client_with_engine):
        """Test updating calendar color."""
        client, engine = client_with_engine

        # Create a calendar first
        client.post(
            "/calendar/calendars/create",
            json={
                "calendar_id": "update-color-test",
                "name": "Color Test",
                "color": "#000000",
            },
        )

        # Update the color
        response = client.post(
            "/calendar/calendars/update",
            json={
                "calendar_id": "update-color-test",
                "color": "#ff0000",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["calendar"]["color"] == "#ff0000"

    def test_update_calendar_visibility(self, client_with_engine):
        """Test updating calendar visibility."""
        client, engine = client_with_engine

        # Create a visible calendar
        client.post(
            "/calendar/calendars/create",
            json={
                "calendar_id": "visibility-test",
                "name": "Visibility Test",
                "visible": True,
            },
        )

        # Update visibility to false
        response = client.post(
            "/calendar/calendars/update",
            json={
                "calendar_id": "visibility-test",
                "visible": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["calendar"]["visible"] is False

    def test_update_multiple_fields(self, client_with_engine):
        """Test updating multiple calendar fields at once."""
        client, engine = client_with_engine

        # Create a calendar first
        client.post(
            "/calendar/calendars/create",
            json={
                "calendar_id": "multi-update-test",
                "name": "Original",
                "color": "#000000",
            },
        )

        # Update multiple fields
        response = client.post(
            "/calendar/calendars/update",
            json={
                "calendar_id": "multi-update-test",
                "name": "Updated",
                "color": "#ffffff",
                "visible": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["calendar"]["name"] == "Updated"
        assert data["calendar"]["color"] == "#ffffff"
        assert data["calendar"]["visible"] is False

    def test_update_nonexistent_calendar_fails(self, client_with_engine):
        """Test that updating a nonexistent calendar returns 404."""
        client, engine = client_with_engine

        response = client.post(
            "/calendar/calendars/update",
            json={
                "calendar_id": "nonexistent-calendar",
                "name": "New Name",
            },
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_update_preserves_unchanged_fields(self, client_with_engine):
        """Test that updating one field preserves others."""
        client, engine = client_with_engine

        # Create a calendar with specific values
        client.post(
            "/calendar/calendars/create",
            json={
                "calendar_id": "preserve-test",
                "name": "Original Name",
                "color": "#123456",
            },
        )

        # Update only the name
        response = client.post(
            "/calendar/calendars/update",
            json={
                "calendar_id": "preserve-test",
                "name": "New Name",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Name changed, color preserved
        assert data["calendar"]["name"] == "New Name"
        assert data["calendar"]["color"] == "#123456"


class TestPostCalendarsDelete:
    """Tests for POST /calendar/calendars/delete endpoint."""

    def test_delete_calendar_succeeds(self, client_with_engine):
        """Test deleting a calendar succeeds."""
        client, engine = client_with_engine

        # Create a calendar first
        client.post(
            "/calendar/calendars/create",
            json={
                "calendar_id": "to-delete",
                "name": "To Delete",
            },
        )

        # Delete it
        response = client.post(
            "/calendar/calendars/delete",
            json={"calendar_id": "to-delete"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert "Deleted" in data["message"]

    def test_deleted_calendar_removed_from_list(self, client_with_engine):
        """Test that deleted calendar is removed from calendar list."""
        client, engine = client_with_engine

        # Create a calendar
        client.post(
            "/calendar/calendars/create",
            json={
                "calendar_id": "remove-from-list",
                "name": "Will Be Removed",
            },
        )

        # Verify it exists
        list_response = client.get("/calendar/calendars")
        calendar_ids = [c["calendar_id"] for c in list_response.json()["calendars"]]
        assert "remove-from-list" in calendar_ids

        # Delete it
        client.post(
            "/calendar/calendars/delete",
            json={"calendar_id": "remove-from-list"},
        )

        # Verify it's gone
        list_response = client.get("/calendar/calendars")
        calendar_ids = [c["calendar_id"] for c in list_response.json()["calendars"]]
        assert "remove-from-list" not in calendar_ids

    def test_delete_calendar_removes_events(self, client_with_engine):
        """Test that deleting a calendar removes all its events."""
        client, engine = client_with_engine

        # Get current time via API
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])

        # Create a calendar
        client.post(
            "/calendar/calendars/create",
            json={
                "calendar_id": "cal-with-events",
                "name": "Calendar With Events",
            },
        )

        # Create an event in that calendar
        start = current_time + timedelta(hours=1)
        end = current_time + timedelta(hours=2)
        client.post(
            "/calendar/create",
            json={
                "title": "Event to be deleted",
                "start": start.isoformat(),
                "end": end.isoformat(),
                "calendar_id": "cal-with-events",
            },
        )

        # Verify event exists
        state_response = client.get("/calendar/state")
        assert state_response.json()["event_count"] > 0

        # Delete the calendar
        client.post(
            "/calendar/calendars/delete",
            json={"calendar_id": "cal-with-events"},
        )

        # Verify events in that calendar are gone
        state_response = client.get("/calendar/state")
        events = state_response.json()["events"]
        for event in events.values():
            assert event["calendar_id"] != "cal-with-events"

    def test_delete_default_calendar_fails(self, client_with_engine):
        """Test that deleting the default calendar fails."""
        client, engine = client_with_engine

        response = client.post(
            "/calendar/calendars/delete",
            json={"calendar_id": "primary"},
        )

        assert response.status_code == 400
        assert "default calendar" in response.json()["detail"].lower()

    def test_delete_nonexistent_calendar_fails(self, client_with_engine):
        """Test that deleting a nonexistent calendar returns 404."""
        client, engine = client_with_engine

        response = client.post(
            "/calendar/calendars/delete",
            json={"calendar_id": "nonexistent"},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestPostCalendarsSetDefault:
    """Tests for POST /calendar/calendars/set-default endpoint."""

    def test_set_default_calendar_succeeds(self, client_with_engine):
        """Test setting a calendar as default succeeds."""
        client, engine = client_with_engine

        # Create a new calendar
        client.post(
            "/calendar/calendars/create",
            json={
                "calendar_id": "new-default",
                "name": "New Default Calendar",
            },
        )

        # Set it as default
        response = client.post(
            "/calendar/calendars/set-default",
            json={"calendar_id": "new-default"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["calendar"]["calendar_id"] == "new-default"

    def test_set_default_updates_list_response(self, client_with_engine):
        """Test that setting default updates the calendars list response."""
        client, engine = client_with_engine

        # Create a new calendar
        client.post(
            "/calendar/calendars/create",
            json={
                "calendar_id": "will-be-default",
                "name": "Will Be Default",
            },
        )

        # Set it as default
        client.post(
            "/calendar/calendars/set-default",
            json={"calendar_id": "will-be-default"},
        )

        # Verify default_calendar_id in list response
        list_response = client.get("/calendar/calendars")
        data = list_response.json()

        assert data["default_calendar_id"] == "will-be-default"

    def test_set_default_updates_state_response(self, client_with_engine):
        """Test that setting default updates the state response."""
        client, engine = client_with_engine

        # Create a new calendar
        client.post(
            "/calendar/calendars/create",
            json={
                "calendar_id": "state-default",
                "name": "State Default",
            },
        )

        # Set it as default
        client.post(
            "/calendar/calendars/set-default",
            json={"calendar_id": "state-default"},
        )

        # Verify default_calendar_id in state response
        state_response = client.get("/calendar/state")
        data = state_response.json()

        assert data["default_calendar_id"] == "state-default"

    def test_set_default_nonexistent_calendar_fails(self, client_with_engine):
        """Test that setting nonexistent calendar as default fails."""
        client, engine = client_with_engine

        response = client.post(
            "/calendar/calendars/set-default",
            json={"calendar_id": "nonexistent"},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_set_default_to_primary(self, client_with_engine):
        """Test that we can set default back to primary."""
        client, engine = client_with_engine

        # Create a new calendar and set it as default
        client.post(
            "/calendar/calendars/create",
            json={
                "calendar_id": "temp-default",
                "name": "Temp Default",
            },
        )
        client.post(
            "/calendar/calendars/set-default",
            json={"calendar_id": "temp-default"},
        )

        # Set back to primary
        response = client.post(
            "/calendar/calendars/set-default",
            json={"calendar_id": "primary"},
        )

        assert response.status_code == 200

        # Verify
        list_response = client.get("/calendar/calendars")
        assert list_response.json()["default_calendar_id"] == "primary"
