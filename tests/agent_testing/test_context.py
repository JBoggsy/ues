"""Tests for the agent_testing.context module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agent_testing.context import EvalContext


class TestEvalContext:
    """Tests for the EvalContext class."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock UES client."""
        client = MagicMock()
        
        # Mock modality clients
        client.email = MagicMock()
        client.email.get_state = AsyncMock(return_value=MagicMock(message_count=5))
        
        client.sms = MagicMock()
        client.sms.get_state = AsyncMock(return_value=MagicMock())
        
        client.calendar = MagicMock()
        client.calendar.get_state = AsyncMock(return_value=MagicMock())
        
        client.location = MagicMock()
        client.location.get_state = AsyncMock(return_value=MagicMock())
        
        client.weather = MagicMock()
        client.weather.get_state = AsyncMock(return_value=MagicMock())
        
        # Mock time client
        client.time = MagicMock()
        from datetime import datetime, timezone
        mock_time_state = MagicMock()
        mock_time_state.current_time = datetime(2026, 1, 19, 12, 0, tzinfo=timezone.utc)
        client.time.get_state = AsyncMock(return_value=mock_time_state)
        
        # Mock events client
        client.events = MagicMock()
        client.events.list = AsyncMock(return_value=[])
        
        return client

    def test_context_initialization(self, mock_client):
        """Test creating a context with all fields."""
        ctx = EvalContext(
            client=mock_client,
            event_history=[{"id": "1", "modality": "email"}],
            trigger_event={"id": "2", "modality": "sms"},
            scenario_config={"name": "Test Scenario"},
            criteria_config={"name": "Test Criteria"},
        )

        assert ctx.client == mock_client
        assert len(ctx.event_history) == 1
        assert ctx.trigger_event["id"] == "2"
        assert ctx.scenario_config["name"] == "Test Scenario"

    def test_context_defaults(self, mock_client):
        """Test default values for context fields."""
        ctx = EvalContext(client=mock_client)

        assert ctx.event_history == []
        assert ctx.trigger_event is None
        assert ctx.scenario_config == {}
        assert ctx.criteria_config == {}

    @pytest.mark.asyncio
    async def test_get_state_email(self, mock_client):
        """Test getting email state."""
        ctx = EvalContext(client=mock_client)

        state = await ctx.get_state("email")

        mock_client.email.get_state.assert_called_once()
        assert state.message_count == 5

    @pytest.mark.asyncio
    async def test_get_state_sms(self, mock_client):
        """Test getting SMS state."""
        ctx = EvalContext(client=mock_client)

        await ctx.get_state("sms")

        mock_client.sms.get_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_state_calendar(self, mock_client):
        """Test getting calendar state."""
        ctx = EvalContext(client=mock_client)

        await ctx.get_state("calendar")

        mock_client.calendar.get_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_state_location(self, mock_client):
        """Test getting location state."""
        ctx = EvalContext(client=mock_client)

        await ctx.get_state("location")

        mock_client.location.get_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_state_weather(self, mock_client):
        """Test getting weather state."""
        ctx = EvalContext(client=mock_client)

        await ctx.get_state("weather")

        mock_client.weather.get_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_state_unknown_modality(self, mock_client):
        """Test that unknown modality raises ValueError."""
        ctx = EvalContext(client=mock_client)

        with pytest.raises(ValueError) as exc_info:
            await ctx.get_state("unknown_modality")

        assert "unknown modality" in str(exc_info.value).lower()
        assert "email" in str(exc_info.value).lower()  # Should list valid options

    @pytest.mark.asyncio
    async def test_get_time(self, mock_client):
        """Test getting simulation time."""
        from datetime import datetime, timezone

        ctx = EvalContext(client=mock_client)

        time = await ctx.get_time()

        mock_client.time.get_state.assert_called_once()
        assert isinstance(time, datetime)
        assert time.year == 2026

    @pytest.mark.asyncio
    async def test_get_events(self, mock_client):
        """Test getting events."""
        mock_events = [
            MagicMock(model_dump=MagicMock(return_value={"id": "1", "modality": "email", "status": "pending"})),
            MagicMock(model_dump=MagicMock(return_value={"id": "2", "modality": "sms", "status": "executed"})),
        ]
        mock_client.events.list = AsyncMock(return_value=mock_events)

        ctx = EvalContext(client=mock_client)

        events = await ctx.get_events()

        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_get_events_filter_modality(self, mock_client):
        """Test filtering events by modality."""
        mock_events = [
            MagicMock(model_dump=MagicMock(return_value={"id": "1", "modality": "email", "status": "pending"})),
            MagicMock(model_dump=MagicMock(return_value={"id": "2", "modality": "sms", "status": "pending"})),
        ]
        mock_client.events.list = AsyncMock(return_value=mock_events)

        ctx = EvalContext(client=mock_client)

        events = await ctx.get_events(modality="email")

        assert len(events) == 1
        assert events[0]["modality"] == "email"

    @pytest.mark.asyncio
    async def test_get_events_filter_status(self, mock_client):
        """Test filtering events by status."""
        mock_events = [
            MagicMock(model_dump=MagicMock(return_value={"id": "1", "modality": "email", "status": "pending"})),
            MagicMock(model_dump=MagicMock(return_value={"id": "2", "modality": "sms", "status": "executed"})),
        ]
        mock_client.events.list = AsyncMock(return_value=mock_events)

        ctx = EvalContext(client=mock_client)

        events = await ctx.get_events(status="pending")

        assert len(events) == 1
        assert events[0]["status"] == "pending"

    def test_with_trigger_event(self, mock_client):
        """Test creating context with trigger event."""
        ctx = EvalContext(
            client=mock_client,
            event_history=[{"id": "1"}],
            scenario_config={"name": "Test"},
        )

        trigger = {"id": "trigger", "modality": "email"}
        new_ctx = ctx.with_trigger_event(trigger)

        # New context should have trigger event
        assert new_ctx.trigger_event == trigger

        # Other fields should be preserved
        assert new_ctx.client == mock_client
        assert new_ctx.event_history == ctx.event_history
        assert new_ctx.scenario_config == ctx.scenario_config

        # Original should be unchanged
        assert ctx.trigger_event is None

    def test_add_event(self, mock_client):
        """Test adding event to history."""
        ctx = EvalContext(client=mock_client)

        assert len(ctx.event_history) == 0

        ctx.add_event({"id": "1", "modality": "email"})

        assert len(ctx.event_history) == 1
        assert ctx.event_history[0]["id"] == "1"

        ctx.add_event({"id": "2", "modality": "sms"})

        assert len(ctx.event_history) == 2
