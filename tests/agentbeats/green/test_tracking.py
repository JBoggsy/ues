"""Tests for ActionTracker in the Green Agent.

These tests verify that the ActionTracker correctly:
- Queries events filtered by Purple agent ID
- Converts events to ActionLogEntry format
- Tracks seen events to avoid duplicates
- Generates appropriate summaries for different modalities
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from agentbeats.green.tracking import ActionTracker
from agentbeats.green.session import ActionLogEntry
from client._events import EventResponse, EventListResponse


@pytest.fixture
def mock_ues_client():
    """Create a mock AsyncUESClient with events sub-client."""
    client = AsyncMock()
    client.events = AsyncMock()
    return client


@pytest.fixture
def tracker(mock_ues_client):
    """Create an ActionTracker with mock client."""
    return ActionTracker(mock_ues_client, "purple-agent-12345")


def make_event_response(
    event_id: str,
    modality: str,
    data: dict | None = None,
    scheduled_time: datetime | None = None,
    created_at: datetime | None = None,
    agent_id: str = "purple-agent-12345",
) -> EventResponse:
    """Helper to create EventResponse objects for testing."""
    now = datetime.now(timezone.utc)
    return EventResponse(
        event_id=event_id,
        scheduled_time=scheduled_time or now,
        modality=modality,
        status="pending",
        priority=0,
        created_at=created_at or now,
        data=data,
        agent_id=agent_id,
    )


class TestActionTrackerInit:
    """Tests for ActionTracker initialization."""
    
    def test_init_stores_client_and_agent_id(self, mock_ues_client):
        """Verify ActionTracker stores provided dependencies."""
        tracker = ActionTracker(mock_ues_client, "test-agent")
        assert tracker._client is mock_ues_client
        assert tracker._purple_agent_id == "test-agent"
    
    def test_init_has_empty_seen_events(self, tracker):
        """Verify ActionTracker starts with no seen events."""
        assert tracker.seen_count == 0


class TestGetActionsSince:
    """Tests for get_actions_since method."""
    
    @pytest.mark.asyncio
    async def test_queries_with_agent_id(self, tracker, mock_ues_client):
        """Verify it filters events by Purple agent ID."""
        mock_ues_client.events.list_events.return_value = EventListResponse(
            events=[],
            total=0,
            pending=0,
            executed=0,
            failed=0,
            skipped=0,
        )
        
        since_time = datetime.now(timezone.utc)
        await tracker.get_actions_since(since_time)
        
        mock_ues_client.events.list_events.assert_called_once_with(
            agent_id="purple-agent-12345",
        )
    
    @pytest.mark.asyncio
    async def test_returns_new_events_only(self, tracker, mock_ues_client):
        """Verify it only returns events after since_time."""
        old_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        new_time = datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        since_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        mock_ues_client.events.list_events.return_value = EventListResponse(
            events=[
                make_event_response("old-event", "email", {"subject": "Old"}, created_at=old_time),
                make_event_response("new-event", "email", {"subject": "New"}, created_at=new_time),
            ],
            total=2,
            pending=2,
            executed=0,
            failed=0,
            skipped=0,
        )
        
        actions = await tracker.get_actions_since(since_time)
        
        assert len(actions) == 1
        assert actions[0].event_id == "new-event"
    
    @pytest.mark.asyncio
    async def test_skips_already_seen_events(self, tracker, mock_ues_client):
        """Verify it doesn't return events that were already seen."""
        now = datetime.now(timezone.utc)
        event = make_event_response("event-1", "email", {"subject": "Test"}, created_at=now)
        
        mock_ues_client.events.list_events.return_value = EventListResponse(
            events=[event],
            total=1,
            pending=1,
            executed=0,
            failed=0,
            skipped=0,
        )
        
        # First call should return the event
        actions1 = await tracker.get_actions_since(now)
        assert len(actions1) == 1
        
        # Second call should skip it
        actions2 = await tracker.get_actions_since(now)
        assert len(actions2) == 0
    
    @pytest.mark.asyncio
    async def test_assigns_correct_turn_number(self, tracker, mock_ues_client):
        """Verify turn number is assigned to action entries."""
        now = datetime.now(timezone.utc)
        mock_ues_client.events.list_events.return_value = EventListResponse(
            events=[
                make_event_response("event-1", "email", {"subject": "Test"}, created_at=now),
            ],
            total=1,
            pending=1,
            executed=0,
            failed=0,
            skipped=0,
        )
        
        actions = await tracker.get_actions_since(now, turn=3)
        
        assert actions[0].turn == 3


