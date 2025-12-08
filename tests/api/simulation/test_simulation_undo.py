"""Integration tests for POST /simulation/undo endpoint.

Tests verify that the simulation undo endpoint correctly reverses event
executions, properly restores modality state, handles edge cases, and 
returns appropriate responses.
"""

from datetime import datetime, timedelta, timezone
from copy import deepcopy

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


class TestPostSimulationUndo:
    """Tests for POST /simulation/undo endpoint."""

    # ===== Success Cases =====

    def test_undo_returns_success_response(self, client_with_engine):
        """Test that POST /simulation/undo returns a successful response.
        
        Verifies:
        - Response status code is 200
        - Response contains expected fields
        """
        client, engine = client_with_engine
        
        # Execute an event first so there's something to undo
        response = client.post(
            "/location/update",
            json={"latitude": 40.7128, "longitude": -74.0060},
        )
        assert response.status_code == 200
        
        # Undo
        response = client.post("/simulation/undo")
        
        assert response.status_code == 200
        data = response.json()
        assert "undone_count" in data
        assert "undone_events" in data
        assert "can_undo" in data
        assert "can_redo" in data

    def test_undo_single_location_update(self, client_with_engine):
        """Test undoing a single location update restores previous state.
        
        Verifies:
        - Location is updated
        - After undo, location is restored to previous state
        """
        client, engine = client_with_engine
        
        # Store initial location state
        initial_loc = engine.environment.get_state("location")
        initial_lat = initial_loc.current_latitude
        initial_lon = initial_loc.current_longitude
        
        # Update location
        response = client.post(
            "/location/update",
            json={"latitude": 40.7128, "longitude": -74.0060},
        )
        assert response.status_code == 200
        
        # Verify location was updated
        loc_state = engine.environment.get_state("location")
        assert loc_state.current_latitude == 40.7128
        assert loc_state.current_longitude == -74.0060
        
        # Undo
        undo_response = client.post("/simulation/undo")
        assert undo_response.status_code == 200
        data = undo_response.json()
        assert data["undone_count"] == 1
        assert len(data["undone_events"]) == 1
        assert data["undone_events"][0]["modality"] == "location"
        assert data["can_redo"] is True
        
        # Verify location is restored to initial state
        loc_state = engine.environment.get_state("location")
        assert loc_state.current_latitude == initial_lat
        assert loc_state.current_longitude == initial_lon

    def test_undo_email_receive_removes_email(self, client_with_engine):
        """Test undoing an email receive removes the email from inbox.
        
        Verifies:
        - Email is received and appears in inbox
        - After undo, email is removed from inbox
        """
        client, engine = client_with_engine
        
        # Receive an email
        response = client.post(
            "/email/receive",
            json={
                "from_address": "sender@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Test Email",
                "body_text": "Hello World!",
            },
        )
        assert response.status_code == 200
        
        # Verify email is in inbox
        email_state = engine.environment.get_state("email")
        assert len(email_state.emails) == 1
        
        # Undo
        undo_response = client.post("/simulation/undo")
        assert undo_response.status_code == 200
        data = undo_response.json()
        assert data["undone_count"] == 1
        # The undo action is the inverse operation name
        assert data["undone_events"][0]["modality"] == "email"
        
        # Verify email is removed
        email_state = engine.environment.get_state("email")
        assert len(email_state.emails) == 0

    def test_undo_sms_send_removes_message(self, client_with_engine):
        """Test undoing an SMS send removes the message from conversation.
        
        Verifies:
        - SMS is sent and appears in conversation
        - After undo, message is removed
        """
        client, engine = client_with_engine
        
        # Send an SMS (to_numbers is a list)
        response = client.post(
            "/sms/send",
            json={
                "from_number": "+15559998888",
                "to_numbers": ["+15551234567"],
                "body": "Hello from test!",
            },
        )
        assert response.status_code == 200
        
        # Verify SMS is in state
        sms_state = engine.environment.get_state("sms")
        assert len(sms_state.conversations) == 1
        
        # Undo
        undo_response = client.post("/simulation/undo")
        assert undo_response.status_code == 200
        assert undo_response.json()["undone_count"] == 1
        
        # Verify SMS is removed
        sms_state = engine.environment.get_state("sms")
        assert len(sms_state.conversations) == 0

    def test_undo_chat_send_removes_message(self, client_with_engine):
        """Test undoing a chat send removes the message from conversation.
        
        Verifies:
        - Chat message is sent and appears in conversation
        - After undo, message is removed
        """
        client, engine = client_with_engine
        
        # Send a chat message
        response = client.post(
            "/chat/send",
            json={
                "content": "Hello, assistant!",
                "role": "user",
            },
        )
        assert response.status_code == 200
        
        # Verify chat is in state
        chat_state = engine.environment.get_state("chat")
        assert len(chat_state.messages) == 1
        
        # Undo
        undo_response = client.post("/simulation/undo")
        assert undo_response.status_code == 200
        
        # Verify chat message is removed
        chat_state = engine.environment.get_state("chat")
        assert len(chat_state.messages) == 0

    def test_undo_multiple_events(self, client_with_engine):
        """Test undoing multiple events at once.
        
        Verifies:
        - Multiple events are executed
        - Undo with count > 1 undoes multiple events
        - All modality states are properly restored
        """
        client, engine = client_with_engine
        
        # Store initial states
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
        client.post(
            "/chat/send",
            json={"content": "Chat message", "role": "user"},
        )
        
        # Verify all three events applied
        assert engine.environment.get_state("location").current_latitude == 40.7128
        assert len(engine.environment.get_state("email").emails) == initial_email_count + 1
        assert len(engine.environment.get_state("chat").messages) == initial_chat_count + 1
        
        # Undo all three
        undo_response = client.post("/simulation/undo", json={"count": 3})
        assert undo_response.status_code == 200
        data = undo_response.json()
        assert data["undone_count"] == 3
        assert len(data["undone_events"]) == 3
        
        # Verify all states restored
        assert len(engine.environment.get_state("email").emails) == initial_email_count
        assert len(engine.environment.get_state("chat").messages) == initial_chat_count

    def test_undo_updates_can_redo_flag(self, client_with_engine):
        """Test that undo properly sets can_redo flag.
        
        Verifies:
        - After undo, can_redo becomes True
        """
        client, engine = client_with_engine
        
        # Execute an event
        client.post("/location/update", json={"latitude": 40.7128, "longitude": -74.0060})
        
        # Undo
        undo_response = client.post("/simulation/undo")
        data = undo_response.json()
        
        assert data["can_redo"] is True

    def test_undo_updates_can_undo_flag(self, client_with_engine):
        """Test that undo properly updates can_undo flag.
        
        Verifies:
        - After undoing the only event, can_undo becomes False
        """
        client, engine = client_with_engine
        
        # Execute one event
        client.post("/location/update", json={"latitude": 40.7128, "longitude": -74.0060})
        
        # Undo it
        undo_response = client.post("/simulation/undo")
        data = undo_response.json()
        
        # No more events to undo
        assert data["can_undo"] is False

    # ===== Edge Cases =====

    def test_undo_nothing_to_undo(self, client_with_engine):
        """Test that undo with nothing to undo returns appropriate response.
        
        Verifies:
        - Response indicates nothing was undone
        - undone_count is 0
        - message field explains situation
        """
        client, engine = client_with_engine
        
        # Don't execute any events - try to undo immediately
        undo_response = client.post("/simulation/undo")
        
        assert undo_response.status_code == 200
        data = undo_response.json()
        assert data["undone_count"] == 0
        assert len(data["undone_events"]) == 0
        assert data["can_undo"] is False
        assert data["message"] == "Nothing to undo"

    def test_undo_count_more_than_available(self, client_with_engine):
        """Test that undo with count > available undoes only what's available.
        
        Verifies:
        - Only available events are undone
        - undone_count reflects actual undos
        """
        client, engine = client_with_engine
        
        # Execute 2 events
        client.post("/location/update", json={"latitude": 40.7128, "longitude": -74.0060})
        client.post("/location/update", json={"latitude": 41.0, "longitude": -75.0})
        
        # Try to undo 10 (only 2 available)
        undo_response = client.post("/simulation/undo", json={"count": 10})
        
        assert undo_response.status_code == 200
        data = undo_response.json()
        assert data["undone_count"] == 2
        assert len(data["undone_events"]) == 2

    def test_undo_default_count_is_one(self, client_with_engine):
        """Test that undo without count parameter undoes only one event.
        
        Verifies:
        - Default count is 1
        - Only one event is undone
        """
        client, engine = client_with_engine
        
        # Execute 3 events
        client.post("/location/update", json={"latitude": 40.0, "longitude": -74.0})
        client.post("/location/update", json={"latitude": 41.0, "longitude": -75.0})
        client.post("/location/update", json={"latitude": 42.0, "longitude": -76.0})
        
        # Undo with default (no body)
        undo_response = client.post("/simulation/undo")
        
        assert undo_response.status_code == 200
        data = undo_response.json()
        assert data["undone_count"] == 1

    # ===== Error Cases =====

    def test_undo_simulation_not_running(self, client_without_start):
        """Test that undo fails when simulation is not running.
        
        Verifies:
        - Returns 409 Conflict
        - Error message indicates simulation must be started
        """
        client, engine = client_without_start
        
        response = client.post("/simulation/undo")
        
        assert response.status_code == 409
        assert "not running" in response.json()["detail"].lower()

    def test_undo_invalid_count_zero(self, client_with_engine):
        """Test that undo with count=0 returns validation error.
        
        Verifies:
        - Returns 422 Unprocessable Entity
        """
        client, engine = client_with_engine
        
        response = client.post("/simulation/undo", json={"count": 0})
        
        assert response.status_code == 422

    def test_undo_invalid_count_negative(self, client_with_engine):
        """Test that undo with negative count returns validation error.
        
        Verifies:
        - Returns 422 Unprocessable Entity
        """
        client, engine = client_with_engine
        
        response = client.post("/simulation/undo", json={"count": -1})
        
        assert response.status_code == 422

    # ===== State Verification Tests =====

    def test_undo_restores_complete_location_state(self, client_with_engine):
        """Test that undo fully restores location state including history.
        
        Verifies:
        - Location update adds to history
        - Undo restores history to previous state
        """
        client, engine = client_with_engine
        
        # Update location twice
        client.post("/location/update", json={"latitude": 40.0, "longitude": -74.0})
        client.post("/location/update", json={"latitude": 41.0, "longitude": -75.0})
        
        # Get state after both updates
        loc_state = engine.environment.get_state("location")
        assert loc_state.current_latitude == 41.0
        assert len(loc_state.location_history) == 2
        
        # Undo the second update
        client.post("/simulation/undo")
        
        # Verify state is restored
        loc_state = engine.environment.get_state("location")
        assert loc_state.current_latitude == 40.0
        assert len(loc_state.location_history) == 1

    def test_undo_restores_complete_email_state(self, client_with_engine):
        """Test that undo fully restores email state including folder placement.
        
        Verifies:
        - Email is received and in inbox
        - Undo removes email completely
        """
        client, engine = client_with_engine
        
        # Receive two emails
        client.post(
            "/email/receive",
            json={
                "from_address": "sender1@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "First Email",
                "body_text": "First",
            },
        )
        client.post(
            "/email/receive",
            json={
                "from_address": "sender2@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Second Email",
                "body_text": "Second",
            },
        )
        
        # Verify both emails present
        email_state = engine.environment.get_state("email")
        assert len(email_state.emails) == 2
        
        # Undo the second email
        client.post("/simulation/undo")
        
        # Verify only first email remains
        email_state = engine.environment.get_state("email")
        assert len(email_state.emails) == 1
        # Check the remaining email is the first one
        remaining_email = list(email_state.emails.values())[0]
        assert remaining_email.subject == "First Email"

    def test_undo_restores_complete_sms_state(self, client_with_engine):
        """Test that undo fully restores SMS state including conversation.
        
        Verifies:
        - SMS creates conversation and message
        - Undo removes message and empty conversation
        """
        client, engine = client_with_engine
        
        # Send SMS (to_numbers is a list)
        client.post(
            "/sms/send",
            json={
                "from_number": "+15559998888",
                "to_numbers": ["+15551234567"],
                "body": "Hello!",
            },
        )
        
        # Verify conversation exists
        sms_state = engine.environment.get_state("sms")
        assert len(sms_state.conversations) == 1
        
        # Undo
        client.post("/simulation/undo")
        
        # Verify conversation is removed
        sms_state = engine.environment.get_state("sms")
        assert len(sms_state.conversations) == 0

    def test_undo_restores_complete_chat_state(self, client_with_engine):
        """Test that undo fully restores chat state.
        
        Verifies:
        - Chat message is added
        - Undo removes message and restores conversation state
        """
        client, engine = client_with_engine
        
        # Send chat messages
        client.post("/chat/send", json={"content": "First message", "role": "user"})
        client.post("/chat/send", json={"content": "Second message", "role": "user"})
        
        # Verify messages
        chat_state = engine.environment.get_state("chat")
        assert len(chat_state.messages) == 2
        
        # Undo second message
        client.post("/simulation/undo")
        
        # Verify only first message remains
        chat_state = engine.environment.get_state("chat")
        assert len(chat_state.messages) == 1

    def test_undo_restores_calendar_state(self, client_with_engine):
        """Test that undo fully restores calendar state.
        
        Verifies:
        - Calendar event is created
        - Undo removes event
        """
        client, engine = client_with_engine
        
        # Create a calendar event (uses 'start' and 'end', not 'start_time'/'end_time')
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
        
        # Verify event exists
        cal_state = engine.environment.get_state("calendar")
        assert len(cal_state.events) == 1
        
        # Undo
        client.post("/simulation/undo")
        
        # Verify event is removed
        cal_state = engine.environment.get_state("calendar")
        assert len(cal_state.events) == 0

    def test_undo_restores_weather_state(self, client_with_engine):
        """Test that undo fully restores weather state.
        
        Verifies:
        - Weather report is added
        - Undo removes weather report
        """
        client, engine = client_with_engine
        
        # Add weather report (requires full WeatherReport format with all fields)
        import time
        current_unix = int(time.time())
        response = client.post(
            "/weather/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "report": {
                    "lat": 40.7128,
                    "lon": -74.0060,
                    "timezone": "America/New_York",
                    "timezone_offset": -18000,
                    "current": {
                        "dt": current_unix,
                        "sunrise": current_unix - 3600,
                        "sunset": current_unix + 36000,
                        "temp": 72.0,
                        "feels_like": 70.0,
                        "pressure": 1013,
                        "humidity": 45,
                        "dew_point": 55.0,
                        "uvi": 5.0,
                        "clouds": 10,
                        "visibility": 10000,
                        "wind_speed": 5.0,
                        "wind_deg": 180,
                        "weather": [
                            {
                                "id": 800,
                                "main": "Clear",
                                "description": "clear sky",
                                "icon": "01d",
                            }
                        ],
                    },
                },
            },
        )
        assert response.status_code == 200, f"Failed to update weather: {response.json()}"
        
        # Verify weather exists
        weather_state = engine.environment.get_state("weather")
        assert len(weather_state.locations) == 1
        
        # Undo
        client.post("/simulation/undo")
        
        # Verify weather is removed
        weather_state = engine.environment.get_state("weather")
        assert len(weather_state.locations) == 0
