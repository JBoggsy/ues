"""Unit tests for the EventsClient and AsyncEventsClient.

This module tests the events management sub-client that provides methods for
creating, querying, and managing simulation events.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from client._events import (
    AsyncEventsClient,
    CancelEventResponse,
    EventListResponse,
    EventResponse,
    EventsClient,
    EventSummaryResponse,
)
from client.exceptions import NotFoundError


# =============================================================================
# Response Model Tests
# =============================================================================


class TestEventResponse:
    """Tests for the EventResponse model."""

    def test_instantiation_with_all_fields(self):
        """Test creating an EventResponse with all fields."""
        response = EventResponse(
            event_id="evt-123-abc",
            scheduled_time=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
            modality="email",
            status="pending",
            priority=50,
            created_at=datetime(2025, 1, 15, 9, 0, tzinfo=timezone.utc),
            executed_at=None,
            error_message=None,
            data={"action": "receive", "from_address": "sender@example.com"},
        )
        assert response.event_id == "evt-123-abc"
        assert response.scheduled_time == datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc)
        assert response.modality == "email"
        assert response.status == "pending"
        assert response.priority == 50
        assert response.created_at == datetime(2025, 1, 15, 9, 0, tzinfo=timezone.utc)
        assert response.executed_at is None
        assert response.error_message is None
        assert response.data == {"action": "receive", "from_address": "sender@example.com"}

    def test_instantiation_with_executed_event(self):
        """Test EventResponse for an executed event."""
        response = EventResponse(
            event_id="evt-456-def",
            scheduled_time=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
            modality="sms",
            status="executed",
            priority=75,
            created_at=datetime(2025, 1, 15, 9, 0, tzinfo=timezone.utc),
            executed_at=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
            error_message=None,
            data=None,
        )
        assert response.status == "executed"
        assert response.executed_at is not None

    def test_instantiation_with_failed_event(self):
        """Test EventResponse for a failed event."""
        response = EventResponse(
            event_id="evt-789-ghi",
            scheduled_time=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
            modality="calendar",
            status="failed",
            priority=50,
            created_at=datetime(2025, 1, 15, 9, 0, tzinfo=timezone.utc),
            executed_at=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
            error_message="Invalid calendar event data",
            data=None,
        )
        assert response.status == "failed"
        assert response.error_message == "Invalid calendar event data"

    def test_instantiation_with_minimal_fields(self):
        """Test EventResponse with only required fields."""
        response = EventResponse(
            event_id="evt-min",
            scheduled_time=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
            modality="email",
            status="pending",
            priority=50,
            created_at=datetime(2025, 1, 15, 9, 0, tzinfo=timezone.utc),
        )
        assert response.executed_at is None
        assert response.error_message is None
        assert response.data is None


class TestEventListResponse:
    """Tests for the EventListResponse model."""

    def test_instantiation_with_events(self):
        """Test creating an EventListResponse with events."""
        events = [
            EventResponse(
                event_id="evt-1",
                scheduled_time=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
                modality="email",
                status="pending",
                priority=50,
                created_at=datetime(2025, 1, 15, 9, 0, tzinfo=timezone.utc),
            ),
            EventResponse(
                event_id="evt-2",
                scheduled_time=datetime(2025, 1, 15, 11, 0, tzinfo=timezone.utc),
                modality="sms",
                status="executed",
                priority=75,
                created_at=datetime(2025, 1, 15, 9, 0, tzinfo=timezone.utc),
            ),
        ]
        response = EventListResponse(
            events=events,
            total=100,
            pending=40,
            executed=55,
            failed=3,
            skipped=2,
        )
        assert len(response.events) == 2
        assert response.total == 100
        assert response.pending == 40
        assert response.executed == 55
        assert response.failed == 3
        assert response.skipped == 2

    def test_instantiation_with_empty_events(self):
        """Test EventListResponse with no events."""
        response = EventListResponse(
            events=[],
            total=0,
            pending=0,
            executed=0,
            failed=0,
            skipped=0,
        )
        assert response.events == []
        assert response.total == 0


class TestEventSummaryResponse:
    """Tests for the EventSummaryResponse model."""

    def test_instantiation_with_all_fields(self):
        """Test creating an EventSummaryResponse with all fields."""
        response = EventSummaryResponse(
            total=100,
            pending=40,
            executed=55,
            failed=3,
            skipped=2,
            by_modality={"email": 50, "sms": 30, "calendar": 20},
            next_event_time=datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc),
        )
        assert response.total == 100
        assert response.pending == 40
        assert response.executed == 55
        assert response.failed == 3
        assert response.skipped == 2
        assert response.by_modality == {"email": 50, "sms": 30, "calendar": 20}
        assert response.next_event_time == datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc)

    def test_instantiation_without_next_event_time(self):
        """Test EventSummaryResponse when no pending events."""
        response = EventSummaryResponse(
            total=50,
            pending=0,
            executed=50,
            failed=0,
            skipped=0,
            by_modality={"email": 50},
            next_event_time=None,
        )
        assert response.next_event_time is None

    def test_instantiation_with_minimal_fields(self):
        """Test EventSummaryResponse without optional next_event_time."""
        response = EventSummaryResponse(
            total=0,
            pending=0,
            executed=0,
            failed=0,
            skipped=0,
            by_modality={},
        )
        assert response.next_event_time is None
        assert response.by_modality == {}


class TestCancelEventResponse:
    """Tests for the CancelEventResponse model."""

    def test_instantiation_cancelled_true(self):
        """Test CancelEventResponse for successful cancellation."""
        response = CancelEventResponse(
            cancelled=True,
            event_id="evt-cancelled-123",
        )
        assert response.cancelled is True
        assert response.event_id == "evt-cancelled-123"

    def test_instantiation_cancelled_false(self):
        """Test CancelEventResponse for failed cancellation."""
        response = CancelEventResponse(
            cancelled=False,
            event_id="evt-not-cancelled",
        )
        assert response.cancelled is False


# =============================================================================
# EventsClient Tests
# =============================================================================


class TestEventsClientListEvents:
    """Tests for EventsClient.list_events() method."""

    def test_list_events_no_filters(self):
        """Test listing events without any filters."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "events": [
                {
                    "event_id": "evt-1",
                    "scheduled_time": "2025-01-15T10:00:00+00:00",
                    "modality": "email",
                    "status": "pending",
                    "priority": 50,
                    "created_at": "2025-01-15T09:00:00+00:00",
                }
            ],
            "total": 1,
            "pending": 1,
            "executed": 0,
            "failed": 0,
            "skipped": 0,
        }

        client = EventsClient(mock_http)
        result = client.list_events()

        mock_http.get.assert_called_once_with("/events", params={})
        assert isinstance(result, EventListResponse)
        assert len(result.events) == 1
        assert result.pending == 1

    def test_list_events_with_status_filter(self):
        """Test listing events filtered by status."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "events": [],
            "total": 0,
            "pending": 10,
            "executed": 50,
            "failed": 5,
            "skipped": 2,
        }

        client = EventsClient(mock_http)
        result = client.list_events(status="pending")

        mock_http.get.assert_called_once_with("/events", params={"status": "pending"})
        assert isinstance(result, EventListResponse)

    def test_list_events_with_modality_filter(self):
        """Test listing events filtered by modality."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "events": [],
            "total": 0,
            "pending": 0,
            "executed": 0,
            "failed": 0,
            "skipped": 0,
        }

        client = EventsClient(mock_http)
        result = client.list_events(modality="email")

        mock_http.get.assert_called_once_with("/events", params={"modality": "email"})

    def test_list_events_with_time_range(self):
        """Test listing events filtered by time range."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "events": [],
            "total": 0,
            "pending": 0,
            "executed": 0,
            "failed": 0,
            "skipped": 0,
        }

        start = datetime(2025, 1, 15, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 16, 0, 0, tzinfo=timezone.utc)
        client = EventsClient(mock_http)
        result = client.list_events(start_time=start, end_time=end)

        mock_http.get.assert_called_once_with(
            "/events",
            params={
                "start_time": "2025-01-15T00:00:00+00:00",
                "end_time": "2025-01-16T00:00:00+00:00",
            },
        )

    def test_list_events_with_pagination(self):
        """Test listing events with pagination."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "events": [],
            "total": 100,
            "pending": 50,
            "executed": 40,
            "failed": 5,
            "skipped": 5,
        }

        client = EventsClient(mock_http)
        result = client.list_events(limit=10, offset=20)

        mock_http.get.assert_called_once_with(
            "/events",
            params={"limit": 10, "offset": 20},
        )

    def test_list_events_with_all_filters(self):
        """Test listing events with all filters combined."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "events": [],
            "total": 5,
            "pending": 5,
            "executed": 0,
            "failed": 0,
            "skipped": 0,
        }

        start = datetime(2025, 1, 15, 0, 0, tzinfo=timezone.utc)
        client = EventsClient(mock_http)
        result = client.list_events(
            status="pending",
            modality="email",
            start_time=start,
            limit=5,
            offset=10,
        )

        mock_http.get.assert_called_once_with(
            "/events",
            params={
                "status": "pending",
                "modality": "email",
                "start_time": "2025-01-15T00:00:00+00:00",
                "limit": 5,
                "offset": 10,
            },
        )


class TestEventsClientCreate:
    """Tests for EventsClient.create() method."""

    def test_create_event_minimal(self):
        """Test creating an event with minimal parameters."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-new-1",
            "scheduled_time": "2025-01-15T12:00:00+00:00",
            "modality": "email",
            "status": "pending",
            "priority": 50,
            "created_at": "2025-01-15T10:00:00+00:00",
        }

        scheduled = datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc)
        client = EventsClient(mock_http)
        result = client.create(
            scheduled_time=scheduled,
            modality="email",
            data={"action": "receive", "from_address": "test@example.com"},
        )

        mock_http.post.assert_called_once_with(
            "/events",
            json={
                "scheduled_time": "2025-01-15T12:00:00+00:00",
                "modality": "email",
                "data": {"action": "receive", "from_address": "test@example.com"},
                "priority": 50,
            },
            params=None,
        )
        assert isinstance(result, EventResponse)
        assert result.event_id == "evt-new-1"

    def test_create_event_with_priority(self):
        """Test creating an event with custom priority."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-high-pri",
            "scheduled_time": "2025-01-15T12:00:00+00:00",
            "modality": "sms",
            "status": "pending",
            "priority": 100,
            "created_at": "2025-01-15T10:00:00+00:00",
        }

        scheduled = datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc)
        client = EventsClient(mock_http)
        result = client.create(
            scheduled_time=scheduled,
            modality="sms",
            data={"action": "send"},
            priority=100,
        )

        call_args = mock_http.post.call_args
        assert call_args[1]["json"]["priority"] == 100

    def test_create_event_with_metadata(self):
        """Test creating an event with metadata."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-meta",
            "scheduled_time": "2025-01-15T12:00:00+00:00",
            "modality": "email",
            "status": "pending",
            "priority": 50,
            "created_at": "2025-01-15T10:00:00+00:00",
        }

        scheduled = datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc)
        metadata = {"source": "test", "batch_id": "batch-123"}
        client = EventsClient(mock_http)
        result = client.create(
            scheduled_time=scheduled,
            modality="email",
            data={"action": "receive"},
            metadata=metadata,
        )

        call_args = mock_http.post.call_args
        assert call_args[1]["json"]["metadata"] == metadata

    def test_create_event_with_agent_id(self):
        """Test creating an event with agent_id."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-agent",
            "scheduled_time": "2025-01-15T12:00:00+00:00",
            "modality": "email",
            "status": "pending",
            "priority": 50,
            "created_at": "2025-01-15T10:00:00+00:00",
        }

        scheduled = datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc)
        client = EventsClient(mock_http)
        result = client.create(
            scheduled_time=scheduled,
            modality="email",
            data={"action": "receive"},
            agent_id="agent-001",
        )

        call_args = mock_http.post.call_args
        assert call_args[1]["json"]["agent_id"] == "agent-001"

    def test_create_event_with_all_params(self):
        """Test creating an event with all parameters."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-full",
            "scheduled_time": "2025-01-15T12:00:00+00:00",
            "modality": "calendar",
            "status": "pending",
            "priority": 75,
            "created_at": "2025-01-15T10:00:00+00:00",
        }

        scheduled = datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc)
        client = EventsClient(mock_http)
        result = client.create(
            scheduled_time=scheduled,
            modality="calendar",
            data={"action": "create", "title": "Meeting"},
            priority=75,
            metadata={"test": True},
            agent_id="agent-002",
        )

        mock_http.post.assert_called_once_with(
            "/events",
            json={
                "scheduled_time": "2025-01-15T12:00:00+00:00",
                "modality": "calendar",
                "data": {"action": "create", "title": "Meeting"},
                "priority": 75,
                "metadata": {"test": True},
                "agent_id": "agent-002",
            },
            params=None,
        )


