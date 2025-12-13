"""Unit tests for the TimeClient and AsyncTimeClient.

This module tests the time control sub-clients defined in client/_time.py.
The tests verify:

1. Response Models:
   - TimeStateResponse, AdvanceTimeResponse, SetTimeResponse, etc.
   - Proper parsing of API responses into typed models

2. TimeClient (Synchronous):
   - get_state(): Get current simulator time state
   - advance(seconds): Advance time by a duration
   - set(target_time): Jump to a specific time
   - skip_to_next(): Jump to the next scheduled event
   - pause(): Pause automatic time advancement
   - resume(): Resume automatic time advancement
   - set_scale(scale): Change time multiplier

3. AsyncTimeClient:
   - Same functionality as TimeClient but async

Note: These tests use mock HTTP clients to avoid real network calls.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock

import pytest

from client._time import (
    TimeClient,
    AsyncTimeClient,
    TimeStateResponse,
    AdvanceTimeResponse,
    SetTimeResponse,
    SkipToNextResponse,
    PauseResumeResponse,
    EventExecutionDetail,
)


# =============================================================================
# Response Model Tests
# =============================================================================

class TestEventExecutionDetail:
    """Tests for the EventExecutionDetail response model."""
    
    def test_successful_event(self) -> None:
        """EventExecutionDetail can represent a successful event."""
        detail = EventExecutionDetail(
            event_id="evt_123",
            modality="email",
            status="executed",
            error=None,
        )
        
        assert detail.event_id == "evt_123"
        assert detail.modality == "email"
        assert detail.status == "executed"
        assert detail.error is None
    
    def test_failed_event(self) -> None:
        """EventExecutionDetail can represent a failed event with error."""
        detail = EventExecutionDetail(
            event_id="evt_456",
            modality="sms",
            status="failed",
            error="Invalid phone number format",
        )
        
        assert detail.event_id == "evt_456"
        assert detail.status == "failed"
        assert detail.error == "Invalid phone number format"


class TestTimeStateResponse:
    """Tests for the TimeStateResponse model."""
    
    def test_basic_state(self) -> None:
        """TimeStateResponse captures all time state fields."""
        state = TimeStateResponse(
            current_time=datetime(2024, 6, 15, 10, 30, 0, tzinfo=timezone.utc),
            time_scale=1.0,
            is_paused=False,
            auto_advance=False,
            mode="manual",
        )
        
        assert state.current_time == datetime(2024, 6, 15, 10, 30, 0, tzinfo=timezone.utc)
        assert state.time_scale == 1.0
        assert state.is_paused is False
        assert state.auto_advance is False
        assert state.mode == "manual"
    
    def test_auto_advance_mode(self) -> None:
        """TimeStateResponse can represent auto-advance mode."""
        state = TimeStateResponse(
            current_time=datetime(2024, 6, 15, 10, 30, 0, tzinfo=timezone.utc),
            time_scale=2.5,
            is_paused=False,
            auto_advance=True,
            mode="auto",
        )
        
        assert state.time_scale == 2.5
        assert state.auto_advance is True
        assert state.mode == "auto"
    
    def test_paused_state(self) -> None:
        """TimeStateResponse can represent paused state."""
        state = TimeStateResponse(
            current_time=datetime(2024, 6, 15, 10, 30, 0, tzinfo=timezone.utc),
            time_scale=1.0,
            is_paused=True,
            auto_advance=True,
            mode="paused",
        )
        
        assert state.is_paused is True
        assert state.mode == "paused"


class TestAdvanceTimeResponse:
    """Tests for the AdvanceTimeResponse model."""
    
    def test_no_events_executed(self) -> None:
        """AdvanceTimeResponse for time period with no events."""
        response = AdvanceTimeResponse(
            previous_time=datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc),
            current_time=datetime(2024, 6, 15, 11, 0, 0, tzinfo=timezone.utc),
            time_advanced="1:00:00",
            events_executed=0,
            events_failed=0,
            execution_details=[],
        )
        
        assert response.events_executed == 0
        assert response.events_failed == 0
        assert response.execution_details == []
    
    def test_with_executed_events(self) -> None:
        """AdvanceTimeResponse with events that were executed."""
        response = AdvanceTimeResponse(
            previous_time=datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc),
            current_time=datetime(2024, 6, 15, 11, 0, 0, tzinfo=timezone.utc),
            time_advanced="1:00:00",
            events_executed=2,
            events_failed=0,
            execution_details=[
                EventExecutionDetail(
                    event_id="evt_1",
                    modality="email",
                    status="executed",
                    error=None,
                ),
                EventExecutionDetail(
                    event_id="evt_2",
                    modality="sms",
                    status="executed",
                    error=None,
                ),
            ],
        )
        
        assert response.events_executed == 2
        assert len(response.execution_details) == 2
        assert response.execution_details[0].event_id == "evt_1"
    
    def test_with_failed_events(self) -> None:
        """AdvanceTimeResponse with some failed events."""
        response = AdvanceTimeResponse(
            previous_time=datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc),
            current_time=datetime(2024, 6, 15, 11, 0, 0, tzinfo=timezone.utc),
            time_advanced="1:00:00",
            events_executed=1,
            events_failed=1,
            execution_details=[
                EventExecutionDetail(
                    event_id="evt_1",
                    modality="email",
                    status="executed",
                    error=None,
                ),
                EventExecutionDetail(
                    event_id="evt_2",
                    modality="sms",
                    status="failed",
                    error="Delivery failed",
                ),
            ],
        )
        
        assert response.events_executed == 1
        assert response.events_failed == 1


class TestSetTimeResponse:
    """Tests for the SetTimeResponse model."""
    
    def test_jump_forward(self) -> None:
        """SetTimeResponse for jumping forward in time."""
        response = SetTimeResponse(
            current_time=datetime(2024, 6, 16, 0, 0, 0, tzinfo=timezone.utc),
            previous_time=datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc),
            skipped_events=5,
            executed_events=0,
        )
        
        assert response.current_time > response.previous_time
        assert response.skipped_events == 5
        assert response.executed_events == 0


class TestSkipToNextResponse:
    """Tests for the SkipToNextResponse model."""
    
    def test_skip_with_next_event(self) -> None:
        """SkipToNextResponse when more events are pending."""
        response = SkipToNextResponse(
            previous_time=datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc),
            current_time=datetime(2024, 6, 15, 10, 30, 0, tzinfo=timezone.utc),
            events_executed=1,
            next_event_time=datetime(2024, 6, 15, 11, 0, 0, tzinfo=timezone.utc),
        )
        
        assert response.events_executed == 1
        assert response.next_event_time is not None
    
    def test_skip_no_more_events(self) -> None:
        """SkipToNextResponse when no more events are pending."""
        response = SkipToNextResponse(
            previous_time=datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc),
            current_time=datetime(2024, 6, 15, 10, 30, 0, tzinfo=timezone.utc),
            events_executed=1,
            next_event_time=None,
        )
        
        assert response.next_event_time is None


class TestPauseResumeResponse:
    """Tests for the PauseResumeResponse model."""
    
    def test_paused_response(self) -> None:
        """PauseResumeResponse after pausing."""
        response = PauseResumeResponse(
            message="Simulation paused",
            current_time=datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc),
            is_paused=True,
        )
        
        assert "paused" in response.message.lower()
        assert response.is_paused is True
    
    def test_resumed_response(self) -> None:
        """PauseResumeResponse after resuming."""
        response = PauseResumeResponse(
            message="Simulation resumed",
            current_time=datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc),
            is_paused=False,
        )
        
        assert "resumed" in response.message.lower()
        assert response.is_paused is False


# =============================================================================
# TimeClient Tests (Synchronous)
# =============================================================================

class TestTimeClientGetState:
    """Tests for TimeClient.get_state()."""
    
    def test_get_state_returns_response_model(self) -> None:
        """get_state() returns a TimeStateResponse model."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "current_time": "2024-06-15T10:30:00+00:00",
            "time_scale": 1.0,
            "is_paused": False,
            "auto_advance": False,
            "mode": "manual",
        }
        
        client = TimeClient(mock_http)
        result = client.get_state()
        
        assert isinstance(result, TimeStateResponse)
        assert result.time_scale == 1.0
        assert result.mode == "manual"
    
    def test_get_state_calls_correct_endpoint(self) -> None:
        """get_state() calls the correct API endpoint."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "current_time": "2024-06-15T10:30:00+00:00",
            "time_scale": 1.0,
            "is_paused": False,
            "auto_advance": False,
            "mode": "manual",
        }
        
        client = TimeClient(mock_http)
        client.get_state()
        
        mock_http.get.assert_called_once_with("/simulator/time", params=None)


class TestTimeClientAdvance:
    """Tests for TimeClient.advance()."""
    
    def test_advance_returns_response_model(self) -> None:
        """advance() returns an AdvanceTimeResponse model."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "previous_time": "2024-06-15T10:00:00+00:00",
            "current_time": "2024-06-15T11:00:00+00:00",
            "time_advanced": "1:00:00",
            "events_executed": 3,
            "events_failed": 0,
            "execution_details": [],
        }
        
        client = TimeClient(mock_http)
        result = client.advance(seconds=3600)
        
        assert isinstance(result, AdvanceTimeResponse)
        assert result.events_executed == 3
    
    def test_advance_sends_seconds_in_body(self) -> None:
        """advance() sends the seconds parameter in the request body."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "previous_time": "2024-06-15T10:00:00+00:00",
            "current_time": "2024-06-15T10:05:00+00:00",
            "time_advanced": "0:05:00",
            "events_executed": 0,
            "events_failed": 0,
            "execution_details": [],
        }
        
        client = TimeClient(mock_http)
        client.advance(seconds=300)
        
        mock_http.post.assert_called_once_with(
            "/simulator/time/advance",
            json={"seconds": 300},
            params=None,
        )
    
    def test_advance_with_fractional_seconds(self) -> None:
        """advance() supports fractional seconds."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "previous_time": "2024-06-15T10:00:00+00:00",
            "current_time": "2024-06-15T10:00:01.500000+00:00",
            "time_advanced": "0:00:01.500000",
            "events_executed": 0,
            "events_failed": 0,
            "execution_details": [],
        }
        
        client = TimeClient(mock_http)
        client.advance(seconds=1.5)
        
        mock_http.post.assert_called_once_with(
            "/simulator/time/advance",
            json={"seconds": 1.5},
            params=None,
        )


