"""Test for respond_to_event endpoint."""
from datetime import datetime, timedelta, timezone


class TestPostCalendarRespond:
    """Tests for POST /calendar/respond endpoint."""

    def test_respond_updates_attendee_status(self, client_with_engine):
        """Test that respond_to_event actually updates the attendee status in state.
        
        This test reproduces the bug reported in: 
        'respond_to_event does not update attendee response_status'
        """
        client, engine = client_with_engine

        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        start = current_time + timedelta(hours=1)
        end = current_time + timedelta(hours=2)

        # Create a calendar event with an attendee
        create_response = client.post("/calendar/create", json={
            "title": "Team Meeting",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "attendees": [
                {"email": "alice@example.com", "display_name": "Alice", "response": "needs-action"}
            ],
        })
        assert create_response.status_code == 200
        assert create_response.json()["status"] == "executed"

        # Get the event ID from state
        state_response = client.get("/calendar/state")
        events = state_response.json()["events"]
        event_id = list(events.keys())[0]
        
        # Verify initial state
        initial_attendee = events[event_id]["attendees"][0]
        assert initial_attendee["response"] == "needs-action"

        # Respond to the event
        respond_response = client.post("/calendar/respond", json={
            "event_id": event_id,
            "attendee_email": "alice@example.com",
            "response": "accepted",
        })
        assert respond_response.status_code == 200
        assert respond_response.json()["status"] == "executed"

        # Check state again - THE BUG: status should be updated but isn't
        state_response2 = client.get("/calendar/state")
        events2 = state_response2.json()["events"]
        updated_attendee = events2[event_id]["attendees"][0]
        
        # This assertion FAILS due to the bug
        assert updated_attendee["response"] == "accepted", \
            f"Expected 'accepted' but got '{updated_attendee['response']}'"