class TestEventsClientCreateImmediate:
    """Tests for EventsClient.create_immediate() method."""

    def test_create_immediate_event(self):
        """Test creating an immediate event."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-immediate",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "modality": "email",
            "status": "pending",
            "priority": 100,
            "created_at": "2025-01-15T10:00:00+00:00",
        }

        client = EventsClient(mock_http)
        result = client.create_immediate(
            modality="email",
            data={"action": "receive", "from_address": "urgent@example.com"},
        )

        mock_http.post.assert_called_once_with(
            "/events/immediate",
            json={
                "modality": "email",
                "data": {"action": "receive", "from_address": "urgent@example.com"},
            },
            params=None,
        )
        assert isinstance(result, EventResponse)
        assert result.priority == 100


class TestEventsClientGet:
    """Tests for EventsClient.get() method."""

    def test_get_event(self):
        """Test getting a specific event by ID."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "event_id": "evt-get-123",
            "scheduled_time": "2025-01-15T12:00:00+00:00",
            "modality": "email",
            "status": "pending",
            "priority": 50,
            "created_at": "2025-01-15T10:00:00+00:00",
            "data": {"action": "receive", "from_address": "sender@example.com"},
        }

        client = EventsClient(mock_http)
        result = client.get("evt-get-123")

        mock_http.get.assert_called_once_with("/events/evt-get-123", params=None)
        assert isinstance(result, EventResponse)
        assert result.event_id == "evt-get-123"
        assert result.data == {"action": "receive", "from_address": "sender@example.com"}