class TestTimeClientSet:
    """Tests for TimeClient.set()."""
    
    def test_set_returns_response_model(self) -> None:
        """set() returns a SetTimeResponse model."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "current_time": "2024-06-16T00:00:00+00:00",
            "previous_time": "2024-06-15T10:00:00+00:00",
            "skipped_events": 5,
            "executed_events": 0,
        }
        
        client = TimeClient(mock_http)
        target = datetime(2024, 6, 16, 0, 0, 0, tzinfo=timezone.utc)
        result = client.set(target_time=target)
        
        assert isinstance(result, SetTimeResponse)
        assert result.skipped_events == 5
    
    def test_set_sends_iso_format_time(self) -> None:
        """set() sends the target time in ISO format."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "current_time": "2024-06-16T00:00:00+00:00",
            "previous_time": "2024-06-15T10:00:00+00:00",
            "skipped_events": 0,
            "executed_events": 0,
        }
        
        client = TimeClient(mock_http)
        target = datetime(2024, 6, 16, 0, 0, 0, tzinfo=timezone.utc)
        client.set(target_time=target)
        
        mock_http.post.assert_called_once_with(
            "/simulator/time/set",
            json={"target_time": "2024-06-16T00:00:00+00:00"},
            params=None,
        )
    
    def test_set_handles_naive_datetime(self) -> None:
        """set() handles naive datetime objects."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "current_time": "2024-06-16T00:00:00",
            "previous_time": "2024-06-15T10:00:00",
            "skipped_events": 0,
            "executed_events": 0,
        }
        
        client = TimeClient(mock_http)
        # Naive datetime (no timezone)
        target = datetime(2024, 6, 16, 0, 0, 0)
        client.set(target_time=target)
        
        # Should still serialize correctly
        mock_http.post.assert_called_once()
        call_args = mock_http.post.call_args
        assert "2024-06-16T00:00:00" in call_args.kwargs["json"]["target_time"]


class TestTimeClientSkipToNext:
    """Tests for TimeClient.skip_to_next()."""
    
    def test_skip_to_next_returns_response_model(self) -> None:
        """skip_to_next() returns a SkipToNextResponse model."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "previous_time": "2024-06-15T10:00:00+00:00",
            "current_time": "2024-06-15T10:30:00+00:00",
            "events_executed": 2,
            "next_event_time": "2024-06-15T11:00:00+00:00",
        }
        
        client = TimeClient(mock_http)
        result = client.skip_to_next()
        
        assert isinstance(result, SkipToNextResponse)
        assert result.events_executed == 2
        assert result.next_event_time is not None
    
    def test_skip_to_next_calls_correct_endpoint(self) -> None:
        """skip_to_next() calls the correct API endpoint."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "previous_time": "2024-06-15T10:00:00+00:00",
            "current_time": "2024-06-15T10:30:00+00:00",
            "events_executed": 1,
            "next_event_time": None,
        }
        
        client = TimeClient(mock_http)
        client.skip_to_next()
        
        mock_http.post.assert_called_once_with(
            "/simulator/time/skip-to-next",
            json=None,
            params=None,
        )
    
    def test_skip_to_next_handles_no_next_event(self) -> None:
        """skip_to_next() handles None next_event_time."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "previous_time": "2024-06-15T10:00:00+00:00",
            "current_time": "2024-06-15T10:30:00+00:00",
            "events_executed": 1,
            "next_event_time": None,
        }
        
        client = TimeClient(mock_http)
        result = client.skip_to_next()
        
        assert result.next_event_time is None


