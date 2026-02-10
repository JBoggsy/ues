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

from ues.api.auth import initialize_api_key_registry, shutdown_api_key_registry
from ues.api.dependencies import initialize_simulation_engine, shutdown_simulation_engine
from ues.client import (
    AsyncUESClient,
    UESClient,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from ues.client._http import HTTPClient
from ues.main import app


# Module-level variable to store the admin API key secret
_admin_api_key: str | None = None


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def setup_simulation_engine():
    """Initialize the simulation engine and API key registry before each test.
    
    This fixture runs automatically for all tests in this module.
    It initializes the simulation engine and API key registry before each test
    and shuts them down afterwards to ensure clean state.
    """
    global _admin_api_key
    initialize_simulation_engine()
    _admin_api_key, _ = initialize_api_key_registry()
    yield
    shutdown_api_key_registry()
    shutdown_simulation_engine()
    _admin_api_key = None


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
    with UESClient(
        base_url="http://test",
        transport=transport,
        api_key=_admin_api_key,
    ) as client:
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
    async with AsyncUESClient(
        base_url="http://test",
        transport=transport,
        api_key=_admin_api_key,
    ) as client:
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

    def test_get_modality_state_via_modality_client(self, sync_client):
        """Test getting a specific modality's state via the modality client.
        
        Note: The /environment/modalities/{modality} endpoint was removed.
        Use the modality-specific clients instead (e.g., client.email.get_state()).
        """
        sync_client.simulation.start()
        
        # Use the email-specific client to get state
        state = sync_client.email.get_state()
        assert state.user_email_address is not None

    def test_invalid_endpoint_returns_404(self, sync_client):
        """Test that accessing an invalid endpoint raises NotFoundError.
        
        Note: The /environment/modalities/{modality} endpoint was removed.
        Invalid modality names now simply result in 404 from the router.
        """
        sync_client.simulation.start()
        
        # Accessing a non-existent endpoint should raise NotFoundError
        with pytest.raises(NotFoundError):
            sync_client._http.get("/nonexistent_modality/state")


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
        # Check event via typed CalendarEvent model
        events_list = list(state.events.values())
        assert len(events_list) == 1
        assert events_list[0].title == "Test Meeting"

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
        assert state.events[event_id].title == "Updated Title"

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
# Sub-Model & Field Value Integration Tests (Phase 5.3)
# =============================================================================


class TestEmailSubModelIntegration:
    """Integration tests exercising email sub-models and field value assertions."""

    def test_send_email_with_attachments(self, sync_client):
        """Verify email attachments round-trip through the API."""
        sync_client.simulation.start()

        sync_client.email.send(
            from_address="user@example.com",
            to_addresses=["recipient@example.com"],
            subject="With Attachments",
            body_text="See attached files.",
            attachments=[
                {
                    "filename": "report.pdf",
                    "size": 102400,
                    "mime_type": "application/pdf",
                },
                {
                    "filename": "photo.jpg",
                    "size": 2048000,
                    "mime_type": "image/jpeg",
                    "content_id": "cid-photo-001",
                },
            ],
        )

        state = sync_client.email.get_state()
        email = list(state.emails.values())[0]
        assert email.subject == "With Attachments"
        assert len(email.attachments) == 2

        # Assert individual attachment field values
        filenames = {a.filename for a in email.attachments}
        assert filenames == {"report.pdf", "photo.jpg"}

        pdf = next(a for a in email.attachments if a.filename == "report.pdf")
        assert pdf.size == 102400
        assert pdf.mime_type == "application/pdf"

        jpg = next(a for a in email.attachments if a.filename == "photo.jpg")
        assert jpg.size == 2048000
        assert jpg.content_id == "cid-photo-001"

    def test_receive_email_with_all_fields(self, sync_client):
        """Verify all email fields round-trip, including optional ones."""
        sync_client.simulation.start()

        sync_client.email.receive(
            from_address="alice@example.com",
            to_addresses=["user@example.com"],
            cc_addresses=["cc@example.com"],
            bcc_addresses=["bcc@example.com"],
            reply_to_address="reply@example.com",
            subject="Full Email",
            body_text="Plain text body",
            body_html="<p>HTML body</p>",
            priority="high",
        )

        state = sync_client.email.get_state()
        email = list(state.emails.values())[0]
        assert email.from_address == "alice@example.com"
        assert email.to_addresses == ["user@example.com"]
        assert email.cc_addresses == ["cc@example.com"]
        assert email.bcc_addresses == ["bcc@example.com"]
        assert email.reply_to_address == "reply@example.com"
        assert email.body_text == "Plain text body"
        assert email.body_html == "<p>HTML body</p>"
        assert email.priority == "high"
        assert email.folder == "inbox"
        assert email.is_read is False
        assert email.is_starred is False

    def test_email_thread_fields(self, sync_client):
        """Verify thread-level fields after sending and replying."""
        sync_client.simulation.start()

        # Send initial email
        sync_client.email.receive(
            from_address="alice@example.com",
            to_addresses=["user@example.com"],
            subject="Thread Test",
            body_text="First message",
        )

        state = sync_client.email.get_state()
        first_email = list(state.emails.values())[0]
        thread_id = first_email.thread_id

        # Reply in the same thread
        sync_client.email.send(
            from_address="user@example.com",
            to_addresses=["alice@example.com"],
            subject="Re: Thread Test",
            body_text="Reply message",
            thread_id=thread_id,
            in_reply_to=first_email.message_id,
        )

        state = sync_client.email.get_state()
        assert len(state.threads) >= 1
        thread = state.threads[thread_id]
        assert thread.message_count >= 2
        assert thread.subject is not None


class TestSMSSubModelIntegration:
    """Integration tests exercising SMS sub-models and field value assertions."""

    def test_send_sms_with_attachments(self, sync_client):
        """Verify SMS attachments round-trip through the API."""
        sync_client.simulation.start()

        sync_client.sms.send(
            from_number="+15551234567",
            to_numbers=["+15559876543"],
            body="Check this photo",
            attachments=[
                {
                    "filename": "vacation.jpg",
                    "size": 3072000,
                    "mime_type": "image/jpeg",
                    "thumbnail_url": "https://example.com/thumb.jpg",
                },
            ],
        )

        state = sync_client.sms.get_state()
        message = list(state.messages.values())[0]
        assert message.body == "Check this photo"
        assert len(message.attachments) == 1
        assert message.attachments[0].filename == "vacation.jpg"
        assert message.attachments[0].size == 3072000
        assert message.attachments[0].mime_type == "image/jpeg"

    def test_sms_reaction(self, sync_client):
        """Verify SMS reaction fields round-trip through the API."""
        sync_client.simulation.start()

        sync_client.sms.receive(
            from_number="+15559876543",
            to_numbers=["+15551234567"],
            body="Did you see the game?",
        )

        state = sync_client.sms.get_state()
        message_id = list(state.messages.keys())[0]

        sync_client.sms.react(
            message_id=message_id,
            phone_number="+15551234567",
            emoji="👍",
        )

        state = sync_client.sms.get_state()
        message = state.messages[message_id]
        assert len(message.reactions) == 1
        assert message.reactions[0].emoji == "👍"
        assert message.reactions[0].phone_number == "+15551234567"
        assert message.reactions[0].message_id == message_id

    def test_sms_field_values(self, sync_client):
        """Verify all SMS message fields including direction and type."""
        sync_client.simulation.start()

        # Get the simulated user's phone number so direction is set correctly
        state = sync_client.sms.get_state()
        user_phone = state.user_phone_number

        sync_client.sms.send(
            from_number=user_phone,
            to_numbers=["+15559876543"],
            body="RCS message",
            message_type="rcs",
        )

        state = sync_client.sms.get_state()
        message = list(state.messages.values())[0]
        assert message.from_number == user_phone
        assert message.to_numbers == ["+15559876543"]
        assert message.body == "RCS message"
        assert message.message_type == "rcs"
        assert message.direction == "outgoing"

    def test_sms_conversation_fields(self, sync_client):
        """Verify conversation metadata fields."""
        sync_client.simulation.start()

        sync_client.sms.send(
            from_number="+15551234567",
            to_numbers=["+15559876543"],
            body="First message",
        )
        sync_client.sms.receive(
            from_number="+15559876543",
            to_numbers=["+15551234567"],
            body="Reply",
        )

        state = sync_client.sms.get_state()
        assert state.total_conversation_count >= 1
        conv = list(state.conversations.values())[0]
        assert conv.message_count >= 2
        assert conv.thread_id is not None


class TestCalendarSubModelIntegration:
    """Integration tests exercising calendar sub-models."""

    def test_create_event_with_attendees(self, sync_client):
        """Verify attendee fields round-trip through the API."""
        sync_client.simulation.start()

        start = datetime(2025, 7, 1, 9, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 7, 1, 10, 0, 0, tzinfo=timezone.utc)

        sync_client.calendar.create(
            title="Meeting with Attendees",
            start=start,
            end=end,
            attendees=[
                {
                    "email": "alice@example.com",
                    "display_name": "Alice",
                    "optional": False,
                    "response": "accepted",
                },
                {
                    "email": "bob@example.com",
                    "display_name": "Bob",
                    "optional": True,
                    "response": "tentative",
                    "comment": "Might be late",
                },
            ],
        )

        state = sync_client.calendar.get_state()
        event = list(state.events.values())[0]
        assert event.title == "Meeting with Attendees"
        assert len(event.attendees) == 2

        emails = {a.email for a in event.attendees}
        assert emails == {"alice@example.com", "bob@example.com"}

        bob = next(a for a in event.attendees if a.email == "bob@example.com")
        assert bob.display_name == "Bob"
        assert bob.optional is True
        assert bob.response == "tentative"
        assert bob.comment == "Might be late"

    def test_create_event_with_recurrence(self, sync_client):
        """Verify recurrence rule fields round-trip through the API."""
        sync_client.simulation.start()

        start = datetime(2025, 7, 1, 9, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 7, 1, 10, 0, 0, tzinfo=timezone.utc)

        sync_client.calendar.create(
            title="Weekly Standup",
            start=start,
            end=end,
            recurrence={
                "frequency": "weekly",
                "interval": 1,
                "days_of_week": ["monday", "wednesday", "friday"],
                "end_type": "count",
                "count": 12,
            },
        )

        state = sync_client.calendar.get_state()
        event = list(state.events.values())[0]
        assert event.recurrence is not None
        assert event.recurrence.frequency == "weekly"
        assert event.recurrence.interval == 1
        assert event.recurrence.days_of_week == [
            "monday", "wednesday", "friday",
        ]
        assert event.recurrence.end_type == "count"
        assert event.recurrence.count == 12

    def test_create_event_with_reminders(self, sync_client):
        """Verify reminder fields round-trip through the API."""
        sync_client.simulation.start()

        start = datetime(2025, 7, 1, 14, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 7, 1, 15, 0, 0, tzinfo=timezone.utc)

        sync_client.calendar.create(
            title="Reminded Event",
            start=start,
            end=end,
            reminders=[
                {"minutes_before": 15, "type": "notification"},
                {"minutes_before": 60, "type": "email"},
            ],
        )

        state = sync_client.calendar.get_state()
        event = list(state.events.values())[0]
        assert len(event.reminders) == 2

        mins = {r.minutes_before for r in event.reminders}
        assert mins == {15, 60}

        email_reminder = next(
            r for r in event.reminders if r.type == "email"
        )
        assert email_reminder.minutes_before == 60

    def test_create_event_with_attachments(self, sync_client):
        """Verify calendar event attachment fields round-trip."""
        sync_client.simulation.start()

        start = datetime(2025, 7, 1, 14, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 7, 1, 15, 0, 0, tzinfo=timezone.utc)

        sync_client.calendar.create(
            title="Event with Files",
            start=start,
            end=end,
            attachments=[
                {
                    "filename": "agenda.pdf",
                    "size": 10240,
                    "mime_type": "application/pdf",
                    "url": "https://files.example.com/agenda.pdf",
                },
            ],
        )

        state = sync_client.calendar.get_state()
        event = list(state.events.values())[0]
        assert len(event.attachments) == 1
        assert event.attachments[0].filename == "agenda.pdf"
        assert event.attachments[0].size == 10240
        assert event.attachments[0].mime_type == "application/pdf"
        assert event.attachments[0].url == "https://files.example.com/agenda.pdf"

    def test_create_event_all_fields(self, sync_client):
        """Verify all CalendarEvent fields persist through the API."""
        sync_client.simulation.start()

        start = datetime(2025, 8, 1, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 8, 1, 12, 0, 0, tzinfo=timezone.utc)

        sync_client.calendar.create(
            title="Full Event",
            start=start,
            end=end,
            description="Detailed description",
            all_day=False,
            timezone="America/New_York",
            location="Conference Room A",
            status="confirmed",
            organizer="manager@example.com",
            color="#dc2626",
            visibility="private",
            transparency="opaque",
            conference_link="https://meet.example.com/room",
        )

        state = sync_client.calendar.get_state()
        event = list(state.events.values())[0]
        assert event.title == "Full Event"
        assert event.description == "Detailed description"
        assert event.all_day is False
        assert event.timezone == "America/New_York"
        assert event.location == "Conference Room A"
        assert event.status == "confirmed"
        assert event.organizer == "manager@example.com"
        assert event.color == "#dc2626"
        assert event.visibility == "private"
        assert event.transparency == "opaque"
        assert event.conference_link == "https://meet.example.com/room"
        assert event.created_at is not None
        assert event.updated_at is not None

    def test_calendar_container_fields(self, sync_client):
        """Verify calendar container fields from get_state()."""
        sync_client.simulation.start()

        state = sync_client.calendar.get_state()
        # Default "primary" calendar should exist
        assert "primary" in state.calendars
        cal = state.calendars["primary"]
        assert cal.calendar_id == "primary"
        assert cal.name is not None
        assert cal.visible is True
        assert cal.created_at is not None


class TestChatSubModelIntegration:
    """Integration tests exercising chat sub-models."""

    def test_send_with_metadata(self, sync_client):
        """Verify metadata dict round-trips through the API."""
        sync_client.simulation.start()

        sync_client.chat.send(
            role="assistant",
            content="Here's the answer.",
            metadata={
                "model": "gpt-4",
                "token_count": 42,
                "latency_ms": 150.5,
            },
        )

        state = sync_client.chat.get_state()
        msg = state.messages[0]
        assert msg.role == "assistant"
        assert msg.content == "Here's the answer."
        assert msg.metadata is not None
        assert msg.metadata["model"] == "gpt-4"
        assert msg.metadata["token_count"] == 42
        assert msg.metadata["latency_ms"] == 150.5

    def test_send_multimodal_content(self, sync_client):
        """Verify multimodal (list) content round-trips through the API."""
        sync_client.simulation.start()

        sync_client.chat.send(
            role="user",
            content=[
                {"type": "text", "text": "What's in this image?"},
                {"type": "image_url", "url": "https://example.com/photo.jpg"},
            ],
        )

        state = sync_client.chat.get_state()
        msg = state.messages[0]
        assert msg.role == "user"
        assert isinstance(msg.content, list)
        assert len(msg.content) == 2
        assert msg.content[0]["type"] == "text"
        assert msg.content[0]["text"] == "What's in this image?"
        assert msg.content[1]["type"] == "image_url"

    def test_conversation_metadata_fields(self, sync_client):
        """Verify conversation metadata in query response."""
        sync_client.simulation.start()

        sync_client.chat.send(role="user", content="Hello")
        sync_client.chat.send(role="assistant", content="Hi there!")

        result = sync_client.chat.query()
        assert result.total_count == 2
        assert len(result.messages) == 2
        # Verify message fields are populated
        for msg in result.messages:
            assert msg.message_id is not None
            assert msg.conversation_id is not None
            assert msg.role in ("user", "assistant")
            assert msg.content is not None


class TestWeatherSubModelIntegration:
    """Integration tests exercising weather sub-models and nested field values."""

    def _build_full_weather_report(self) -> dict:
        """Build a full weather report dict with all sub-models."""
        import time
        now = int(time.time())
        return {
            "lat": 40.7128,
            "lon": -74.0060,
            "timezone": "America/New_York",
            "timezone_offset": -18000,
            "current": {
                "dt": now,
                "sunrise": now - 21600,
                "sunset": now + 21600,
                "temp": 295.5,
                "feels_like": 296.0,
                "pressure": 1013,
                "humidity": 65,
                "dew_point": 288.0,
                "uvi": 5.0,
                "clouds": 40,
                "visibility": 10000,
                "wind_speed": 5.5,
                "wind_deg": 180,
                "wind_gust": 8.2,
                "weather": [
                    {
                        "id": 802,
                        "main": "Clouds",
                        "description": "scattered clouds",
                        "icon": "03d",
                    }
                ],
            },
            "minutely": [
                {"dt": now + i * 60, "precipitation": 0.0}
                for i in range(3)
            ],
            "hourly": [
                {
                    "dt": now + i * 3600,
                    "temp": 295.0 + i,
                    "feels_like": 293.0 + i,
                    "pressure": 1013,
                    "humidity": 60 + i,
                    "dew_point": 287.0,
                    "uvi": max(0, 5.0 - i),
                    "clouds": 40,
                    "visibility": 10000,
                    "wind_speed": 4.0 + i * 0.5,
                    "wind_deg": 180,
                    "weather": [
                        {
                            "id": 802,
                            "main": "Clouds",
                            "description": "scattered clouds",
                            "icon": "03d",
                        }
                    ],
                    "pop": 0.1 * i,
                }
                for i in range(3)
            ],
            "daily": [
                {
                    "dt": now + i * 86400,
                    "sunrise": now + i * 86400 - 21600,
                    "sunset": now + i * 86400 + 21600,
                    "moonrise": now + i * 86400 - 10800,
                    "moonset": now + i * 86400 + 32400,
                    "moon_phase": 0.25 * i,
                    "summary": f"Day {i} forecast",
                    "temp": {
                        "day": 295.0,
                        "min": 288.0,
                        "max": 300.0,
                        "night": 290.0,
                        "eve": 293.0,
                        "morn": 289.0,
                    },
                    "feels_like": {
                        "day": 293.0,
                        "night": 288.0,
                        "eve": 291.0,
                        "morn": 287.0,
                    },
                    "pressure": 1013,
                    "humidity": 55,
                    "dew_point": 284.0,
                    "wind_speed": 4.0,
                    "wind_deg": 200,
                    "weather": [
                        {
                            "id": 800,
                            "main": "Clear",
                            "description": "clear sky",
                            "icon": "01d",
                        }
                    ],
                    "clouds": 10,
                    "pop": 0.05,
                    "uvi": 7.0,
                }
                for i in range(2)
            ],
            "alerts": [
                {
                    "sender_name": "National Weather Service",
                    "event": "Heat Advisory",
                    "start": now,
                    "end": now + 86400,
                    "description": "High temperatures expected.",
                    "tags": ["Heat", "Extreme"],
                },
            ],
        }

    def test_weather_current_nested_fields(self, sync_client):
        """Verify current weather nested fields round-trip."""
        sync_client.simulation.start()

        report = self._build_full_weather_report()
        sync_client.weather.update(
            latitude=40.7128, longitude=-74.0060, report=report,
        )

        result = sync_client.weather.query(lat=40.7128, lon=-74.0060)
        assert result.count >= 1

        weather_report = result.reports[0]
        assert weather_report.current is not None
        assert weather_report.current.temp == 295.5
        assert weather_report.current.humidity == 65
        assert weather_report.current.wind_speed == 5.5
        assert weather_report.current.wind_gust == 8.2
        assert len(weather_report.current.weather) == 1
        assert weather_report.current.weather[0].main == "Clouds"
        assert weather_report.current.weather[0].description == "scattered clouds"
        assert weather_report.current.weather[0].icon == "03d"

    def test_weather_hourly_nested_fields(self, sync_client):
        """Verify hourly forecast nested fields round-trip."""
        sync_client.simulation.start()

        report = self._build_full_weather_report()
        sync_client.weather.update(
            latitude=40.7128, longitude=-74.0060, report=report,
        )

        result = sync_client.weather.query(lat=40.7128, lon=-74.0060)
        weather_report = result.reports[0]
        assert weather_report.hourly is not None
        assert len(weather_report.hourly) == 3
        # First hour
        assert weather_report.hourly[0].temp == 295.0
        assert weather_report.hourly[0].pop == 0.0
        # Second hour has incremented values
        assert weather_report.hourly[1].temp == 296.0
        assert weather_report.hourly[1].humidity == 61

    def test_weather_daily_nested_fields(self, sync_client):
        """Verify daily forecast nested temp/feels_like round-trip."""
        sync_client.simulation.start()

        report = self._build_full_weather_report()
        sync_client.weather.update(
            latitude=40.7128, longitude=-74.0060, report=report,
        )

        result = sync_client.weather.query(lat=40.7128, lon=-74.0060)
        weather_report = result.reports[0]
        assert weather_report.daily is not None
        assert len(weather_report.daily) == 2

        day0 = weather_report.daily[0]
        assert day0.temp.day == 295.0
        assert day0.temp.min == 288.0
        assert day0.temp.max == 300.0
        assert day0.feels_like.day == 293.0
        assert day0.feels_like.night == 288.0
        assert day0.summary == "Day 0 forecast"

    def test_weather_alerts_nested_fields(self, sync_client):
        """Verify weather alert nested fields round-trip."""
        sync_client.simulation.start()

        report = self._build_full_weather_report()
        sync_client.weather.update(
            latitude=40.7128, longitude=-74.0060, report=report,
        )

        result = sync_client.weather.query(lat=40.7128, lon=-74.0060)
        weather_report = result.reports[0]
        assert weather_report.alerts is not None
        assert len(weather_report.alerts) == 1
        assert weather_report.alerts[0].sender_name == "National Weather Service"
        assert weather_report.alerts[0].event == "Heat Advisory"
        assert weather_report.alerts[0].tags == ["Heat", "Extreme"]

    def test_weather_minutely_fields(self, sync_client):
        """Verify minutely forecast round-trips."""
        sync_client.simulation.start()

        report = self._build_full_weather_report()
        sync_client.weather.update(
            latitude=40.7128, longitude=-74.0060, report=report,
        )

        result = sync_client.weather.query(lat=40.7128, lon=-74.0060)
        weather_report = result.reports[0]
        assert weather_report.minutely is not None
        assert len(weather_report.minutely) == 3
        assert weather_report.minutely[0].precipitation == 0.0


class TestLocationSubModelIntegration:
    """Integration tests exercising location field values."""

    def test_location_all_fields(self, sync_client):
        """Verify all location fields round-trip through the API."""
        sync_client.simulation.start()

        sync_client.location.update(
            latitude=40.7128,
            longitude=-74.0060,
            address="350 5th Ave, New York, NY",
            named_location="Empire State Building",
            altitude=443.0,
            accuracy=5.0,
            speed=0.0,
            bearing=90.0,
        )

        state = sync_client.location.get_state()
        assert abs(state.current["latitude"] - 40.7128) < 0.001
        assert abs(state.current["longitude"] - (-74.0060)) < 0.001
        assert state.current["address"] == "350 5th Ave, New York, NY"
        assert state.current["named_location"] == "Empire State Building"
        assert state.current["altitude"] == 443.0
        assert state.current["accuracy"] == 5.0
        assert state.current["speed"] == 0.0
        assert state.current["bearing"] == 90.0

    def test_location_history_field_values(self, sync_client):
        """Verify location history entries have correct field values."""
        sync_client.simulation.start()

        sync_client.location.update(
            latitude=40.7128, longitude=-74.0060,
            named_location="NYC",
        )
        sync_client.location.update(
            latitude=34.0522, longitude=-118.2437,
            named_location="LA",
        )

        result = sync_client.location.query()
        assert result.total_count >= 2
        # Verify entries have location data
        for entry in result.locations:
            assert "latitude" in entry
            assert "longitude" in entry


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

    def test_not_found_error_on_invalid_endpoint(self, sync_client):
        """Test that accessing invalid endpoint raises NotFoundError.
        
        Note: The /environment/modalities/{modality} endpoint was removed.
        This test verifies that invalid routes return 404.
        """
        sync_client.simulation.start()
        
        with pytest.raises(NotFoundError):
            sync_client._http.get("/fake_modality/state")


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