class TestEventsClientCancel:
    """Tests for EventsClient.cancel() method."""

    def test_cancel_event(self):
        """Test cancelling a pending event."""
        mock_http = MagicMock()
        mock_http.delete.return_value = {
            "cancelled": True,
            "event_id": "evt-cancel-123",
        }

        client = EventsClient(mock_http)
        result = client.cancel("evt-cancel-123")

        mock_http.delete.assert_called_once_with("/events/evt-cancel-123", params=None)
        assert isinstance(result, CancelEventResponse)
        assert result.cancelled is True
        assert result.event_id == "evt-cancel-123"


class TestEventsClientNext:
    """Tests for EventsClient.next() method."""

    def test_next_event_exists(self):
        """Test getting next event when one exists."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "event_id": "evt-next",
            "scheduled_time": "2025-01-15T12:00:00+00:00",
            "modality": "email",
            "status": "pending",
            "priority": 50,
            "created_at": "2025-01-15T10:00:00+00:00",
        }

        client = EventsClient(mock_http)
        result = client.next()

        mock_http.get.assert_called_once_with("/events/next", params=None)
        assert isinstance(result, EventResponse)
        assert result.event_id == "evt-next"

    def test_next_event_not_exists(self):
        """Test getting next event when none exist."""
        mock_http = MagicMock()
        mock_http.get.side_effect = NotFoundError(
            message="No pending events",
        )

        client = EventsClient(mock_http)
        result = client.next()

        assert result is None


class TestEventsClientSummary:
    """Tests for EventsClient.summary() method."""

    def test_summary(self):
        """Test getting event summary."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "total": 100,
            "pending": 40,
            "executed": 55,
            "failed": 3,
            "skipped": 2,
            "by_modality": {"email": 50, "sms": 30, "calendar": 20},
            "next_event_time": "2025-01-15T12:00:00+00:00",
        }

        client = EventsClient(mock_http)
        result = client.summary()

        mock_http.get.assert_called_once_with("/events/summary", params=None)
        assert isinstance(result, EventSummaryResponse)
        assert result.total == 100
        assert result.pending == 40
        assert result.by_modality == {"email": 50, "sms": 30, "calendar": 20}

    def test_summary_no_pending_events(self):
        """Test getting summary when no pending events."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "total": 50,
            "pending": 0,
            "executed": 50,
            "failed": 0,
            "skipped": 0,
            "by_modality": {"email": 50},
            "next_event_time": None,
        }

        client = EventsClient(mock_http)
        result = client.summary()

        assert result.pending == 0
        assert result.next_event_time is None


# =============================================================================
# AsyncEventsClient Tests
# =============================================================================


class TestAsyncEventsClientListEvents:
    """Tests for AsyncEventsClient.list_events() method."""

    async def test_list_events_no_filters(self):
        """Test listing events without filters."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {
            "events": [
                {
                    "event_id": "async-evt-1",
                    "scheduled_time": "2025-01-15T10:00:00+00:00",
                    "modality": "email",
                    "status": "pending",
                    "priority": 50,
                    "created_at": "2025-01-15T09:00:00+00:00",
                }
            ],
            "total": 1,
            "pending": 1,
            "executed": 0,
            "failed": 0,
            "skipped": 0,
        }

        client = AsyncEventsClient(mock_http)
        result = await client.list_events()

        mock_http.get.assert_called_once_with("/events", params={})
        assert isinstance(result, EventListResponse)

    async def test_list_events_with_filters(self):
        """Test listing events with filters."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {
            "events": [],
            "total": 0,
            "pending": 0,
            "executed": 0,
            "failed": 0,
            "skipped": 0,
        }

        start = datetime(2025, 1, 15, 0, 0, tzinfo=timezone.utc)
        client = AsyncEventsClient(mock_http)
        result = await client.list_events(
            status="pending",
            modality="email",
            start_time=start,
        )

        mock_http.get.assert_called_once_with(
            "/events",
            params={
                "status": "pending",
                "modality": "email",
                "start_time": "2025-01-15T00:00:00+00:00",
            },
        )


class TestAsyncEventsClientCreate:
    """Tests for AsyncEventsClient.create() method."""

    async def test_create_event(self):
        """Test creating an event."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "event_id": "async-evt-new",
            "scheduled_time": "2025-01-15T12:00:00+00:00",
            "modality": "email",
            "status": "pending",
            "priority": 50,
            "created_at": "2025-01-15T10:00:00+00:00",
        }

        scheduled = datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc)
        client = AsyncEventsClient(mock_http)
        result = await client.create(
            scheduled_time=scheduled,
            modality="email",
            data={"action": "receive"},
        )

        mock_http.post.assert_called_once_with(
            "/events",
            json={
                "scheduled_time": "2025-01-15T12:00:00+00:00",
                "modality": "email",
                "data": {"action": "receive"},
                "priority": 50,
            },
            params=None,
        )
        assert isinstance(result, EventResponse)