class TestTimeClientPause:
    """Tests for TimeClient.pause()."""
    
    def test_pause_returns_response_model(self) -> None:
        """pause() returns a PauseResumeResponse model."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "message": "Simulation paused",
            "current_time": "2024-06-15T10:00:00+00:00",
            "is_paused": True,
        }
        
        client = TimeClient(mock_http)
        result = client.pause()
        
        assert isinstance(result, PauseResumeResponse)
        assert result.is_paused is True
    
    def test_pause_calls_correct_endpoint(self) -> None:
        """pause() calls the correct API endpoint."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "message": "Simulation paused",
            "current_time": "2024-06-15T10:00:00+00:00",
            "is_paused": True,
        }
        
        client = TimeClient(mock_http)
        client.pause()
        
        mock_http.post.assert_called_once_with(
            "/simulator/time/pause",
            json=None,
            params=None,
        )


class TestTimeClientResume:
    """Tests for TimeClient.resume()."""
    
    def test_resume_returns_response_model(self) -> None:
        """resume() returns a PauseResumeResponse model."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "message": "Simulation resumed",
            "current_time": "2024-06-15T10:00:00+00:00",
            "is_paused": False,
        }
        
        client = TimeClient(mock_http)
        result = client.resume()
        
        assert isinstance(result, PauseResumeResponse)
        assert result.is_paused is False
    
    def test_resume_calls_correct_endpoint(self) -> None:
        """resume() calls the correct API endpoint."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "message": "Simulation resumed",
            "current_time": "2024-06-15T10:00:00+00:00",
            "is_paused": False,
        }
        
        client = TimeClient(mock_http)
        client.resume()
        
        mock_http.post.assert_called_once_with(
            "/simulator/time/resume",
            json=None,
            params=None,
        )


