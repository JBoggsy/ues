"""Integration tests for UES API client library.

These tests run against a real UES server instance using FastAPI's TestClient
and httpx's ASGITransport for async tests. This provides true end-to-end
testing of the client library against the actual API implementation.

To run these tests:
    uv run pytest tests/client/test_integration.py -v

Note: These tests use pytest-asyncio for async test support and create
a fresh simulation state for each test to ensure isolation.
"""

from datetime import datetime, timedelta, timezone

import httpx
import pytest
from httpx import ASGITransport

from api.dependencies import initialize_simulation_engine, shutdown_simulation_engine
from client import (
    AsyncUESClient,
    UESClient,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from client._http import HTTPClient
from main import app


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def setup_simulation_engine():
    """Initialize the simulation engine before each test.
    
    This fixture runs automatically for all tests in this module.
    It initializes the simulation engine before each test and shuts it
    down afterwards to ensure clean state.
    """
    initialize_simulation_engine()
    yield
    shutdown_simulation_engine()


@pytest.fixture
def sync_client():
    """Create a synchronous UES client connected to the test app.
    
    Uses httpx's built-in MockTransport for sync testing. The TestClient
    approach from FastAPI/Starlette wraps the ASGI app for synchronous use.
    """
    # Use httpx Client directly with a custom transport that uses TestClient
    from starlette.testclient import TestClient
    
    test_client = TestClient(app, raise_server_exceptions=False)
    
    # Create a custom transport that wraps TestClient
    class SyncTestTransport(httpx.BaseTransport):
        def handle_request(self, request: httpx.Request) -> httpx.Response:
            # Convert httpx request to TestClient request
            response = test_client.request(
                method=request.method,
                url=str(request.url.path),
                params=dict(request.url.params) if request.url.params else None,
                content=request.content,
                headers=dict(request.headers),
            )
            return httpx.Response(
                status_code=response.status_code,
                headers=response.headers,
                content=response.content,
            )
    
    transport = SyncTestTransport()
    with UESClient(base_url="http://test", transport=transport) as client:
        yield client
        # Clean up after test
        try:
            client.simulation.stop()
        except ConflictError:
            pass  # Already stopped


@pytest.fixture
async def async_client():
    """Create an asynchronous UES client connected to the test app.
    
    Uses httpx's ASGITransport to connect directly to the FastAPI app
    without needing an external server process.
    """
    transport = ASGITransport(app=app)
    async with AsyncUESClient(base_url="http://test", transport=transport) as client:
        yield client
        # Clean up after test
        try:
            await client.simulation.stop()
        except ConflictError:
            pass  # Already stopped


# =============================================================================
# Simulation Control Tests
# =============================================================================


class TestSimulationIntegration:
    """Integration tests for simulation control."""

    def test_start_and_stop(self, sync_client):
        """Test starting and stopping the simulation."""
        # Start simulation
        result = sync_client.simulation.start()
        assert result.status == "running"
        
        # Verify running
        status = sync_client.simulation.status()
        assert status.is_running is True
        
        # Stop simulation
        result = sync_client.simulation.stop()
        assert result.status == "stopped"
        
        # Verify stopped
        status = sync_client.simulation.status()
        assert status.is_running is False

    def test_start_twice_raises_conflict(self, sync_client):
        """Test that starting an already running simulation raises ConflictError."""
        sync_client.simulation.start()
        
        with pytest.raises(ConflictError):
            sync_client.simulation.start()

    def test_reset_clears_state(self, sync_client):
        """Test that reset clears all simulation state."""
        sync_client.simulation.start()
        
        # Add some data
        sync_client.email.send(
            from_address="user@example.com",
            to_addresses=["recipient@example.com"],
            subject="Test",
            body_text="Test body",
        )
        
        # Verify email exists
        state = sync_client.email.get_state()
        assert state.total_email_count == 1
        
        # Reset
        sync_client.simulation.reset()
        
        # Verify email state is cleared
        sync_client.simulation.start()
        state = sync_client.email.get_state()
        assert state.total_email_count == 0

    def test_undo_and_redo(self, sync_client):
        """Test undo and redo functionality."""
        sync_client.simulation.start()
        
        # Send an email
        sync_client.email.send(
            from_address="user@example.com",
            to_addresses=["recipient@example.com"],
            subject="Test",
            body_text="Test body",
        )
        
        # Verify email exists
        state = sync_client.email.get_state()
        assert state.total_email_count == 1
        
        # Undo
        sync_client.simulation.undo()
        
        # Verify email is gone
        state = sync_client.email.get_state()
        assert state.total_email_count == 0
        
        # Redo
        sync_client.simulation.redo()
        
        # Verify email is back
        state = sync_client.email.get_state()
        assert state.total_email_count == 1


class TestAsyncSimulationIntegration:
    """Async integration tests for simulation control."""

    async def test_start_and_stop(self, async_client):
        """Test starting and stopping the simulation asynchronously."""
        result = await async_client.simulation.start()
        assert result.status == "running"
        
        status = await async_client.simulation.status()
        assert status.is_running is True
        
        result = await async_client.simulation.stop()
        assert result.status == "stopped"


# =============================================================================
# Time Control Tests
# =============================================================================


class TestTimeIntegration:
    """Integration tests for time control."""

    def test_get_time_state(self, sync_client):
        """Test getting the current simulator time state."""
        sync_client.simulation.start()
        
        state = sync_client.time.get_state()
        assert state.current_time is not None
        assert state.is_paused is False

    def test_advance_time(self, sync_client):
        """Test advancing simulator time."""
        sync_client.simulation.start()
        
        # Get initial time
        initial = sync_client.time.get_state()
        initial_time = initial.current_time
        
        # Advance by 1 hour
        result = sync_client.time.advance(seconds=3600)
        assert result.events_executed >= 0
        
        # Verify time advanced
        state = sync_client.time.get_state()
        assert state.current_time > initial_time

    def test_set_time(self, sync_client):
        """Test setting simulator time to a specific value."""
        sync_client.simulation.start()
        
        # Get current time first, then set to a future time
        current = sync_client.time.get_state()
        # Set to 1 hour in the future from current time
        target_time = current.current_time + timedelta(hours=1)
        result = sync_client.time.set(target_time=target_time)
        
        # Verify time was set (compare as string ISO format to avoid timezone issues)
        state = sync_client.time.get_state()
        assert state.current_time >= target_time

    def test_pause_and_resume(self, sync_client):
        """Test pausing and resuming time."""
        sync_client.simulation.start()
        
        # Pause
        result = sync_client.time.pause()
        assert result.is_paused is True
        
        # Verify paused
        state = sync_client.time.get_state()
        assert state.is_paused is True
        
        # Resume
        result = sync_client.time.resume()
        assert result.is_paused is False

    def test_set_time_scale(self, sync_client):
        """Test setting time scale."""
        sync_client.simulation.start()
        
        result = sync_client.time.set_scale(scale=2.0)
        assert result.time_scale == 2.0


# =============================================================================
# Events Tests
# =============================================================================


class TestEventsIntegration:
    """Integration tests for event management."""

    def test_create_and_get_event(self, sync_client):
        """Test creating and retrieving an event."""
        sync_client.simulation.start()
        
        # Get current time for scheduling
        time_state = sync_client.time.get_state()
        scheduled_time = time_state.current_time + timedelta(hours=1)
        
        # Create an event
        result = sync_client.events.create(
            scheduled_time=scheduled_time,
            modality="email",
            data={
                "operation": "receive",
                "from_address": "sender@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Scheduled Email",
                "body_text": "This email was scheduled.",
            },
        )
        
        event_id = result.event_id
        assert event_id is not None
        
        # Retrieve the event
        event = sync_client.events.get(event_id)
        assert event.event_id == event_id
        assert event.modality == "email"
        assert event.status == "pending"

    def test_list_events(self, sync_client):
        """Test listing events with filters."""
        sync_client.simulation.start()
        
        time_state = sync_client.time.get_state()
        scheduled_time = time_state.current_time + timedelta(hours=1)
        
        # Create multiple events
        sync_client.events.create(
            scheduled_time=scheduled_time,
            modality="email",
            data={"operation": "receive", "from_address": "a@example.com", 
                  "to_addresses": ["user@example.com"], "subject": "Email 1", "body_text": "Body 1"},
        )
        sync_client.events.create(
            scheduled_time=scheduled_time + timedelta(hours=1),
            modality="sms",
            data={"action": "receive_message", "message_data": {
                "from_number": "+1234567890",
                "to_numbers": ["+0987654321"], 
                "body": "SMS 1",
                "conversation_id": None,
            }},
        )
        
        # List all events
        result = sync_client.events.list_events()
        assert result.total >= 2
        
        # List only email events
        email_events = sync_client.events.list_events(modality="email")
        assert all(e.modality == "email" for e in email_events.events)

    def test_cancel_event(self, sync_client):
        """Test cancelling an event."""
        sync_client.simulation.start()
        
        time_state = sync_client.time.get_state()
        scheduled_time = time_state.current_time + timedelta(hours=1)
        
        result = sync_client.events.create(
            scheduled_time=scheduled_time,
            modality="email",
            data={"operation": "receive", "from_address": "sender@example.com",
                  "to_addresses": ["user@example.com"], "subject": "Test", "body_text": "Test"},
        )
        
        event_id = result.event_id
        
        # Cancel the event
        cancel_result = sync_client.events.cancel(event_id)
        assert cancel_result.cancelled is True
        
        # Verify cancelled
        event = sync_client.events.get(event_id)
        assert event.status == "cancelled"

    def test_event_summary(self, sync_client):
        """Test getting event summary."""
        sync_client.simulation.start()
        
        summary = sync_client.events.summary()
        assert hasattr(summary, "total")
        assert hasattr(summary, "pending")


# =============================================================================
# Environment Tests
# =============================================================================


class TestEnvironmentIntegration:
    """Integration tests for environment state."""

    def test_get_environment_state(self, sync_client):
        """Test getting overall environment state."""
        sync_client.simulation.start()
        
        state = sync_client.environment.get_state()
        assert state.modalities is not None
        assert "email" in state.modalities
        assert "sms" in state.modalities

    def test_list_modalities(self, sync_client):
        """Test listing available modalities."""
        sync_client.simulation.start()
        
        result = sync_client.environment.list_modalities()
        assert "email" in result.modalities
        assert "sms" in result.modalities
        assert "chat" in result.modalities
        assert "calendar" in result.modalities
        assert "location" in result.modalities
        assert "weather" in result.modalities

    def test_get_modality_state(self, sync_client):
        """Test getting a specific modality's state."""
        sync_client.simulation.start()
        
        state = sync_client.environment.get_modality("email")
        assert state.modality_type == "email"

    def test_get_unknown_modality_raises_not_found(self, sync_client):
        """Test that getting unknown modality raises NotFoundError."""
        sync_client.simulation.start()
        
        with pytest.raises(NotFoundError):
            sync_client.environment.get_modality("unknown_modality")


# =============================================================================
# Email Modality Tests
# =============================================================================


class TestEmailIntegration:
    """Integration tests for email modality."""

    def test_send_email(self, sync_client):
        """Test sending an email."""
        sync_client.simulation.start()
        
        result = sync_client.email.send(
            from_address="user@example.com",
            to_addresses=["recipient@example.com"],
            subject="Test Email",
            body_text="This is a test email.",
        )
        
        assert result.status == "executed"
        assert result.modality == "email"
        
        # Verify email appears in state
        state = sync_client.email.get_state()
        assert state.total_email_count == 1
        # Check the email exists and has correct folder
        emails_list = list(state.emails.values())
        assert len(emails_list) == 1
        assert emails_list[0].subject == "Test Email"
        assert emails_list[0].folder == "sent"

    def test_receive_email(self, sync_client):
        """Test receiving an email."""
        sync_client.simulation.start()
        
        result = sync_client.email.receive(
            from_address="sender@example.com",
            to_addresses=["user@example.com"],
            subject="Incoming Email",
            body_text="You've got mail!",
        )
        
        assert result.status == "executed"
        
        # Verify email appears in inbox
        state = sync_client.email.get_state()
        assert state.total_email_count == 1
        emails_list = list(state.emails.values())
        assert emails_list[0].subject == "Incoming Email"
        assert emails_list[0].folder == "inbox"
        assert emails_list[0].is_read is False

    def test_read_and_unread_email(self, sync_client):
        """Test marking emails as read and unread."""
        sync_client.simulation.start()
        
        # Receive an email
        sync_client.email.receive(
            from_address="sender@example.com",
            to_addresses=["user@example.com"],
            subject="Test",
            body_text="Test body",
        )
        
        state = sync_client.email.get_state()
        message_id = list(state.emails.keys())[0]
        
        # Mark as read
        sync_client.email.read(message_ids=[message_id])
        
        state = sync_client.email.get_state()
        assert state.emails[message_id].is_read is True
        
        # Mark as unread
        sync_client.email.unread(message_ids=[message_id])
        
        state = sync_client.email.get_state()
        assert state.emails[message_id].is_read is False

    def test_star_and_unstar_email(self, sync_client):
        """Test starring and unstarring emails."""
        sync_client.simulation.start()
        
        sync_client.email.receive(
            from_address="sender@example.com",
            to_addresses=["user@example.com"],
            subject="Test",
            body_text="Test body",
        )
        
        state = sync_client.email.get_state()
        message_id = list(state.emails.keys())[0]
        
        # Star
        sync_client.email.star(message_ids=[message_id])
        
        state = sync_client.email.get_state()
        assert state.emails[message_id].is_starred is True
        
        # Unstar
        sync_client.email.unstar(message_ids=[message_id])
        
        state = sync_client.email.get_state()
        assert state.emails[message_id].is_starred is False

    def test_delete_email(self, sync_client):
        """Test deleting an email."""
        sync_client.simulation.start()
        
        sync_client.email.receive(
            from_address="sender@example.com",
            to_addresses=["user@example.com"],
            subject="Test",
            body_text="Test body",
        )
        
        state = sync_client.email.get_state()
        message_id = list(state.emails.keys())[0]
        
        # Delete
        sync_client.email.delete(message_ids=[message_id])
        
        # Verify moved to trash
        state = sync_client.email.get_state()
        assert state.emails[message_id].folder == "trash"

    def test_query_emails(self, sync_client):
        """Test querying emails with filters."""
        sync_client.simulation.start()
        
        # Receive multiple emails
        sync_client.email.receive(
            from_address="alice@example.com",
            to_addresses=["user@example.com"],
            subject="From Alice",
            body_text="Hello from Alice",
        )
        sync_client.email.receive(
            from_address="bob@example.com",
            to_addresses=["user@example.com"],
            subject="From Bob",
            body_text="Hello from Bob",
        )
        
        # Query for emails from Alice
        result = sync_client.email.query(from_address="alice@example.com")
        assert result.total_count == 1
        assert result.emails[0].from_address == "alice@example.com"

    def test_email_labels(self, sync_client):
        """Test adding and removing labels."""
        sync_client.simulation.start()
        
        sync_client.email.receive(
            from_address="sender@example.com",
            to_addresses=["user@example.com"],
            subject="Test",
            body_text="Test body",
        )
        
        state = sync_client.email.get_state()
        message_id = list(state.emails.keys())[0]
        
        # Add label
        sync_client.email.label(message_ids=[message_id], labels=["important"])
        
        state = sync_client.email.get_state()
        assert "important" in state.emails[message_id].labels
        
        # Remove label
        sync_client.email.unlabel(message_ids=[message_id], labels=["important"])
        
        state = sync_client.email.get_state()
        assert "important" not in state.emails[message_id].labels


# =============================================================================
# SMS Modality Tests
# =============================================================================


class TestSMSIntegration:
    """Integration tests for SMS modality."""

    def test_send_sms(self, sync_client):
        """Test sending an SMS."""
        sync_client.simulation.start()
        
        result = sync_client.sms.send(
            from_number="+1234567890",
            to_numbers=["+0987654321"],
            body="Hello via SMS!",
        )
        
        assert result.status == "executed"
        assert result.modality == "sms"
        
        # Verify message exists
        state = sync_client.sms.get_state()
        assert state.total_message_count == 1
        assert state.total_conversation_count == 1

    def test_receive_sms(self, sync_client):
        """Test receiving an SMS."""
        sync_client.simulation.start()
        
        result = sync_client.sms.receive(
            from_number="+0987654321",
            to_numbers=["+1234567890"],
            body="Incoming SMS!",
        )
        
        assert result.status == "executed"
        
        # Verify message received
        state = sync_client.sms.get_state()
        assert state.total_message_count == 1

    def test_read_sms(self, sync_client):
        """Test marking SMS as read."""
        sync_client.simulation.start()
        
        sync_client.sms.receive(
            from_number="+0987654321",
            to_numbers=["+1234567890"],
            body="Test message",
        )
        
        state = sync_client.sms.get_state()
        message_id = list(state.messages.keys())[0]
        
        # Mark as read
        sync_client.sms.read(message_ids=[message_id])
        
        state = sync_client.sms.get_state()
        assert state.messages[message_id].is_read is True

    def test_query_sms(self, sync_client):
        """Test querying SMS messages."""
        sync_client.simulation.start()
        
        sync_client.sms.receive(
            from_number="+1111111111",
            to_numbers=["+1234567890"],
            body="Message 1",
        )
        sync_client.sms.receive(
            from_number="+2222222222",
            to_numbers=["+1234567890"],
            body="Message 2",
        )
        
        # Query all
        result = sync_client.sms.query()
        assert result.total_count >= 2


# =============================================================================
# Chat Modality Tests
# =============================================================================


class TestChatIntegration:
    """Integration tests for chat modality."""

    def test_send_user_message(self, sync_client):
        """Test sending a user message."""
        sync_client.simulation.start()
        
        result = sync_client.chat.send(
            role="user",
            content="Hello, assistant!",
        )
        
        assert result.status == "executed"
        
        # Verify message exists
        state = sync_client.chat.get_state()
        assert state.total_message_count == 1
        assert len(state.messages) == 1
        assert state.messages[0].role == "user"
        assert state.messages[0].content == "Hello, assistant!"

    def test_send_assistant_message(self, sync_client):
        """Test sending an assistant message."""
        sync_client.simulation.start()
        
        result = sync_client.chat.send(
            role="assistant",
            content="Hello, user! How can I help?",
        )
        
        assert result.status == "executed"
        
        state = sync_client.chat.get_state()
        assert state.messages[0].role == "assistant"

    def test_chat_conversation_flow(self, sync_client):
        """Test a multi-turn conversation."""
        sync_client.simulation.start()
        
        sync_client.chat.send(role="user", content="What's the weather?")
        sync_client.chat.send(role="assistant", content="It's sunny today!")
        sync_client.chat.send(role="user", content="Thanks!")
        
        state = sync_client.chat.get_state()
        assert state.total_message_count == 3
        
        # Verify all messages exist (don't rely on specific order)
        contents = [m.content for m in state.messages]
        assert "What's the weather?" in contents
        assert "It's sunny today!" in contents
        assert "Thanks!" in contents

    def test_delete_message(self, sync_client):
        """Test deleting a chat message."""
        sync_client.simulation.start()
        
        sync_client.chat.send(role="user", content="Test message")
        
        state = sync_client.chat.get_state()
        message_id = state.messages[0].message_id
        
        sync_client.chat.delete(message_id=message_id)
        
        state = sync_client.chat.get_state()
        assert state.total_message_count == 0

    def test_clear_conversation(self, sync_client):
        """Test clearing a conversation."""
        sync_client.simulation.start()
        
        sync_client.chat.send(role="user", content="Message 1")
        sync_client.chat.send(role="assistant", content="Message 2")
        
        sync_client.chat.clear()
        
        state = sync_client.chat.get_state()
        assert state.total_message_count == 0

    def test_query_chat(self, sync_client):
        """Test querying chat messages."""
        sync_client.simulation.start()
        
        sync_client.chat.send(role="user", content="User message")
        sync_client.chat.send(role="assistant", content="Assistant reply")
        
        # Query only user messages
        result = sync_client.chat.query(role="user")
        assert result.total_count == 1
        assert result.messages[0].role == "user"


# =============================================================================
# Calendar Modality Tests
# =============================================================================


class TestCalendarIntegration:
    """Integration tests for calendar modality."""

    def test_create_event(self, sync_client):
        """Test creating a calendar event."""
        sync_client.simulation.start()
        
        start = datetime(2025, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 6, 15, 11, 0, 0, tzinfo=timezone.utc)
        
        result = sync_client.calendar.create(
            title="Test Meeting",
            start=start,
            end=end,
            description="A test meeting",
        )
        
        assert result.status == "executed"
        
        # Verify event exists
        state = sync_client.calendar.get_state()
        assert state.event_count == 1
        # Check event via dict
        events_list = list(state.events.values())
        assert len(events_list) == 1
        assert events_list[0]["title"] == "Test Meeting"

    def test_update_event(self, sync_client):
        """Test updating a calendar event."""
        sync_client.simulation.start()
        
        start = datetime(2025, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 6, 15, 11, 0, 0, tzinfo=timezone.utc)
        
        sync_client.calendar.create(
            title="Original Title",
            start=start,
            end=end,
        )
        
        state = sync_client.calendar.get_state()
        event_id = list(state.events.keys())[0]
        
        # Update the title
        sync_client.calendar.update(
            event_id=event_id,
            title="Updated Title",
        )
        
        state = sync_client.calendar.get_state()
        assert state.events[event_id]["title"] == "Updated Title"

    def test_delete_event(self, sync_client):
        """Test deleting a calendar event."""
        sync_client.simulation.start()
        
        start = datetime(2025, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 6, 15, 11, 0, 0, tzinfo=timezone.utc)
        
        sync_client.calendar.create(
            title="To Delete",
            start=start,
            end=end,
        )
        
        state = sync_client.calendar.get_state()
        event_id = list(state.events.keys())[0]
        
        sync_client.calendar.delete(event_id=event_id)
        
        state = sync_client.calendar.get_state()
        assert state.event_count == 0

    def test_query_calendar(self, sync_client):
        """Test querying calendar events."""
        sync_client.simulation.start()
        
        # Create events on different days
        sync_client.calendar.create(
            title="Event 1",
            start=datetime(2025, 6, 15, 10, 0, 0, tzinfo=timezone.utc),
            end=datetime(2025, 6, 15, 11, 0, 0, tzinfo=timezone.utc),
        )
        sync_client.calendar.create(
            title="Event 2",
            start=datetime(2025, 6, 16, 10, 0, 0, tzinfo=timezone.utc),
            end=datetime(2025, 6, 16, 11, 0, 0, tzinfo=timezone.utc),
        )
        
        # Query all
        result = sync_client.calendar.query()
        assert result.total_count == 2


# =============================================================================
# Location Modality Tests
# =============================================================================


class TestLocationIntegration:
    """Integration tests for location modality."""

    def test_get_location_state(self, sync_client):
        """Test getting location state."""
        sync_client.simulation.start()
        
        state = sync_client.location.get_state()
        assert state.modality_type == "location"
        assert state.current is not None

    def test_update_location(self, sync_client):
        """Test updating location."""
        sync_client.simulation.start()
        
        result = sync_client.location.update(
            latitude=40.7128,
            longitude=-74.0060,
            address="New York, NY",
            named_location="NYC Office",
        )
        
        assert result.status == "executed"
        
        # Verify location updated
        state = sync_client.location.get_state()
        assert abs(state.current["latitude"] - 40.7128) < 0.001
        assert abs(state.current["longitude"] - (-74.0060)) < 0.001

    def test_location_history(self, sync_client):
        """Test location history tracking."""
        sync_client.simulation.start()
        
        # Update location multiple times
        sync_client.location.update(latitude=40.7128, longitude=-74.0060)
        sync_client.location.update(latitude=34.0522, longitude=-118.2437)
        sync_client.location.update(latitude=41.8781, longitude=-87.6298)
        
        # Query history
        result = sync_client.location.query()
        assert result.total_count >= 3


# =============================================================================
# Weather Modality Tests
# =============================================================================


class TestWeatherIntegration:
    """Integration tests for weather modality."""

    def _get_sample_weather_report(self, lat: float, lon: float) -> dict:
        """Create a complete weather report with all required fields."""
        import time
        current_time = int(time.time())
        return {
            "lat": lat,
            "lon": lon,
            "timezone": "America/New_York",
            "timezone_offset": -18000,
            "current": {
                "dt": current_time,
                "sunrise": current_time - 21600,  # 6 hours ago
                "sunset": current_time + 21600,   # 6 hours from now
                "temp": 295.5,  # ~72°F in Kelvin
                "feels_like": 296.0,
                "pressure": 1013,
                "humidity": 65,
                "dew_point": 288.0,
                "uvi": 5.0,
                "clouds": 40,
                "visibility": 10000,
                "wind_speed": 5.5,
                "wind_deg": 180,
                "weather": [
                    {"id": 802, "main": "Clouds", "description": "partly cloudy", "icon": "03d"}
                ],
            },
        }

    def test_get_weather_state(self, sync_client):
        """Test getting weather state."""
        sync_client.simulation.start()
        
        state = sync_client.weather.get_state()
        assert state.modality_type == "weather"

    def test_update_weather(self, sync_client):
        """Test updating weather data."""
        sync_client.simulation.start()
        
        result = sync_client.weather.update(
            latitude=40.7128,
            longitude=-74.0060,
            report=self._get_sample_weather_report(40.7128, -74.0060),
        )
        
        assert result.status == "executed"
        
        # Verify weather was stored
        state = sync_client.weather.get_state()
        assert state.location_count >= 1

    def test_query_weather(self, sync_client):
        """Test querying weather data."""
        sync_client.simulation.start()
        
        # First update weather
        sync_client.weather.update(
            latitude=40.7128,
            longitude=-74.0060,
            report=self._get_sample_weather_report(40.7128, -74.0060),
        )
        
        # Query
        result = sync_client.weather.query(lat=40.7128, lon=-74.0060)
        assert result.count >= 1


# =============================================================================
# Cross-Modality Workflow Tests
# =============================================================================


class TestCrossModalityWorkflows:
    """Integration tests for workflows involving multiple modalities."""

    def test_email_notification_workflow(self, sync_client):
        """Test a workflow: receive email, check calendar, respond."""
        sync_client.simulation.start()
        
        # Create a calendar event
        start = datetime(2025, 6, 15, 14, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 6, 15, 15, 0, 0, tzinfo=timezone.utc)
        sync_client.calendar.create(
            title="Meeting with Bob",
            start=start,
            end=end,
        )
        
        # Receive an email about scheduling
        sync_client.email.receive(
            from_address="bob@example.com",
            to_addresses=["user@example.com"],
            subject="Can we meet?",
            body_text="Are you free at 2pm?",
        )
        
        # Send a reply
        sync_client.email.send(
            from_address="user@example.com",
            to_addresses=["bob@example.com"],
            subject="Re: Can we meet?",
            body_text="Yes, I have it on my calendar!",
        )
        
        # Verify both emails exist
        email_state = sync_client.email.get_state()
        assert email_state.total_email_count == 2
        
        # Verify calendar event
        cal_state = sync_client.calendar.get_state()
        assert cal_state.event_count == 1

    def test_location_weather_workflow(self, sync_client):
        """Test workflow: update location, check weather."""
        sync_client.simulation.start()
        
        # Update location to NYC
        sync_client.location.update(
            latitude=40.7128,
            longitude=-74.0060,
            named_location="New York City",
        )
        
        # Set weather for that location (with complete report)
        import time
        current_time = int(time.time())
        sync_client.weather.update(
            latitude=40.7128,
            longitude=-74.0060,
            report={
                "lat": 40.7128,
                "lon": -74.0060,
                "timezone": "America/New_York",
                "timezone_offset": -18000,
                "current": {
                    "dt": current_time,
                    "sunrise": current_time - 21600,
                    "sunset": current_time + 21600,
                    "temp": 297.0,
                    "feels_like": 297.5,
                    "pressure": 1015,
                    "humidity": 50,
                    "dew_point": 286.0,
                    "uvi": 6.0,
                    "clouds": 10,
                    "visibility": 10000,
                    "wind_speed": 3.0,
                    "wind_deg": 90,
                    "weather": [{"id": 800, "main": "Clear", "description": "sunny", "icon": "01d"}],
                },
            },
        )
        
        # Verify both states
        loc_state = sync_client.location.get_state()
        assert loc_state.current["named_location"] == "New York City"
        
        weather_state = sync_client.weather.get_state()
        assert weather_state.location_count >= 1

    def test_scheduled_events_workflow(self, sync_client):
        """Test scheduling events and advancing time to execute them."""
        sync_client.simulation.start()
        
        # Get current time
        time_state = sync_client.time.get_state()
        future_time = time_state.current_time + timedelta(minutes=30)
        
        # Schedule an email to arrive in 30 minutes
        sync_client.events.create(
            scheduled_time=future_time,
            modality="email",
            data={
                "operation": "receive",
                "from_address": "scheduled@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Scheduled Email",
                "body_text": "This was scheduled!",
            },
        )
        
        # Verify email not yet received
        email_state = sync_client.email.get_state()
        initial_count = email_state.total_email_count
        
        # Advance time past the scheduled event
        result = sync_client.time.advance(seconds=1800)  # 30 minutes
        assert result.events_executed >= 1
        
        # Verify email now received
        email_state = sync_client.email.get_state()
        assert email_state.total_email_count > initial_count


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Integration tests for error handling."""

    def test_conflict_error_on_duplicate_start(self, sync_client):
        """Test that starting twice raises ConflictError."""
        sync_client.simulation.start()
        
        with pytest.raises(ConflictError):
            sync_client.simulation.start()

    def test_not_found_error_on_missing_event(self, sync_client):
        """Test that getting non-existent event raises NotFoundError."""
        sync_client.simulation.start()
        
        with pytest.raises(NotFoundError):
            sync_client.events.get("non-existent-event-id")

    def test_not_found_error_on_unknown_modality(self, sync_client):
        """Test that querying unknown modality raises NotFoundError."""
        sync_client.simulation.start()
        
        with pytest.raises(NotFoundError):
            sync_client.environment.get_modality("unknown_modality")


# =============================================================================
# Async Modality Tests
# =============================================================================


class TestAsyncModalities:
    """Async integration tests for modality operations."""

    async def test_async_email_workflow(self, async_client):
        """Test async email operations."""
        await async_client.simulation.start()
        
        # Send email
        result = await async_client.email.send(
            from_address="user@example.com",
            to_addresses=["recipient@example.com"],
            subject="Async Test",
            body_text="Sent asynchronously!",
        )
        assert result.status == "executed"
        
        # Get state
        state = await async_client.email.get_state()
        assert state.total_email_count == 1

    async def test_async_chat_workflow(self, async_client):
        """Test async chat operations."""
        await async_client.simulation.start()
        
        await async_client.chat.send(role="user", content="Hello async!")
        await async_client.chat.send(role="assistant", content="Hi there!")
        
        state = await async_client.chat.get_state()
        assert state.total_message_count == 2

    async def test_async_calendar_workflow(self, async_client):
        """Test async calendar operations."""
        await async_client.simulation.start()
        
        start = datetime(2025, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 6, 15, 11, 0, 0, tzinfo=timezone.utc)
        
        await async_client.calendar.create(
            title="Async Meeting",
            start=start,
            end=end,
        )
        
        state = await async_client.calendar.get_state()
        assert state.event_count == 1
