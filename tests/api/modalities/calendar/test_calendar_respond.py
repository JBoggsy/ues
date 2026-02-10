"""Test for respond_to_event endpoint."""
from datetime import datetime, timedelta, timezone


class TestPostCalendarRespond:
    """Tests for POST /calendar/respond endpoint."""

    def _create_event_with_attendees(self, client, attendees):
        """Helper to create a calendar event with attendees and return the event ID."""
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])

        start = current_time + timedelta(hours=1)
        end = current_time + timedelta(hours=2)

        create_response = client.post("/calendar/create", json={
            "title": "Team Meeting",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "attendees": attendees,
        })
        assert create_response.status_code == 200

        state_response = client.get("/calendar/state")
        events = state_response.json()["events"]
        event_id = list(events.keys())[0]
        return event_id

    def test_respond_updates_attendee_status(self, client_with_engine):
        """Test that respond_to_event actually updates the attendee status in state.

        This test reproduces the bug reported in:
        'respond_to_event does not update attendee response_status'
        """
        client, engine = client_with_engine

        event_id = self._create_event_with_attendees(client, [
            {"email": "alice@example.com", "display_name": "Alice", "response": "needs-action"}
        ])

        # Verify initial state
        state_response = client.get("/calendar/state")
        initial_attendee = state_response.json()["events"][event_id]["attendees"][0]
        assert initial_attendee["response"] == "needs-action"

        # Respond to the event
        respond_response = client.post("/calendar/respond", json={
            "event_id": event_id,
            "attendee_email": "alice@example.com",
            "response": "accepted",
        })
        assert respond_response.status_code == 200
        assert respond_response.json()["status"] == "executed"

        # Verify state is updated
        state_response2 = client.get("/calendar/state")
        updated_attendee = state_response2.json()["events"][event_id]["attendees"][0]
        assert updated_attendee["response"] == "accepted", \
            f"Expected 'accepted' but got '{updated_attendee['response']}'"

    def test_respond_with_declined(self, client_with_engine):
        """Test responding with 'declined' status."""
        client, engine = client_with_engine

        event_id = self._create_event_with_attendees(client, [
            {"email": "bob@example.com", "display_name": "Bob", "response": "needs-action"}
        ])

        respond_response = client.post("/calendar/respond", json={
            "event_id": event_id,
            "attendee_email": "bob@example.com",
            "response": "declined",
        })
        assert respond_response.status_code == 200

        state_response = client.get("/calendar/state")
        attendee = state_response.json()["events"][event_id]["attendees"][0]
        assert attendee["response"] == "declined"

    def test_respond_with_tentative(self, client_with_engine):
        """Test responding with 'tentative' status."""
        client, engine = client_with_engine

        event_id = self._create_event_with_attendees(client, [
            {"email": "carol@example.com", "display_name": "Carol", "response": "needs-action"}
        ])

        respond_response = client.post("/calendar/respond", json={
            "event_id": event_id,
            "attendee_email": "carol@example.com",
            "response": "tentative",
        })
        assert respond_response.status_code == 200

        state_response = client.get("/calendar/state")
        attendee = state_response.json()["events"][event_id]["attendees"][0]
        assert attendee["response"] == "tentative"

    def test_respond_with_comment(self, client_with_engine):
        """Test that response comment is stored in attendee record."""
        client, engine = client_with_engine

        event_id = self._create_event_with_attendees(client, [
            {"email": "alice@example.com", "display_name": "Alice", "response": "needs-action"}
        ])

        respond_response = client.post("/calendar/respond", json={
            "event_id": event_id,
            "attendee_email": "alice@example.com",
            "response": "accepted",
            "comment": "Looking forward to it!",
        })
        assert respond_response.status_code == 200

        state_response = client.get("/calendar/state")
        attendee = state_response.json()["events"][event_id]["attendees"][0]
        assert attendee["response"] == "accepted"
        assert attendee["comment"] == "Looking forward to it!"

    def test_respond_updates_correct_attendee_among_multiple(self, client_with_engine):
        """Test that only the targeted attendee's response is updated."""
        client, engine = client_with_engine

        event_id = self._create_event_with_attendees(client, [
            {"email": "alice@example.com", "display_name": "Alice", "response": "needs-action"},
            {"email": "bob@example.com", "display_name": "Bob", "response": "needs-action"},
            {"email": "carol@example.com", "display_name": "Carol", "response": "needs-action"},
        ])

        # Only respond for Bob
        respond_response = client.post("/calendar/respond", json={
            "event_id": event_id,
            "attendee_email": "bob@example.com",
            "response": "accepted",
        })
        assert respond_response.status_code == 200

        state_response = client.get("/calendar/state")
        attendees = state_response.json()["events"][event_id]["attendees"]

        # Find each attendee by email
        attendee_map = {a["email"]: a for a in attendees}
        assert attendee_map["alice@example.com"]["response"] == "needs-action"
        assert attendee_map["bob@example.com"]["response"] == "accepted"
        assert attendee_map["carol@example.com"]["response"] == "needs-action"

    def test_respond_can_change_response_multiple_times(self, client_with_engine):
        """Test that an attendee can change their response multiple times."""
        client, engine = client_with_engine

        event_id = self._create_event_with_attendees(client, [
            {"email": "alice@example.com", "display_name": "Alice", "response": "needs-action"}
        ])

        # First: accept
        client.post("/calendar/respond", json={
            "event_id": event_id,
            "attendee_email": "alice@example.com",
            "response": "accepted",
        })
        state = client.get("/calendar/state").json()
        assert state["events"][event_id]["attendees"][0]["response"] == "accepted"

        # Second: change to tentative
        client.post("/calendar/respond", json={
            "event_id": event_id,
            "attendee_email": "alice@example.com",
            "response": "tentative",
        })
        state = client.get("/calendar/state").json()
        assert state["events"][event_id]["attendees"][0]["response"] == "tentative"

        # Third: decline
        client.post("/calendar/respond", json={
            "event_id": event_id,
            "attendee_email": "alice@example.com",
            "response": "declined",
        })
        state = client.get("/calendar/state").json()
        assert state["events"][event_id]["attendees"][0]["response"] == "declined"
