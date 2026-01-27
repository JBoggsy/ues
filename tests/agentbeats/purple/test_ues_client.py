"""Tests for TrackedAsyncUESClient and related tracking infrastructure.

This module tests the automatic action tracking functionality provided by
ues_client.py, ensuring that write operations are tracked while read
operations are not.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agentbeats.purple.context import AssessmentContext
from agentbeats.purple.ues_client import (
    TrackedAsyncUESClient,
    TrackedCalendarClient,
    TrackedChatClient,
    TrackedEmailClient,
    TrackedLocationClient,
    TrackedSMSClient,
    TrackedSubClient,
    TrackedWeatherClient,
    _CALENDAR_ACTIONS,
    _CHAT_ACTIONS,
    _EMAIL_ACTIONS,
    _LOCATION_ACTIONS,
    _SMS_ACTIONS,
    _WEATHER_ACTIONS,
    _create_tracking_wrapper,
    create_tracked_client,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_time() -> datetime:
    """Provide a sample datetime for tests."""
    return datetime(2026, 1, 22, 9, 0, tzinfo=timezone.utc)


@pytest.fixture
def context(sample_time: datetime) -> AssessmentContext:
    """Create a fresh AssessmentContext for testing."""
    return AssessmentContext(
        assessment_id="test-001",
        ues_url="http://localhost:8000",
        api_key="test-key",
        current_time=sample_time,
    )


@pytest.fixture
def mock_async_client() -> MagicMock:
    """Create a mock AsyncUESClient with all sub-clients."""
    mock = MagicMock()
    
    # Email sub-client with action methods
    mock.email = MagicMock()
    mock.email.send = AsyncMock(return_value={"success": True})
    mock.email.read = AsyncMock(return_value={"success": True})
    mock.email.unread = AsyncMock(return_value={"success": True})
    mock.email.star = AsyncMock(return_value={"success": True})
    mock.email.unstar = AsyncMock(return_value={"success": True})
    mock.email.archive = AsyncMock(return_value={"success": True})
    mock.email.delete = AsyncMock(return_value={"success": True})
    mock.email.move = AsyncMock(return_value={"success": True})
    mock.email.add_label = AsyncMock(return_value={"success": True})
    mock.email.remove_label = AsyncMock(return_value={"success": True})
    mock.email.get_state = AsyncMock(return_value={"emails": []})
    mock.email.query = AsyncMock(return_value={"emails": []})
    
    # SMS sub-client
    mock.sms = MagicMock()
    mock.sms.send = AsyncMock(return_value={"success": True})
    mock.sms.read = AsyncMock(return_value={"success": True})
    mock.sms.unread = AsyncMock(return_value={"success": True})
    mock.sms.delete = AsyncMock(return_value={"success": True})
    mock.sms.react = AsyncMock(return_value={"success": True})
    mock.sms.get_state = AsyncMock(return_value={"messages": []})
    mock.sms.query = AsyncMock(return_value={"messages": []})
    
    # Chat sub-client
    mock.chat = MagicMock()
    mock.chat.send = AsyncMock(return_value={"success": True})
    mock.chat.delete = AsyncMock(return_value={"success": True})
    mock.chat.clear = AsyncMock(return_value={"success": True})
    mock.chat.get_state = AsyncMock(return_value={"messages": []})
    mock.chat.query = AsyncMock(return_value={"messages": []})
    
    # Calendar sub-client
    mock.calendar = MagicMock()
    mock.calendar.create = AsyncMock(return_value={"success": True})
    mock.calendar.update = AsyncMock(return_value={"success": True})
    mock.calendar.delete = AsyncMock(return_value={"success": True})
    mock.calendar.rsvp = AsyncMock(return_value={"success": True})
    mock.calendar.get_state = AsyncMock(return_value={"events": []})
    mock.calendar.query = AsyncMock(return_value={"events": []})
    
    # Location sub-client
    mock.location = MagicMock()
    mock.location.update = AsyncMock(return_value={"success": True})
    mock.location.get_state = AsyncMock(return_value={"location": None})
    mock.location.query = AsyncMock(return_value={"history": []})
    
    # Weather sub-client
    mock.weather = MagicMock()
    mock.weather.update = AsyncMock(return_value={"success": True})
    mock.weather.get_state = AsyncMock(return_value={"conditions": []})
    mock.weather.query = AsyncMock(return_value={"conditions": []})
    
    # Time sub-client (read-only)
    mock.time = MagicMock()
    mock.time.get_state = AsyncMock(return_value={"current_time": "2026-01-22T09:00:00Z"})
    
    # Context manager methods
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=None)
    mock.close = AsyncMock()
    
    return mock


# =============================================================================
# TestActionSets - Verify action method sets are correct
# =============================================================================


class TestActionSets:
    """Tests for the action method sets."""

    def test_email_actions_contains_write_methods(self):
        """Email actions should contain all write methods."""
        expected = {
            "send", "read", "unread", "star", "unstar",
            "archive", "delete", "move", "add_label", "remove_label",
        }
        assert _EMAIL_ACTIONS == expected

    def test_sms_actions_contains_write_methods(self):
        """SMS actions should contain all write methods."""
        expected = {"send", "read", "unread", "delete", "react"}
        assert _SMS_ACTIONS == expected

    def test_chat_actions_contains_write_methods(self):
        """Chat actions should contain all write methods."""
        expected = {"send", "delete", "clear"}
        assert _CHAT_ACTIONS == expected

    def test_calendar_actions_contains_write_methods(self):
        """Calendar actions should contain all write methods."""
        expected = {"create", "update", "delete", "rsvp"}
        assert _CALENDAR_ACTIONS == expected

    def test_location_actions_contains_write_methods(self):
        """Location actions should contain update method."""
        expected = {"update"}
        assert _LOCATION_ACTIONS == expected

    def test_weather_actions_contains_write_methods(self):
        """Weather actions should contain update method."""
        expected = {"update"}
        assert _WEATHER_ACTIONS == expected

    def test_action_sets_are_frozen(self):
        """Action sets should be immutable."""
        assert isinstance(_EMAIL_ACTIONS, frozenset)
        assert isinstance(_SMS_ACTIONS, frozenset)
        assert isinstance(_CHAT_ACTIONS, frozenset)
        assert isinstance(_CALENDAR_ACTIONS, frozenset)
        assert isinstance(_LOCATION_ACTIONS, frozenset)
        assert isinstance(_WEATHER_ACTIONS, frozenset)


# =============================================================================
# TestTrackingWrapper - Tests for _create_tracking_wrapper
# =============================================================================


class TestTrackingWrapper:
    """Tests for the tracking wrapper function."""

    @pytest.mark.asyncio
    async def test_wrapper_calls_original_method(self, context: AssessmentContext):
        """Wrapper should call the original method."""
        mock_method = AsyncMock(return_value="result")
        wrapped = _create_tracking_wrapper(mock_method, context)

        result = await wrapped("arg1", kwarg="value")

        mock_method.assert_called_once_with("arg1", kwarg="value")
        assert result == "result"

    @pytest.mark.asyncio
    async def test_wrapper_records_action(self, context: AssessmentContext):
        """Wrapper should record action after successful call."""
        mock_method = AsyncMock(return_value="result")
        wrapped = _create_tracking_wrapper(mock_method, context)

        assert context.actions_this_turn == 0
        await wrapped()
        assert context.actions_this_turn == 1

    @pytest.mark.asyncio
    async def test_wrapper_records_multiple_actions(self, context: AssessmentContext):
        """Wrapper should record each call separately."""
        mock_method = AsyncMock(return_value="result")
        wrapped = _create_tracking_wrapper(mock_method, context)

        await wrapped()
        await wrapped()
        await wrapped()

        assert context.actions_this_turn == 3
        assert context.total_actions == 3

    @pytest.mark.asyncio
    async def test_wrapper_preserves_function_name(self, context: AssessmentContext):
        """Wrapper should preserve original function metadata."""
        async def my_custom_method():
            """My docstring."""
            return "result"

        wrapped = _create_tracking_wrapper(my_custom_method, context)

        assert wrapped.__name__ == "my_custom_method"
        assert wrapped.__doc__ == "My docstring."


# =============================================================================
# TestTrackedSubClient - Tests for TrackedSubClient base class
# =============================================================================


class TestTrackedSubClient:
    """Tests for the TrackedSubClient base class."""

    @pytest.mark.asyncio
    async def test_action_method_is_wrapped(self, context: AssessmentContext):
        """Action methods should be wrapped for tracking."""
        mock_wrapped = MagicMock()
        mock_wrapped.do_action = AsyncMock(return_value="result")

        sub_client = TrackedSubClient(
            mock_wrapped, context, frozenset({"do_action"})
        )

        result = await sub_client.do_action()

        assert result == "result"
        assert context.actions_this_turn == 1

    @pytest.mark.asyncio
    async def test_non_action_method_not_wrapped(self, context: AssessmentContext):
        """Non-action methods should NOT be wrapped."""
        mock_wrapped = MagicMock()
        mock_wrapped.read_only = AsyncMock(return_value="data")

        sub_client = TrackedSubClient(
            mock_wrapped, context, frozenset({"do_action"})
        )

        result = await sub_client.read_only()

        assert result == "data"
        assert context.actions_this_turn == 0  # Not tracked

    def test_non_callable_attributes_passed_through(self, context: AssessmentContext):
        """Non-callable attributes should be returned unchanged."""
        mock_wrapped = MagicMock()
        mock_wrapped.some_property = "value"

        sub_client = TrackedSubClient(mock_wrapped, context, frozenset())

        assert sub_client.some_property == "value"


# =============================================================================
# TestTrackedEmailClient - Tests for email tracking
# =============================================================================


class TestTrackedEmailClient:
    """Tests for TrackedEmailClient tracking behavior."""

    @pytest.mark.asyncio
    async def test_send_is_tracked(
        self, context: AssessmentContext, mock_async_client: MagicMock
    ):
        """Email send should be tracked."""
        tracked = TrackedEmailClient(mock_async_client.email, context)

        await tracked.send(
            from_address="me@test.com",
            to_addresses=["you@test.com"],
            subject="Test",
            body_text="Hello",
        )

        assert context.actions_this_turn == 1

    @pytest.mark.asyncio
    async def test_read_is_tracked(
        self, context: AssessmentContext, mock_async_client: MagicMock
    ):
        """Email read (mark as read) should be tracked."""
        tracked = TrackedEmailClient(mock_async_client.email, context)

        await tracked.read(["msg-1"])

        assert context.actions_this_turn == 1

    @pytest.mark.asyncio
    async def test_archive_is_tracked(
        self, context: AssessmentContext, mock_async_client: MagicMock
    ):
        """Email archive should be tracked."""
        tracked = TrackedEmailClient(mock_async_client.email, context)

        await tracked.archive(["msg-1", "msg-2"])

        assert context.actions_this_turn == 1

    @pytest.mark.asyncio
    async def test_get_state_not_tracked(
        self, context: AssessmentContext, mock_async_client: MagicMock
    ):
        """Email get_state should NOT be tracked (read-only)."""
        tracked = TrackedEmailClient(mock_async_client.email, context)

        await tracked.get_state()

        assert context.actions_this_turn == 0

    @pytest.mark.asyncio
    async def test_query_not_tracked(
        self, context: AssessmentContext, mock_async_client: MagicMock
    ):
        """Email query should NOT be tracked (read-only)."""
        tracked = TrackedEmailClient(mock_async_client.email, context)

        await tracked.query()

        assert context.actions_this_turn == 0

    @pytest.mark.asyncio
    async def test_all_email_actions_tracked(
        self, context: AssessmentContext, mock_async_client: MagicMock
    ):
        """All email action methods should be tracked."""
        tracked = TrackedEmailClient(mock_async_client.email, context)

        await tracked.send(
            from_address="a@b.com",
            to_addresses=["c@d.com"],
            subject="S",
            body_text="B",
        )
        await tracked.read(["1"])
        await tracked.unread(["1"])
        await tracked.star(["1"])
        await tracked.unstar(["1"])
        await tracked.archive(["1"])
        await tracked.delete(["1"])
        await tracked.move(["1"], "folder")
        await tracked.add_label(["1"], "label")
        await tracked.remove_label(["1"], "label")

        assert context.actions_this_turn == 10


# =============================================================================
# TestTrackedSMSClient - Tests for SMS tracking
# =============================================================================


class TestTrackedSMSClient:
    """Tests for TrackedSMSClient tracking behavior."""

    @pytest.mark.asyncio
    async def test_send_is_tracked(
        self, context: AssessmentContext, mock_async_client: MagicMock
    ):
        """SMS send should be tracked."""
        tracked = TrackedSMSClient(mock_async_client.sms, context)

        await tracked.send(to_number="+1234567890", content="Hello")

        assert context.actions_this_turn == 1

    @pytest.mark.asyncio
    async def test_get_state_not_tracked(
        self, context: AssessmentContext, mock_async_client: MagicMock
    ):
        """SMS get_state should NOT be tracked."""
        tracked = TrackedSMSClient(mock_async_client.sms, context)

        await tracked.get_state()

        assert context.actions_this_turn == 0

    @pytest.mark.asyncio
    async def test_all_sms_actions_tracked(
        self, context: AssessmentContext, mock_async_client: MagicMock
    ):
        """All SMS action methods should be tracked."""
        tracked = TrackedSMSClient(mock_async_client.sms, context)

        await tracked.send(to_number="+1", content="Hi")
        await tracked.read(["1"])
        await tracked.unread(["1"])
        await tracked.delete(["1"])
        await tracked.react("1", "👍")

        assert context.actions_this_turn == 5


# =============================================================================
# TestTrackedChatClient - Tests for chat tracking
# =============================================================================


class TestTrackedChatClient:
    """Tests for TrackedChatClient tracking behavior."""

    @pytest.mark.asyncio
    async def test_send_is_tracked(
        self, context: AssessmentContext, mock_async_client: MagicMock
    ):
        """Chat send should be tracked."""
        tracked = TrackedChatClient(mock_async_client.chat, context)

        await tracked.send(content="Hello", role="assistant")

        assert context.actions_this_turn == 1

    @pytest.mark.asyncio
    async def test_get_state_not_tracked(
        self, context: AssessmentContext, mock_async_client: MagicMock
    ):
        """Chat get_state should NOT be tracked."""
        tracked = TrackedChatClient(mock_async_client.chat, context)

        await tracked.get_state()

        assert context.actions_this_turn == 0


# =============================================================================
# TestTrackedCalendarClient - Tests for calendar tracking
# =============================================================================


class TestTrackedCalendarClient:
    """Tests for TrackedCalendarClient tracking behavior."""

    @pytest.mark.asyncio
    async def test_create_is_tracked(
        self, context: AssessmentContext, mock_async_client: MagicMock
    ):
        """Calendar create should be tracked."""
        tracked = TrackedCalendarClient(mock_async_client.calendar, context)

        await tracked.create(title="Meeting", start="2026-01-22T10:00:00Z")

        assert context.actions_this_turn == 1

    @pytest.mark.asyncio
    async def test_get_state_not_tracked(
        self, context: AssessmentContext, mock_async_client: MagicMock
    ):
        """Calendar get_state should NOT be tracked."""
        tracked = TrackedCalendarClient(mock_async_client.calendar, context)

        await tracked.get_state()

        assert context.actions_this_turn == 0


# =============================================================================
# TestTrackedLocationClient - Tests for location tracking
# =============================================================================


class TestTrackedLocationClient:
    """Tests for TrackedLocationClient tracking behavior."""

    @pytest.mark.asyncio
    async def test_update_is_tracked(
        self, context: AssessmentContext, mock_async_client: MagicMock
    ):
        """Location update should be tracked."""
        tracked = TrackedLocationClient(mock_async_client.location, context)

        await tracked.update(latitude=37.7749, longitude=-122.4194)

        assert context.actions_this_turn == 1

    @pytest.mark.asyncio
    async def test_get_state_not_tracked(
        self, context: AssessmentContext, mock_async_client: MagicMock
    ):
        """Location get_state should NOT be tracked."""
        tracked = TrackedLocationClient(mock_async_client.location, context)

        await tracked.get_state()

        assert context.actions_this_turn == 0


# =============================================================================
# TestTrackedWeatherClient - Tests for weather tracking
# =============================================================================


class TestTrackedWeatherClient:
    """Tests for TrackedWeatherClient tracking behavior."""

    @pytest.mark.asyncio
    async def test_update_is_tracked(
        self, context: AssessmentContext, mock_async_client: MagicMock
    ):
        """Weather update should be tracked."""
        tracked = TrackedWeatherClient(mock_async_client.weather, context)

        await tracked.update(location="NYC", temperature=72)

        assert context.actions_this_turn == 1

    @pytest.mark.asyncio
    async def test_get_state_not_tracked(
        self, context: AssessmentContext, mock_async_client: MagicMock
    ):
        """Weather get_state should NOT be tracked."""
        tracked = TrackedWeatherClient(mock_async_client.weather, context)

        await tracked.get_state()

        assert context.actions_this_turn == 0


# =============================================================================
# TestTrackedAsyncUESClient - Tests for the main client wrapper
# =============================================================================


class TestTrackedAsyncUESClient:
    """Tests for TrackedAsyncUESClient."""

    def test_initialization(self, context: AssessmentContext):
        """Client should initialize with context."""
        with patch("agentbeats.purple.ues_client.AsyncUESClient"):
            client = TrackedAsyncUESClient(context)

            assert client._context is context

    def test_sub_clients_lazily_initialized(self, context: AssessmentContext):
        """Sub-clients should be lazily initialized."""
        with patch("agentbeats.purple.ues_client.AsyncUESClient") as mock_cls:
            mock_cls.return_value = MagicMock()
            client = TrackedAsyncUESClient(context)

            # Before access
            assert client._email is None
            assert client._sms is None
            assert client._chat is None
            assert client._calendar is None
            assert client._location is None
            assert client._weather is None

            # After access (triggers creation)
            _ = client.email
            assert client._email is not None

    def test_email_property_returns_tracked_client(self, context: AssessmentContext):
        """email property should return TrackedEmailClient."""
        with patch("agentbeats.purple.ues_client.AsyncUESClient") as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance
            client = TrackedAsyncUESClient(context)

            email_client = client.email

            assert isinstance(email_client, TrackedEmailClient)

    def test_same_sub_client_returned_on_repeated_access(
        self, context: AssessmentContext
    ):
        """Same sub-client instance should be returned on repeated access."""
        with patch("agentbeats.purple.ues_client.AsyncUESClient") as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance
            client = TrackedAsyncUESClient(context)

            email1 = client.email
            email2 = client.email

            assert email1 is email2

    def test_time_property_returns_untracked(self, context: AssessmentContext):
        """time property should return untracked client (read-only)."""
        with patch("agentbeats.purple.ues_client.AsyncUESClient") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.time = MagicMock()
            mock_cls.return_value = mock_instance
            client = TrackedAsyncUESClient(context)

            time_client = client.time

            # Should be the raw client, not wrapped
            assert time_client is mock_instance.time

    @pytest.mark.asyncio
    async def test_context_manager_enter(self, context: AssessmentContext):
        """Async context manager should return self on enter."""
        with patch("agentbeats.purple.ues_client.AsyncUESClient") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_cls.return_value = mock_instance

            client = TrackedAsyncUESClient(context)
            result = await client.__aenter__()

            assert result is client
            mock_instance.__aenter__.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_exit(self, context: AssessmentContext):
        """Async context manager should close underlying client on exit."""
        with patch("agentbeats.purple.ues_client.AsyncUESClient") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_cls.return_value = mock_instance

            client = TrackedAsyncUESClient(context)
            await client.__aenter__()
            await client.__aexit__(None, None, None)

            mock_instance.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_method(self, context: AssessmentContext):
        """close() should close the underlying client."""
        with patch("agentbeats.purple.ues_client.AsyncUESClient") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.close = AsyncMock()
            mock_cls.return_value = mock_instance

            client = TrackedAsyncUESClient(context)
            await client.close()

            mock_instance.close.assert_called_once()


# =============================================================================
# TestCreateTrackedClient - Tests for the factory function
# =============================================================================


class TestCreateTrackedClient:
    """Tests for the create_tracked_client factory function."""

    def test_creates_tracked_client(self, context: AssessmentContext):
        """Factory should create TrackedAsyncUESClient."""
        with patch("agentbeats.purple.ues_client.AsyncUESClient"):
            client = create_tracked_client(context)

            assert isinstance(client, TrackedAsyncUESClient)
            assert client._context is context

    def test_uses_context_url_and_key(self, context: AssessmentContext):
        """Factory should pass context URL and key to client."""
        with patch("agentbeats.purple.ues_client.AsyncUESClient") as mock_cls:
            create_tracked_client(context)

            mock_cls.assert_called_once_with(
                base_url=context.ues_url,
                api_key=context.api_key,
            )


# =============================================================================
# TestIntegrationTracking - End-to-end tracking tests
# =============================================================================


class TestIntegrationTracking:
    """Integration tests for action tracking across operations."""

    @pytest.mark.asyncio
    async def test_mixed_operations_track_correctly(
        self, context: AssessmentContext, mock_async_client: MagicMock
    ):
        """Mix of read and write operations should track correctly."""
        with patch(
            "agentbeats.purple.ues_client.AsyncUESClient",
            return_value=mock_async_client,
        ):
            async with TrackedAsyncUESClient(context) as ues:
                # Read - not tracked
                await ues.email.get_state()
                assert context.actions_this_turn == 0

                # Write - tracked
                await ues.email.send(
                    from_address="a@b.com",
                    to_addresses=["c@d.com"],
                    subject="S",
                    body_text="B",
                )
                assert context.actions_this_turn == 1

                # Read - not tracked
                await ues.sms.get_state()
                assert context.actions_this_turn == 1

                # Write - tracked
                await ues.sms.send(to_number="+1", content="Hi")
                assert context.actions_this_turn == 2

    @pytest.mark.asyncio
    async def test_tracking_across_multiple_modalities(
        self, context: AssessmentContext, mock_async_client: MagicMock
    ):
        """Actions across different modalities should all be tracked."""
        with patch(
            "agentbeats.purple.ues_client.AsyncUESClient",
            return_value=mock_async_client,
        ):
            async with TrackedAsyncUESClient(context) as ues:
                await ues.email.send(
                    from_address="a@b.com",
                    to_addresses=["c@d.com"],
                    subject="S",
                    body_text="B",
                )
                await ues.sms.send(to_number="+1", content="Hi")
                await ues.chat.send(content="Hello", role="assistant")
                await ues.calendar.create(title="Meeting", start="2026-01-22T10:00:00Z")
                await ues.location.update(latitude=37.7, longitude=-122.4)
                await ues.weather.update(location="NYC", temperature=72)

                assert context.actions_this_turn == 6
                assert context.total_actions == 6

    @pytest.mark.asyncio
    async def test_tracking_persists_across_turn_reset(
        self, context: AssessmentContext, mock_async_client: MagicMock
    ):
        """Total actions should persist when turn resets."""
        with patch(
            "agentbeats.purple.ues_client.AsyncUESClient",
            return_value=mock_async_client,
        ):
            async with TrackedAsyncUESClient(context) as ues:
                # Turn 1
                await ues.email.send(
                    from_address="a@b.com",
                    to_addresses=["c@d.com"],
                    subject="S",
                    body_text="B",
                )
                await ues.email.send(
                    from_address="a@b.com",
                    to_addresses=["c@d.com"],
                    subject="S",
                    body_text="B",
                )
                assert context.actions_this_turn == 2
                assert context.total_actions == 2

                # Simulate turn reset
                context.start_new_turn(
                    datetime(2026, 1, 22, 10, 0, tzinfo=timezone.utc),
                    events_processed=0,
                )
                assert context.actions_this_turn == 0
                assert context.total_actions == 2  # Preserved

                # Turn 2
                await ues.sms.send(to_number="+1", content="Hi")
                assert context.actions_this_turn == 1
                assert context.total_actions == 3