class TestTimeClientSetScale:
    """Tests for TimeClient.set_scale()."""
    
    def test_set_scale_returns_response_model(self) -> None:
        """set_scale() returns a TimeStateResponse model."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "current_time": "2024-06-15T10:00:00+00:00",
            "time_scale": 2.0,
            "is_paused": False,
            "auto_advance": True,
            "mode": "auto",
        }
        
        client = TimeClient(mock_http)
        result = client.set_scale(scale=2.0)
        
        assert isinstance(result, TimeStateResponse)
        assert result.time_scale == 2.0
    
    def test_set_scale_sends_scale_in_body(self) -> None:
        """set_scale() sends the scale parameter in the request body."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "current_time": "2024-06-15T10:00:00+00:00",
            "time_scale": 10.0,
            "is_paused": False,
            "auto_advance": True,
            "mode": "auto",
        }
        
        client = TimeClient(mock_http)
        client.set_scale(scale=10.0)
        
        mock_http.post.assert_called_once_with(
            "/simulator/time/set-scale",
            json={"scale": 10.0},
            params=None,
        )
    
    def test_set_scale_fractional_values(self) -> None:
        """set_scale() supports fractional scale values."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "current_time": "2024-06-15T10:00:00+00:00",
            "time_scale": 0.5,
            "is_paused": False,
            "auto_advance": True,
            "mode": "auto",
        }
        
        client = TimeClient(mock_http)
        client.set_scale(scale=0.5)
        
        mock_http.post.assert_called_once_with(
            "/simulator/time/set-scale",
            json={"scale": 0.5},
            params=None,
        )


# =============================================================================
# AsyncTimeClient Tests
# =============================================================================

class TestAsyncTimeClientGetState:
    """Tests for AsyncTimeClient.get_state()."""
    
    async def test_get_state_returns_response_model(self) -> None:
        """get_state() returns a TimeStateResponse model."""
        mock_http = MagicMock()
        mock_http.get = AsyncMock(return_value={
            "current_time": "2024-06-15T10:30:00+00:00",
            "time_scale": 1.0,
            "is_paused": False,
            "auto_advance": False,
            "mode": "manual",
        })
        
        client = AsyncTimeClient(mock_http)
        result = await client.get_state()
        
        assert isinstance(result, TimeStateResponse)
        assert result.mode == "manual"
    
    async def test_get_state_calls_correct_endpoint(self) -> None:
        """get_state() calls the correct API endpoint."""
        mock_http = MagicMock()
        mock_http.get = AsyncMock(return_value={
            "current_time": "2024-06-15T10:30:00+00:00",
            "time_scale": 1.0,
            "is_paused": False,
            "auto_advance": False,
            "mode": "manual",
        })
        
        client = AsyncTimeClient(mock_http)
        await client.get_state()
        
        mock_http.get.assert_called_once_with("/simulator/time", params=None)


class TestAsyncTimeClientAdvance:
    """Tests for AsyncTimeClient.advance()."""
    
    async def test_advance_returns_response_model(self) -> None:
        """advance() returns an AdvanceTimeResponse model."""
        mock_http = MagicMock()
        mock_http.post = AsyncMock(return_value={
            "previous_time": "2024-06-15T10:00:00+00:00",
            "current_time": "2024-06-15T11:00:00+00:00",
            "time_advanced": "1:00:00",
            "events_executed": 5,
            "events_failed": 0,
            "execution_details": [],
        })
        
        client = AsyncTimeClient(mock_http)
        result = await client.advance(seconds=3600)
        
        assert isinstance(result, AdvanceTimeResponse)
        assert result.events_executed == 5
    
    async def test_advance_sends_seconds_in_body(self) -> None:
        """advance() sends the seconds parameter in the request body."""
        mock_http = MagicMock()
        mock_http.post = AsyncMock(return_value={
            "previous_time": "2024-06-15T10:00:00+00:00",
            "current_time": "2024-06-15T10:01:00+00:00",
            "time_advanced": "0:01:00",
            "events_executed": 0,
            "events_failed": 0,
            "execution_details": [],
        })
        
        client = AsyncTimeClient(mock_http)
        await client.advance(seconds=60)
        
        mock_http.post.assert_called_once_with(
            "/simulator/time/advance",
            json={"seconds": 60},
            params=None,
        )


class TestAsyncTimeClientSet:
    """Tests for AsyncTimeClient.set()."""
    
    async def test_set_returns_response_model(self) -> None:
        """set() returns a SetTimeResponse model."""
        mock_http = MagicMock()
        mock_http.post = AsyncMock(return_value={
            "current_time": "2024-06-20T00:00:00+00:00",
            "previous_time": "2024-06-15T10:00:00+00:00",
            "skipped_events": 10,
            "executed_events": 0,
        })
        
        client = AsyncTimeClient(mock_http)
        target = datetime(2024, 6, 20, 0, 0, 0, tzinfo=timezone.utc)
        result = await client.set(target_time=target)
        
        assert isinstance(result, SetTimeResponse)
        assert result.skipped_events == 10
    
    async def test_set_sends_iso_format_time(self) -> None:
        """set() sends the target time in ISO format."""
        mock_http = MagicMock()
        mock_http.post = AsyncMock(return_value={
            "current_time": "2024-06-20T12:30:00+00:00",
            "previous_time": "2024-06-15T10:00:00+00:00",
            "skipped_events": 0,
            "executed_events": 0,
        })
        
        client = AsyncTimeClient(mock_http)
        target = datetime(2024, 6, 20, 12, 30, 0, tzinfo=timezone.utc)
        await client.set(target_time=target)
        
        mock_http.post.assert_called_once_with(
            "/simulator/time/set",
            json={"target_time": "2024-06-20T12:30:00+00:00"},
            params=None,
        )


class TestAsyncTimeClientSkipToNext:
    """Tests for AsyncTimeClient.skip_to_next()."""
    
    async def test_skip_to_next_returns_response_model(self) -> None:
        """skip_to_next() returns a SkipToNextResponse model."""
        mock_http = MagicMock()
        mock_http.post = AsyncMock(return_value={
            "previous_time": "2024-06-15T10:00:00+00:00",
            "current_time": "2024-06-15T12:00:00+00:00",
            "events_executed": 3,
            "next_event_time": "2024-06-15T14:00:00+00:00",
        })
        
        client = AsyncTimeClient(mock_http)
        result = await client.skip_to_next()
        
        assert isinstance(result, SkipToNextResponse)
        assert result.events_executed == 3
    
    async def test_skip_to_next_calls_correct_endpoint(self) -> None:
        """skip_to_next() calls the correct API endpoint."""
        mock_http = MagicMock()
        mock_http.post = AsyncMock(return_value={
            "previous_time": "2024-06-15T10:00:00+00:00",
            "current_time": "2024-06-15T10:30:00+00:00",
            "events_executed": 1,
            "next_event_time": None,
        })
        
        client = AsyncTimeClient(mock_http)
        await client.skip_to_next()
        
        mock_http.post.assert_called_once_with(
            "/simulator/time/skip-to-next",
            json=None,
            params=None,
        )


class TestAsyncTimeClientPause:
    """Tests for AsyncTimeClient.pause()."""
    
    async def test_pause_returns_response_model(self) -> None:
        """pause() returns a PauseResumeResponse model."""
        mock_http = MagicMock()
        mock_http.post = AsyncMock(return_value={
            "message": "Simulation paused",
            "current_time": "2024-06-15T10:00:00+00:00",
            "is_paused": True,
        })
        
        client = AsyncTimeClient(mock_http)
        result = await client.pause()
        
        assert isinstance(result, PauseResumeResponse)
        assert result.is_paused is True
    
    async def test_pause_calls_correct_endpoint(self) -> None:
        """pause() calls the correct API endpoint."""
        mock_http = MagicMock()
        mock_http.post = AsyncMock(return_value={
            "message": "Simulation paused",
            "current_time": "2024-06-15T10:00:00+00:00",
            "is_paused": True,
        })
        
        client = AsyncTimeClient(mock_http)
        await client.pause()
        
        mock_http.post.assert_called_once_with(
            "/simulator/time/pause",
            json=None,
            params=None,
        )


class TestAsyncTimeClientResume:
    """Tests for AsyncTimeClient.resume()."""
    
    async def test_resume_returns_response_model(self) -> None:
        """resume() returns a PauseResumeResponse model."""
        mock_http = MagicMock()
        mock_http.post = AsyncMock(return_value={
            "message": "Simulation resumed",
            "current_time": "2024-06-15T10:00:00+00:00",
            "is_paused": False,
        })
        
        client = AsyncTimeClient(mock_http)
        result = await client.resume()
        
        assert isinstance(result, PauseResumeResponse)
        assert result.is_paused is False
    
    async def test_resume_calls_correct_endpoint(self) -> None:
        """resume() calls the correct API endpoint."""
        mock_http = MagicMock()
        mock_http.post = AsyncMock(return_value={
            "message": "Simulation resumed",
            "current_time": "2024-06-15T10:00:00+00:00",
            "is_paused": False,
        })
        
        client = AsyncTimeClient(mock_http)
        await client.resume()
        
        mock_http.post.assert_called_once_with(
            "/simulator/time/resume",
            json=None,
            params=None,
        )


class TestAsyncTimeClientSetScale:
    """Tests for AsyncTimeClient.set_scale()."""
    
    async def test_set_scale_returns_response_model(self) -> None:
        """set_scale() returns a TimeStateResponse model."""
        mock_http = MagicMock()
        mock_http.post = AsyncMock(return_value={
            "current_time": "2024-06-15T10:00:00+00:00",
            "time_scale": 5.0,
            "is_paused": False,
            "auto_advance": True,
            "mode": "auto",
        })
        
        client = AsyncTimeClient(mock_http)
        result = await client.set_scale(scale=5.0)
        
        assert isinstance(result, TimeStateResponse)
        assert result.time_scale == 5.0
    
    async def test_set_scale_sends_scale_in_body(self) -> None:
        """set_scale() sends the scale parameter in the request body."""
        mock_http = MagicMock()
        mock_http.post = AsyncMock(return_value={
            "current_time": "2024-06-15T10:00:00+00:00",
            "time_scale": 0.25,
            "is_paused": False,
            "auto_advance": True,
            "mode": "auto",
        })
        
        client = AsyncTimeClient(mock_http)
        await client.set_scale(scale=0.25)
        
        mock_http.post.assert_called_once_with(
            "/simulator/time/set-scale",
            json={"scale": 0.25},
            params=None,
        )


# =============================================================================
# Base Path Tests
# =============================================================================

class TestTimeClientBasePath:
    """Tests verifying the base path configuration."""
    
    def test_sync_client_base_path(self) -> None:
        """TimeClient uses the correct base path."""
        assert TimeClient._BASE_PATH == "/simulator/time"
    
    def test_async_client_base_path(self) -> None:
        """AsyncTimeClient uses the correct base path."""
        assert AsyncTimeClient._BASE_PATH == "/simulator/time"