class TestAsyncEventsClientCreateImmediate:
    """Tests for AsyncEventsClient.create_immediate() method."""

    async def test_create_immediate_event(self):
        """Test creating an immediate event."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "event_id": "async-evt-imm",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "modality": "sms",
            "status": "pending",
            "priority": 100,
            "created_at": "2025-01-15T10:00:00+00:00",
        }

        client = AsyncEventsClient(mock_http)
        result = await client.create_immediate(
            modality="sms",
            data={"action": "send", "body": "Test message"},
        )

        mock_http.post.assert_called_once_with(
            "/events/immediate",
            json={
                "modality": "sms",
                "data": {"action": "send", "body": "Test message"},
            },
            params=None,
        )
        assert isinstance(result, EventResponse)


class TestAsyncEventsClientGet:
    """Tests for AsyncEventsClient.get() method."""

    async def test_get_event(self):
        """Test getting a specific event."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {
            "event_id": "async-evt-get",
            "scheduled_time": "2025-01-15T12:00:00+00:00",
            "modality": "email",
            "status": "executed",
            "priority": 50,
            "created_at": "2025-01-15T10:00:00+00:00",
            "executed_at": "2025-01-15T12:00:00+00:00",
        }

        client = AsyncEventsClient(mock_http)
        result = await client.get("async-evt-get")

        mock_http.get.assert_called_once_with("/events/async-evt-get", params=None)
        assert isinstance(result, EventResponse)
        assert result.status == "executed"