class TestGetAllActions:
    """Tests for get_all_actions method."""
    
    @pytest.mark.asyncio
    async def test_returns_all_events(self, tracker, mock_ues_client):
        """Verify it returns all events regardless of seen status."""
        now = datetime.now(timezone.utc)
        event = make_event_response("event-1", "email", {"subject": "Test"}, created_at=now)
        
        mock_ues_client.events.list_events.return_value = EventListResponse(
            events=[event],
            total=1,
            pending=1,
            executed=0,
            failed=0,
            skipped=0,
        )
        
        # Mark as seen
        await tracker.get_actions_since(now)
        
        # get_all_actions should still return it
        actions = await tracker.get_all_actions()
        assert len(actions) == 1


class TestEventConversion:
    """Tests for converting events to ActionLogEntry."""
    
    @pytest.mark.asyncio
    async def test_converts_email_event(self, tracker, mock_ues_client):
        """Verify email events are converted correctly."""
        now = datetime.now(timezone.utc)
        mock_ues_client.events.list_events.return_value = EventListResponse(
            events=[
                make_event_response(
                    "email-1",
                    "email",
                    {
                        "subject": "Meeting Tomorrow",
                        "to_addresses": ["bob@example.com"],
                    },
                    scheduled_time=now,
                    created_at=now,
                ),
            ],
            total=1,
            pending=1,
            executed=0,
            failed=0,
            skipped=0,
        )
        
        actions = await tracker.get_actions_since(now, turn=1)
        
        assert len(actions) == 1
        action = actions[0]
        assert action.event_id == "email-1"
        assert action.modality == "email"
        assert action.action_type == "send"
        assert "bob@example.com" in action.summary
        assert "Meeting Tomorrow" in action.summary
    
    @pytest.mark.asyncio
    async def test_converts_sms_event(self, tracker, mock_ues_client):
        """Verify SMS events are converted correctly."""
        now = datetime.now(timezone.utc)
        mock_ues_client.events.list_events.return_value = EventListResponse(
            events=[
                make_event_response(
                    "sms-1",
                    "sms",
                    {
                        "to": "+1234567890",
                        "text": "Hello there!",
                    },
                    created_at=now,
                ),
            ],
            total=1,
            pending=1,
            executed=0,
            failed=0,
            skipped=0,
        )
        
        actions = await tracker.get_actions_since(now)
        
        action = actions[0]
        assert action.modality == "sms"
        assert action.action_type == "send"
        assert "+1234567890" in action.summary
        assert "Hello there!" in action.summary
    
    @pytest.mark.asyncio
    async def test_converts_calendar_event(self, tracker, mock_ues_client):
        """Verify calendar events are converted correctly."""
        now = datetime.now(timezone.utc)
        mock_ues_client.events.list_events.return_value = EventListResponse(
            events=[
                make_event_response(
                    "cal-1",
                    "calendar",
                    {
                        "event_id": "unique-id",
                        "title": "Team Standup",
                    },
                    created_at=now,
                ),
            ],
            total=1,
            pending=1,
            executed=0,
            failed=0,
            skipped=0,
        )
        
        actions = await tracker.get_actions_since(now)
        
        action = actions[0]
        assert action.modality == "calendar"
        assert action.action_type == "create"
        assert "Team Standup" in action.summary
    
    @pytest.mark.asyncio
    async def test_converts_chat_event(self, tracker, mock_ues_client):
        """Verify chat events are converted correctly."""
        now = datetime.now(timezone.utc)
        mock_ues_client.events.list_events.return_value = EventListResponse(
            events=[
                make_event_response(
                    "chat-1",
                    "chat",
                    {
                        "content": "Hello, I need help!",
                    },
                    created_at=now,
                ),
            ],
            total=1,
            pending=1,
            executed=0,
            failed=0,
            skipped=0,
        )
        
        actions = await tracker.get_actions_since(now)
        
        action = actions[0]
        assert action.modality == "chat"
        assert action.action_type == "send"
        assert "Hello, I need help!" in action.summary
    
    @pytest.mark.asyncio
    async def test_handles_event_with_explicit_operation(self, tracker, mock_ues_client):
        """Verify events with explicit operation field use it."""
        now = datetime.now(timezone.utc)
        mock_ues_client.events.list_events.return_value = EventListResponse(
            events=[
                make_event_response(
                    "cal-1",
                    "calendar",
                    {
                        "operation": "delete",
                        "title": "Cancelled Meeting",
                    },
                    created_at=now,
                ),
            ],
            total=1,
            pending=1,
            executed=0,
            failed=0,
            skipped=0,
        )
        
        actions = await tracker.get_actions_since(now)
        
        assert actions[0].action_type == "delete"
    
    @pytest.mark.asyncio
    async def test_handles_event_with_null_data(self, tracker, mock_ues_client):
        """Verify events with null data are handled gracefully."""
        now = datetime.now(timezone.utc)
        mock_ues_client.events.list_events.return_value = EventListResponse(
            events=[
                make_event_response("event-1", "unknown", None, created_at=now),
            ],
            total=1,
            pending=1,
            executed=0,
            failed=0,
            skipped=0,
        )
        
        actions = await tracker.get_actions_since(now)
        
        assert len(actions) == 1
        assert actions[0].action_type == "unknown"


