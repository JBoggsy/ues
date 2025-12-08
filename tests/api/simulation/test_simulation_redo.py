"""Integration tests for POST /simulation/redo endpoint.

Tests verify that the simulation redo endpoint correctly re-applies undone
event executions, properly restores modality state, handles edge cases,
and returns appropriate responses.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_simulation_engine
from main import app


@pytest.fixture
def client_without_start(fresh_engine):
    """Provide a TestClient with a fresh SimulationEngine that is NOT started.
    
    Unlike client_with_engine, this fixture does NOT start the simulation,
    allowing tests to verify behavior with unstarted simulation.
    
    Yields:
        A tuple of (TestClient, SimulationEngine) for testing.
    """
    app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine
    client = TestClient(app)
    
    yield client, fresh_engine
    
    # Cleanup
    try:
        if fresh_engine.is_running:
            client.post("/simulation/stop")
    except Exception:
        pass
    
    app.dependency_overrides.clear()


class TestPostSimulationRedo:
    """Tests for POST /simulation/redo endpoint."""

    # ===== Success Cases =====

    def test_redo_returns_success_response(self, client_with_engine):
        """Test that POST /simulation/redo returns a successful response.
        
        Verifies:
        - Response status code is 200
        - Response contains expected fields
        """
        client, engine = client_with_engine
        
        # Execute an event, then undo it
        client.post("/location/update", json={"latitude": 40.7128, "longitude": -74.0060})
        client.post("/simulation/undo")
        
        # Redo
        response = client.post("/simulation/redo")
        
        assert response.status_code == 200
        data = response.json()
        assert "redone_count" in data
        assert "redone_events" in data
        assert "can_undo" in data
        assert "can_redo" in data

    def test_redo_single_location_update(self, client_with_engine):
        """Test redoing a single location update re-applies the state change.
        
        Verifies:
        - Location is updated, then undone
        - After redo, location is restored to the updated state
        """
        client, engine = client_with_engine
        
        # Store initial state
        initial_lat = engine.environment.get_state("location").current_latitude
        
        # Update location
        client.post("/location/update", json={"latitude": 40.7128, "longitude": -74.0060})
        
        # Verify update applied
        loc_state = engine.environment.get_state("location")
        assert loc_state.current_latitude == 40.7128
        
        # Undo
        client.post("/simulation/undo")
        
        # Verify undone to initial state
        loc_state = engine.environment.get_state("location")
        assert loc_state.current_latitude == initial_lat
        
        # Redo
        redo_response = client.post("/simulation/redo")
        assert redo_response.status_code == 200
        data = redo_response.json()
        assert data["redone_count"] == 1
        assert len(data["redone_events"]) == 1
        assert data["redone_events"][0]["modality"] == "location"
        assert data["can_undo"] is True
        
        # Verify location is restored
        loc_state = engine.environment.get_state("location")
        assert loc_state.current_latitude == 40.7128
        assert loc_state.current_longitude == -74.0060

    def test_redo_email_receive_restores_email(self, client_with_engine):
        """Test redoing an email receive restores the email to inbox.
        
        Verifies:
        - Email is received, then undone (removed)
        - After redo, email is back in inbox
        """
        client, engine = client_with_engine
        
        # Receive an email
        client.post(
            "/email/receive",
            json={
                "from_address": "sender@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Test Email",
                "body_text": "Hello World!",
            },
        )
        
        # Undo
        client.post("/simulation/undo")
        
        # Verify email removed
        email_state = engine.environment.get_state("email")
        assert len(email_state.emails) == 0
        
        # Redo
        redo_response = client.post("/simulation/redo")
        assert redo_response.status_code == 200
        assert redo_response.json()["redone_count"] == 1
        
        # Verify email is back
        email_state = engine.environment.get_state("email")
        assert len(email_state.emails) == 1

    def test_redo_sms_send_restores_message(self, client_with_engine):
        """Test redoing an SMS send restores the message.
        
        Verifies:
        - SMS is sent, then undone (removed)
        - After redo, message is back
        """
        client, engine = client_with_engine
        
        # Send SMS (to_numbers is a list)
        response = client.post(
            "/sms/send",
            json={
                "from_number": "+15559998888",
                "to_numbers": ["+15551234567"],
                "body": "Hello!",
            },
        )
        assert response.status_code == 200
        
        # Undo
        client.post("/simulation/undo")
        
        # Verify removed
        sms_state = engine.environment.get_state("sms")
        assert len(sms_state.conversations) == 0
        
        # Redo
        redo_response = client.post("/simulation/redo")
        assert redo_response.status_code == 200
        
        # Verify restored
        sms_state = engine.environment.get_state("sms")
        assert len(sms_state.conversations) == 1

    def test_redo_chat_send_restores_message(self, client_with_engine):
        """Test redoing a chat send restores the message.
        
        Verifies:
        - Chat is sent, then undone
        - After redo, message is back
        """
        client, engine = client_with_engine
        
        # Send chat
        client.post("/chat/send", json={"content": "Hello!", "role": "user"})
        
        # Undo
        client.post("/simulation/undo")
        
        # Verify removed
        chat_state = engine.environment.get_state("chat")
        assert len(chat_state.messages) == 0
        
        # Redo
        redo_response = client.post("/simulation/redo")
        assert redo_response.status_code == 200
        
        # Verify restored
        chat_state = engine.environment.get_state("chat")
        assert len(chat_state.messages) == 1

    def test_redo_multiple_events(self, client_with_engine):
        """Test redoing multiple events at once.
        
        Verifies:
        - Multiple events are undone
        - Redo with count > 1 redoes multiple events
        - All modality states are properly restored
        """
        client, engine = client_with_engine
        
        # Store initial state
        initial_email_count = len(engine.environment.get_state("email").emails)
        initial_chat_count = len(engine.environment.get_state("chat").messages)
        
        # Execute multiple events
        client.post("/location/update", json={"latitude": 40.7128, "longitude": -74.0060})
        client.post(
            "/email/receive",
            json={
                "from_address": "sender@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Email 1",
                "body_text": "First email",
            },
        )
        client.post("/chat/send", json={"content": "Chat message", "role": "user"})
        
        # Undo all three
        client.post("/simulation/undo", json={"count": 3})
        
        # Verify all undone
        assert len(engine.environment.get_state("email").emails) == initial_email_count
        assert len(engine.environment.get_state("chat").messages) == initial_chat_count
        
        # Redo all three
        redo_response = client.post("/simulation/redo", json={"count": 3})
        assert redo_response.status_code == 200
        data = redo_response.json()
        assert data["redone_count"] == 3
        assert len(data["redone_events"]) == 3
        
        # Verify all restored
        assert engine.environment.get_state("location").current_latitude == 40.7128
        assert len(engine.environment.get_state("email").emails) == initial_email_count + 1
        assert len(engine.environment.get_state("chat").messages) == initial_chat_count + 1

    def test_redo_updates_can_undo_flag(self, client_with_engine):
        """Test that redo properly sets can_undo flag.
        
        Verifies:
        - After redo, can_undo becomes True
        """
        client, engine = client_with_engine
        
        # Execute, undo
        client.post("/location/update", json={"latitude": 40.7128, "longitude": -74.0060})
        client.post("/simulation/undo")
        
        # Redo
        redo_response = client.post("/simulation/redo")
        data = redo_response.json()
        
        assert data["can_undo"] is True

    def test_redo_updates_can_redo_flag(self, client_with_engine):
        """Test that redo properly updates can_redo flag.
        
        Verifies:
        - After redoing the only undone event, can_redo becomes False
        """
        client, engine = client_with_engine
        
        # Execute, undo
        client.post("/location/update", json={"latitude": 40.7128, "longitude": -74.0060})
        client.post("/simulation/undo")
        
        # Redo
        redo_response = client.post("/simulation/redo")
        data = redo_response.json()
        
        # No more events to redo
        assert data["can_redo"] is False

    # ===== Edge Cases =====

    def test_redo_nothing_to_redo(self, client_with_engine):
        """Test that redo with nothing to redo returns appropriate response.
        
        Verifies:
        - Response indicates nothing was redone
        - redone_count is 0
        - message field explains situation
        """
        client, engine = client_with_engine
        
        # Execute an event but don't undo
        client.post("/location/update", json={"latitude": 40.7128, "longitude": -74.0060})
        
        # Try to redo without prior undo
        redo_response = client.post("/simulation/redo")
        
        assert redo_response.status_code == 200
        data = redo_response.json()
        assert data["redone_count"] == 0
        assert len(data["redone_events"]) == 0
        assert data["can_redo"] is False
        assert data["message"] == "Nothing to redo"

    def test_redo_count_more_than_available(self, client_with_engine):
        """Test that redo with count > available redoes only what's available.
        
        Verifies:
        - Only available events are redone
        - redone_count reflects actual redos
        """
        client, engine = client_with_engine
        
        # Execute 2 events, undo both
        client.post("/location/update", json={"latitude": 40.0, "longitude": -74.0})
        client.post("/location/update", json={"latitude": 41.0, "longitude": -75.0})
        client.post("/simulation/undo", json={"count": 2})
        
        # Try to redo 10 (only 2 available)
        redo_response = client.post("/simulation/redo", json={"count": 10})
        
        assert redo_response.status_code == 200
        data = redo_response.json()
        assert data["redone_count"] == 2
        assert len(data["redone_events"]) == 2

    def test_redo_default_count_is_one(self, client_with_engine):
        """Test that redo without count parameter redoes only one event.
        
        Verifies:
        - Default count is 1
        - Only one event is redone
        """
        client, engine = client_with_engine
        
        # Execute 3 events
        client.post("/location/update", json={"latitude": 40.0, "longitude": -74.0})
        client.post("/location/update", json={"latitude": 41.0, "longitude": -75.0})
        client.post("/location/update", json={"latitude": 42.0, "longitude": -76.0})
        
        # Undo all 3
        client.post("/simulation/undo", json={"count": 3})
        
        # Redo with default (no body)
        redo_response = client.post("/simulation/redo")
        
        assert redo_response.status_code == 200
        data = redo_response.json()
        assert data["redone_count"] == 1

    def test_redo_cleared_by_new_action(self, client_with_engine):
        """Test that redo stack is cleared when a new action is executed.
        
        Verifies:
        - After undo, redo is available
        - Executing a new action clears the redo stack
        - Redo then returns nothing to redo
        """
        client, engine = client_with_engine
        
        # Execute and undo
        client.post("/location/update", json={"latitude": 40.0, "longitude": -74.0})
        client.post("/simulation/undo")
        
        # Execute a new action (this should clear redo stack)
        client.post("/location/update", json={"latitude": 42.0, "longitude": -76.0})
        
        # Now redo should have nothing
        redo_response = client.post("/simulation/redo")
        data = redo_response.json()
        assert data["redone_count"] == 0
        assert data["can_redo"] is False

    # ===== Error Cases =====

    def test_redo_simulation_not_running(self, client_without_start):
        """Test that redo fails when simulation is not running.
        
        Verifies:
        - Returns 409 Conflict
        - Error message indicates simulation must be started
        """
        client, engine = client_without_start
        
        response = client.post("/simulation/redo")
        
        assert response.status_code == 409
        assert "not running" in response.json()["detail"].lower()

    def test_redo_invalid_count_zero(self, client_with_engine):
        """Test that redo with count=0 returns validation error.
        
        Verifies:
        - Returns 422 Unprocessable Entity
        """
        client, engine = client_with_engine
        
        response = client.post("/simulation/redo", json={"count": 0})
        
        assert response.status_code == 422

    def test_redo_invalid_count_negative(self, client_with_engine):
        """Test that redo with negative count returns validation error.
        
        Verifies:
        - Returns 422 Unprocessable Entity
        """
        client, engine = client_with_engine
        
        response = client.post("/simulation/redo", json={"count": -1})
        
        assert response.status_code == 422

    # ===== State Verification Tests =====

    def test_redo_restores_complete_location_state(self, client_with_engine):
        """Test that redo fully restores location state including history.
        
        Verifies:
        - Location update adds to history
        - Undo removes from history
        - Redo restores to history
        """
        client, engine = client_with_engine
        
        # Update location twice
        client.post("/location/update", json={"latitude": 40.0, "longitude": -74.0})
        client.post("/location/update", json={"latitude": 41.0, "longitude": -75.0})
        
        # Get original state
        loc_state = engine.environment.get_state("location")
        assert loc_state.current_latitude == 41.0
        assert len(loc_state.location_history) == 2
        
        # Undo
        client.post("/simulation/undo")
        
        # Verify undone
        loc_state = engine.environment.get_state("location")
        assert loc_state.current_latitude == 40.0
        assert len(loc_state.location_history) == 1
        
        # Redo
        client.post("/simulation/redo")
        
        # Verify restored to original
        loc_state = engine.environment.get_state("location")
        assert loc_state.current_latitude == 41.0
        assert len(loc_state.location_history) == 2

    def test_redo_restores_complete_email_state(self, client_with_engine):
        """Test that redo fully restores email state.
        
        Verifies:
        - Email is received
        - Undo removes it
        - Redo restores it with same content
        """
        client, engine = client_with_engine
        
        # Receive email
        client.post(
            "/email/receive",
            json={
                "from_address": "sender@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Important Email",
                "body_text": "This is important!",
            },
        )
        
        # Undo
        client.post("/simulation/undo")
        
        # Verify removed
        assert len(engine.environment.get_state("email").emails) == 0
        
        # Redo
        client.post("/simulation/redo")
        
        # Verify restored with same subject
        email_state = engine.environment.get_state("email")
        assert len(email_state.emails) == 1
        email = list(email_state.emails.values())[0]
        assert email.subject == "Important Email"

    def test_redo_restores_calendar_event(self, client_with_engine):
        """Test that redo fully restores calendar event.
        
        Verifies:
        - Calendar event is created
        - Undo removes it
        - Redo restores it
        """
        client, engine = client_with_engine
        
        # Create event (uses 'start' and 'end', not 'start_time'/'end_time')
        now = datetime.now(timezone.utc)
        response = client.post(
            "/calendar/create",
            json={
                "title": "Team Meeting",
                "start": (now + timedelta(hours=1)).isoformat(),
                "end": (now + timedelta(hours=2)).isoformat(),
            },
        )
        assert response.status_code == 200, f"Failed to create event: {response.json()}"
        
        # Verify created
        cal_state = engine.environment.get_state("calendar")
        assert len(cal_state.events) == 1
        
        # Undo
        client.post("/simulation/undo")
        assert len(engine.environment.get_state("calendar").events) == 0
        
        # Redo
        client.post("/simulation/redo")
        
        # Verify restored
        cal_state = engine.environment.get_state("calendar")
        assert len(cal_state.events) == 1

    def test_undo_redo_workflow(self, client_with_engine):
        """Test a complex undo/redo workflow.
        
        Verifies:
        - Multiple operations can be undone and redone
        - State is properly maintained throughout
        """
        client, engine = client_with_engine
        
        # Execute 4 events
        client.post("/location/update", json={"latitude": 40.0, "longitude": -74.0})  # Event 1
        client.post("/location/update", json={"latitude": 41.0, "longitude": -75.0})  # Event 2
        client.post("/location/update", json={"latitude": 42.0, "longitude": -76.0})  # Event 3
        client.post("/location/update", json={"latitude": 43.0, "longitude": -77.0})  # Event 4
        
        # Verify current state
        loc_state = engine.environment.get_state("location")
        assert loc_state.current_latitude == 43.0
        
        # Undo 2 events (back to Event 2)
        client.post("/simulation/undo", json={"count": 2})
        loc_state = engine.environment.get_state("location")
        assert loc_state.current_latitude == 41.0
        
        # Redo 1 event (forward to Event 3)
        client.post("/simulation/redo")
        loc_state = engine.environment.get_state("location")
        assert loc_state.current_latitude == 42.0
        
        # Undo 1 event (back to Event 2)
        client.post("/simulation/undo")
        loc_state = engine.environment.get_state("location")
        assert loc_state.current_latitude == 41.0
        
        # Redo 2 events (forward to Event 4)
        client.post("/simulation/redo", json={"count": 2})
        loc_state = engine.environment.get_state("location")
        assert loc_state.current_latitude == 43.0

    def test_undo_redo_preserves_redo_stack(self, client_with_engine):
        """Test that redo preserves remaining redo entries.
        
        Verifies:
        - After undoing multiple events
        - Redoing one at a time preserves the ability to redo more
        """
        client, engine = client_with_engine
        
        # Execute 3 events
        client.post("/location/update", json={"latitude": 40.0, "longitude": -74.0})
        client.post("/location/update", json={"latitude": 41.0, "longitude": -75.0})
        client.post("/location/update", json={"latitude": 42.0, "longitude": -76.0})
        
        # Undo all 3
        client.post("/simulation/undo", json={"count": 3})
        
        # Redo 1
        redo1 = client.post("/simulation/redo")
        assert redo1.json()["redone_count"] == 1
        assert redo1.json()["can_redo"] is True  # 2 more to redo
        
        # Redo 1 more
        redo2 = client.post("/simulation/redo")
        assert redo2.json()["redone_count"] == 1
        assert redo2.json()["can_redo"] is True  # 1 more to redo
        
        # Redo last one
        redo3 = client.post("/simulation/redo")
        assert redo3.json()["redone_count"] == 1
        assert redo3.json()["can_redo"] is False  # No more to redo
        
        # Verify final state
        loc_state = engine.environment.get_state("location")
        assert loc_state.current_latitude == 42.0