class TestAsyncEventsClientCancel:
    """Tests for AsyncEventsClient.cancel() method."""

    async def test_cancel_event(self):
        """Test cancelling an event."""
        mock_http = AsyncMock()
        mock_http.delete.return_value = {
            "cancelled": True,
            "event_id": "async-evt-cancel",
        }

        client = AsyncEventsClient(mock_http)
        result = await client.cancel("async-evt-cancel")

        mock_http.delete.assert_called_once_with("/events/async-evt-cancel", params=None)
        assert isinstance(result, CancelEventResponse)
        assert result.cancelled is True


class TestAsyncEventsClientNext:
    """Tests for AsyncEventsClient.next() method."""

    async def test_next_event_exists(self):
        """Test getting next event."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {
            "event_id": "async-evt-next",
            "scheduled_time": "2025-01-15T12:00:00+00:00",
            "modality": "email",
            "status": "pending",
            "priority": 50,
            "created_at": "2025-01-15T10:00:00+00:00",
        }

        client = AsyncEventsClient(mock_http)
        result = await client.next()

        mock_http.get.assert_called_once_with("/events/next", params=None)
        assert isinstance(result, EventResponse)

    async def test_next_event_not_exists(self):
        """Test getting next event when none exist."""
        mock_http = AsyncMock()
        mock_http.get.side_effect = NotFoundError(
            message="No pending events",
        )

        client = AsyncEventsClient(mock_http)
        result = await client.next()

        assert result is None


class TestAsyncEventsClientSummary:
    """Tests for AsyncEventsClient.summary() method."""

    async def test_summary(self):
        """Test getting event summary."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {
            "total": 200,
            "pending": 80,
            "executed": 110,
            "failed": 5,
            "skipped": 5,
            "by_modality": {"email": 100, "sms": 60, "calendar": 40},
            "next_event_time": "2025-01-15T14:00:00+00:00",
        }

        client = AsyncEventsClient(mock_http)
        result = await client.summary()

        mock_http.get.assert_called_once_with("/events/summary", params=None)
        assert isinstance(result, EventSummaryResponse)
        assert result.total == 200