class TestReset:
    """Tests for reset method."""
    
    @pytest.mark.asyncio
    async def test_reset_clears_seen_events(self, tracker, mock_ues_client):
        """Verify reset allows events to be returned again."""
        now = datetime.now(timezone.utc)
        event = make_event_response("event-1", "email", {"subject": "Test"}, created_at=now)
        
        mock_ues_client.events.list_events.return_value = EventListResponse(
            events=[event],
            total=1,
            pending=1,
            executed=0,
            failed=0,
            skipped=0,
        )
        
        # Mark as seen
        await tracker.get_actions_since(now)
        assert tracker.seen_count == 1
        
        # Reset
        tracker.reset()
        assert tracker.seen_count == 0
        
        # Should return again
        actions = await tracker.get_actions_since(now)
        assert len(actions) == 1


class TestSeenCount:
    """Tests for seen_count property."""
    
    def test_starts_at_zero(self, tracker):
        """Verify seen_count starts at 0."""
        assert tracker.seen_count == 0
    
    @pytest.mark.asyncio
    async def test_increments_with_new_events(self, tracker, mock_ues_client):
        """Verify seen_count increases when events are processed."""
        now = datetime.now(timezone.utc)
        mock_ues_client.events.list_events.return_value = EventListResponse(
            events=[
                make_event_response("event-1", "email", {"subject": "Test 1"}, created_at=now),
                make_event_response("event-2", "email", {"subject": "Test 2"}, created_at=now),
            ],
            total=2,
            pending=2,
            executed=0,
            failed=0,
            skipped=0,
        )
        
        await tracker.get_actions_since(now)
        
        assert tracker.seen_count == 2


class TestSummaryGeneration:
    """Tests for summary generation with edge cases."""
    
    @pytest.mark.asyncio
    async def test_truncates_long_sms_content(self, tracker, mock_ues_client):
        """Verify long SMS content is truncated in summary."""
        now = datetime.now(timezone.utc)
        long_text = "A" * 100  # 100 characters
        mock_ues_client.events.list_events.return_value = EventListResponse(
            events=[
                make_event_response("sms-1", "sms", {"to": "123", "text": long_text}, created_at=now),
            ],
            total=1,
            pending=1,
            executed=0,
            failed=0,
            skipped=0,
        )
        
        actions = await tracker.get_actions_since(now)
        
        # Should be truncated with ellipsis
        assert "..." in actions[0].summary
        assert len(actions[0].summary) < 100  # Shouldn't contain full 100 char text
    
    @pytest.mark.asyncio
    async def test_email_draft_action_type(self, tracker, mock_ues_client):
        """Verify email drafts get correct action type."""
        now = datetime.now(timezone.utc)
        mock_ues_client.events.list_events.return_value = EventListResponse(
            events=[
                make_event_response(
                    "email-1",
                    "email",
                    {
                        "subject": "Draft Email",
                        "to_addresses": ["test@example.com"],
                        "is_draft": True,
                    },
                    created_at=now,
                ),
            ],
            total=1,
            pending=1,
            executed=0,
            failed=0,
            skipped=0,
        )
        
        actions = await tracker.get_actions_since(now)
        
        assert actions[0].action_type == "draft"
        assert "Drafted" in actions[0].summary
