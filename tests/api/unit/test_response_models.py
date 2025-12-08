"""Unit tests for API response model validation and serialization.

This module tests that response models properly serialize data, have correct
default values, and maintain their expected structure.

Test Organization:
- Common response models from api/models.py (ModalityStateResponse, etc.)
- Simulation response models (StartSimulationResponse, StopSimulationResponse, etc.)
- Time control response models (TimeStateResponse, SetTimeResponse, etc.)
- Event response models (EventResponse, EventListResponse, EventSummaryResponse)
- Environment response models (EnvironmentStateResponse, ModalityListResponse, etc.)
- Chat response models (ChatStateResponse, ChatQueryResponse)
- Location response models (LocationStateResponse, LocationQueryResponse)
- Weather response models (WeatherStateResponse, WeatherQueryResponse)
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

# Common response models from api/models.py
from api.models import (
    ErrorResponse,
    ModalityActionResponse,
    ModalityQueryResponse,
    ModalityStateResponse,
)

# Simulation response models
from api.routes.simulation import (
    ResetSimulationResponse,
    SimulationStatusResponse,
    StartSimulationResponse,
    StopSimulationResponse,
)

# Time response models
from api.routes.time import SetTimeResponse, SkipToNextResponse, TimeStateResponse

# Event response models
from api.routes.events import EventListResponse, EventResponse, EventSummaryResponse

# Environment response models
from api.routes.environment import (
    EnvironmentStateResponse,
    ModalityListResponse,
    ModalitySummary,
    ValidationResponse,
)

# Chat response models
from api.routes.chat import ChatQueryResponse, ChatStateResponse

# Location response models
from api.routes.location import LocationQueryResponse, LocationStateResponse

# Weather response models
from api.routes.weather import WeatherQueryResponse, WeatherStateResponse


# =============================================================================
# Common Response Models (api/models.py)
# =============================================================================


class TestModalityStateResponse:
    """Tests for ModalityStateResponse generic model."""

    def test_valid_response_with_dict_state(self):
        """Test creating response with dict state."""
        now = datetime.now(timezone.utc)
        response = ModalityStateResponse(
            modality_type="email",
            current_time=now,
            state={"inbox": [], "sent": []},
        )
        assert response.modality_type == "email"
        assert response.current_time == now
        assert response.state == {"inbox": [], "sent": []}

    def test_valid_response_with_list_state(self):
        """Test creating response with list state."""
        now = datetime.now(timezone.utc)
        response = ModalityStateResponse(
            modality_type="sms",
            current_time=now,
            state=[{"id": "msg-1", "body": "Hello"}],
        )
        assert response.state == [{"id": "msg-1", "body": "Hello"}]

    def test_missing_required_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError) as exc_info:
            ModalityStateResponse(modality_type="email")
        errors = str(exc_info.value)
        assert "current_time" in errors
        assert "state" in errors

    def test_serialization(self):
        """Test model serializes to dict correctly."""
        now = datetime.now(timezone.utc)
        response = ModalityStateResponse(
            modality_type="chat",
            current_time=now,
            state={"messages": []},
        )
        data = response.model_dump()
        assert data["modality_type"] == "chat"
        assert data["current_time"] == now
        assert data["state"] == {"messages": []}


class TestModalityActionResponse:
    """Tests for ModalityActionResponse model."""

    def test_valid_response(self):
        """Test creating a valid action response."""
        now = datetime.now(timezone.utc)
        response = ModalityActionResponse(
            event_id="evt-123",
            scheduled_time=now,
            status="pending",
            message="Email queued for delivery",
            modality="email",
        )
        assert response.event_id == "evt-123"
        assert response.scheduled_time == now
        assert response.status == "pending"
        assert response.message == "Email queued for delivery"
        assert response.modality == "email"

    def test_all_fields_required(self):
        """Test that all fields are required."""
        with pytest.raises(ValidationError) as exc_info:
            ModalityActionResponse(event_id="evt-123")
        errors = str(exc_info.value)
        assert "scheduled_time" in errors
        assert "status" in errors
        assert "message" in errors
        assert "modality" in errors

    def test_serialization(self):
        """Test model serializes correctly."""
        now = datetime.now(timezone.utc)
        response = ModalityActionResponse(
            event_id="evt-456",
            scheduled_time=now,
            status="executed",
            message="Message sent",
            modality="sms",
        )
        data = response.model_dump()
        assert "event_id" in data
        assert "scheduled_time" in data
        assert "status" in data
        assert "message" in data
        assert "modality" in data


class TestModalityQueryResponse:
    """Tests for ModalityQueryResponse generic model."""

    def test_valid_response(self):
        """Test creating a valid query response."""
        response = ModalityQueryResponse(
            modality_type="email",
            query={"folder": "inbox", "is_read": False},
            results=[{"id": "msg-1"}, {"id": "msg-2"}],
            total_count=10,
            returned_count=2,
        )
        assert response.modality_type == "email"
        assert response.query == {"folder": "inbox", "is_read": False}
        assert len(response.results) == 2
        assert response.total_count == 10
        assert response.returned_count == 2

    def test_required_fields(self):
        """Test required fields are enforced."""
        with pytest.raises(ValidationError) as exc_info:
            ModalityQueryResponse(modality_type="email")
        errors = str(exc_info.value)
        assert "query" in errors
        assert "results" in errors
        assert "total_count" in errors
        assert "returned_count" in errors


class TestErrorResponse:
    """Tests for ErrorResponse model."""

    def test_valid_error_response(self):
        """Test creating a valid error response."""
        response = ErrorResponse(
            error="SIMULATION_NOT_RUNNING",
            message="The simulation has not been started",
        )
        assert response.error == "SIMULATION_NOT_RUNNING"
        assert response.message == "The simulation has not been started"
        assert response.details is None

    def test_error_with_details(self):
        """Test error response with additional details."""
        response = ErrorResponse(
            error="VALIDATION_ERROR",
            message="Request validation failed",
            details={"field": "email", "reason": "Invalid format"},
        )
        assert response.details == {"field": "email", "reason": "Invalid format"}

    def test_required_fields(self):
        """Test that error and message are required."""
        with pytest.raises(ValidationError) as exc_info:
            ErrorResponse(error="TEST_ERROR")
        assert "message" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            ErrorResponse(message="Something went wrong")
        assert "error" in str(exc_info.value)


# =============================================================================
# Simulation Response Models
# =============================================================================


class TestStartSimulationResponse:
    """Tests for StartSimulationResponse model."""

    def test_valid_response(self):
        """Test creating a valid start simulation response."""
        response = StartSimulationResponse(
            simulation_id="sim-abc123",
            status="running",
            current_time="2024-06-15T10:00:00+00:00",
            auto_advance=True,
            time_scale=2.0,
        )
        assert response.simulation_id == "sim-abc123"
        assert response.status == "running"
        assert response.auto_advance is True
        assert response.time_scale == 2.0

    def test_optional_time_scale(self):
        """Test that time_scale is optional."""
        response = StartSimulationResponse(
            simulation_id="sim-123",
            status="running",
            current_time="2024-06-15T10:00:00+00:00",
            auto_advance=False,
        )
        assert response.time_scale is None

    def test_required_fields(self):
        """Test required fields are enforced."""
        with pytest.raises(ValidationError) as exc_info:
            StartSimulationResponse(simulation_id="sim-123")
        errors = str(exc_info.value)
        assert "status" in errors
        assert "current_time" in errors
        assert "auto_advance" in errors


class TestStopSimulationResponse:
    """Tests for StopSimulationResponse model."""

    def test_valid_response_with_statistics(self):
        """Test stop response with all optional statistics."""
        response = StopSimulationResponse(
            simulation_id="sim-123",
            status="stopped",
            final_time="2024-06-15T12:00:00+00:00",
            total_events=100,
            events_executed=95,
            events_failed=5,
        )
        assert response.simulation_id == "sim-123"
        assert response.status == "stopped"
        assert response.final_time == "2024-06-15T12:00:00+00:00"
        assert response.total_events == 100
        assert response.events_executed == 95
        assert response.events_failed == 5

    def test_minimal_response(self):
        """Test stop response with only required fields."""
        response = StopSimulationResponse(
            simulation_id="sim-123",
            status="stopped",
        )
        assert response.final_time is None
        assert response.total_events is None
        assert response.events_executed is None
        assert response.events_failed is None


class TestSimulationStatusResponse:
    """Tests for SimulationStatusResponse model."""

    def test_valid_response(self):
        """Test creating a valid status response."""
        response = SimulationStatusResponse(
            is_running=True,
            current_time="2024-06-15T10:30:00+00:00",
            is_paused=False,
            auto_advance=False,
            time_scale=1.0,
            pending_events=10,
            executed_events=50,
            failed_events=2,
            next_event_time="2024-06-15T10:31:00+00:00",
        )
        assert response.is_running is True
        assert response.is_paused is False
        assert response.auto_advance is False
        assert response.time_scale == 1.0
        assert response.pending_events == 10
        assert response.executed_events == 50
        assert response.failed_events == 2
        assert response.next_event_time == "2024-06-15T10:31:00+00:00"

    def test_optional_next_event_time(self):
        """Test that next_event_time is optional."""
        response = SimulationStatusResponse(
            is_running=True,
            current_time="2024-06-15T10:30:00+00:00",
            is_paused=False,
            auto_advance=False,
            time_scale=1.0,
            pending_events=0,
            executed_events=100,
            failed_events=0,
        )
        assert response.next_event_time is None


class TestResetSimulationResponse:
    """Tests for ResetSimulationResponse model."""

    def test_valid_response(self):
        """Test creating a valid reset response."""
        response = ResetSimulationResponse(
            status="reset",
            message="Simulation reset to initial state",
            cleared_events=150,
        )
        assert response.status == "reset"
        assert response.message == "Simulation reset to initial state"
        assert response.cleared_events == 150


# =============================================================================
# Time Response Models
# =============================================================================


class TestTimeStateResponse:
    """Tests for TimeStateResponse model."""

    def test_valid_response(self):
        """Test creating a valid time state response."""
        now = datetime.now(timezone.utc)
        response = TimeStateResponse(
            current_time=now,
            time_scale=1.0,
            is_paused=False,
            auto_advance=True,
            mode="manual",
        )
        assert response.current_time == now
        assert response.time_scale == 1.0
        assert response.is_paused is False
        assert response.auto_advance is True
        assert response.mode == "manual"

    def test_all_fields_required(self):
        """Test that all fields are required."""
        with pytest.raises(ValidationError) as exc_info:
            TimeStateResponse(current_time=datetime.now(timezone.utc))
        errors = str(exc_info.value)
        assert "time_scale" in errors
        assert "is_paused" in errors
        assert "mode" in errors
        assert "auto_advance" in errors


class TestSetTimeResponse:
    """Tests for SetTimeResponse model."""

    def test_valid_response(self):
        """Test creating a valid set time response."""
        current = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        previous = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        response = SetTimeResponse(
            current_time=current,
            previous_time=previous,
            skipped_events=5,
            executed_events=0,
        )
        assert response.current_time == current
        assert response.previous_time == previous
        assert response.skipped_events == 5
        assert response.executed_events == 0


class TestSkipToNextResponse:
    """Tests for SkipToNextResponse model."""

    def test_valid_response_with_next_event(self):
        """Test response when there's a next event."""
        previous = datetime(2024, 6, 15, 11, 0, 0, tzinfo=timezone.utc)
        current = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        next_time = datetime(2024, 6, 15, 13, 0, 0, tzinfo=timezone.utc)
        response = SkipToNextResponse(
            previous_time=previous,
            current_time=current,
            events_executed=3,
            next_event_time=next_time,
        )
        assert response.previous_time == previous
        assert response.current_time == current
        assert response.events_executed == 3
        assert response.next_event_time == next_time

    def test_response_without_next_event(self):
        """Test response when no more events pending."""
        previous = datetime(2024, 6, 15, 11, 0, 0, tzinfo=timezone.utc)
        current = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        response = SkipToNextResponse(
            previous_time=previous,
            current_time=current,
            events_executed=1,
        )
        assert response.next_event_time is None


# =============================================================================
# Event Response Models
# =============================================================================


class TestEventResponse:
    """Tests for EventResponse model."""

    def test_valid_response(self):
        """Test creating a valid event response."""
        scheduled = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        created = datetime(2024, 6, 14, 9, 0, 0, tzinfo=timezone.utc)
        response = EventResponse(
            event_id="evt-123",
            scheduled_time=scheduled,
            modality="email",
            status="pending",
            priority=50,
            created_at=created,
        )
        assert response.event_id == "evt-123"
        assert response.scheduled_time == scheduled
        assert response.modality == "email"
        assert response.status == "pending"
        assert response.priority == 50
        assert response.created_at == created
        assert response.executed_at is None
        assert response.error_message is None

    def test_executed_event(self):
        """Test response for an executed event."""
        scheduled = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        created = datetime(2024, 6, 14, 9, 0, 0, tzinfo=timezone.utc)
        executed = datetime(2024, 6, 15, 10, 0, 1, tzinfo=timezone.utc)
        response = EventResponse(
            event_id="evt-123",
            scheduled_time=scheduled,
            modality="sms",
            status="executed",
            priority=75,
            created_at=created,
            executed_at=executed,
        )
        assert response.executed_at == executed
        assert response.error_message is None

    def test_failed_event(self):
        """Test response for a failed event."""
        scheduled = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        created = datetime(2024, 6, 14, 9, 0, 0, tzinfo=timezone.utc)
        response = EventResponse(
            event_id="evt-123",
            scheduled_time=scheduled,
            modality="chat",
            status="failed",
            priority=50,
            created_at=created,
            error_message="Connection timeout",
        )
        assert response.status == "failed"
        assert response.error_message == "Connection timeout"


class TestEventListResponse:
    """Tests for EventListResponse model."""

    def test_valid_response(self):
        """Test creating a valid event list response."""
        scheduled = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        created = datetime(2024, 6, 14, 9, 0, 0, tzinfo=timezone.utc)
        event = EventResponse(
            event_id="evt-1",
            scheduled_time=scheduled,
            modality="email",
            status="pending",
            priority=50,
            created_at=created,
        )
        response = EventListResponse(
            events=[event],
            total=100,
            pending=50,
            executed=45,
            failed=3,
            skipped=2,
        )
        assert len(response.events) == 1
        assert response.total == 100
        assert response.pending == 50
        assert response.executed == 45
        assert response.failed == 3
        assert response.skipped == 2

    def test_empty_events_list(self):
        """Test response with empty events list."""
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
    """Tests for EventSummaryResponse model."""

    def test_valid_response(self):
        """Test creating a valid event summary response."""
        next_time = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        response = EventSummaryResponse(
            total=100,
            pending=25,
            executed=70,
            failed=3,
            skipped=2,
            by_modality={"email": 40, "sms": 30, "chat": 30},
            next_event_time=next_time,
        )
        assert response.total == 100
        assert response.pending == 25
        assert response.executed == 70
        assert response.failed == 3
        assert response.skipped == 2
        assert response.by_modality == {"email": 40, "sms": 30, "chat": 30}
        assert response.next_event_time == next_time

    def test_no_pending_events(self):
        """Test response when no events are pending."""
        response = EventSummaryResponse(
            total=100,
            pending=0,
            executed=100,
            failed=0,
            skipped=0,
            by_modality={"email": 100},
        )
        assert response.next_event_time is None


# =============================================================================
# Environment Response Models
# =============================================================================


class TestModalitySummary:
    """Tests for ModalitySummary model."""

    def test_valid_summary(self):
        """Test creating a valid modality summary."""
        summary = ModalitySummary(
            modality_type="email",
            state_summary="10 messages in inbox, 5 sent",
        )
        assert summary.modality_type == "email"
        assert summary.state_summary == "10 messages in inbox, 5 sent"


class TestEnvironmentStateResponse:
    """Tests for EnvironmentStateResponse model."""

    def test_valid_response(self):
        """Test creating a valid environment state response."""
        summary = ModalitySummary(
            modality_type="email",
            state_summary="email state with 5 fields",
        )
        response = EnvironmentStateResponse(
            current_time="2024-06-15T10:00:00+00:00",
            modalities={"email": {"inbox": [], "sent": []}},
            summary=[summary],
        )
        assert response.current_time == "2024-06-15T10:00:00+00:00"
        assert "email" in response.modalities
        assert len(response.summary) == 1

    def test_modalities_is_required(self):
        """Test that modalities field is required."""
        with pytest.raises(ValidationError) as exc_info:
            EnvironmentStateResponse(
                current_time="2024-06-15T10:00:00+00:00",
                summary=[],
            )
        assert "modalities" in str(exc_info.value)


class TestModalityListResponse:
    """Tests for ModalityListResponse model."""

    def test_valid_response(self):
        """Test creating a valid modality list response."""
        response = ModalityListResponse(
            modalities=["email", "sms", "chat", "calendar"],
            count=4,
        )
        assert len(response.modalities) == 4
        assert response.count == 4
        assert "email" in response.modalities

    def test_empty_modalities(self):
        """Test response with no modalities."""
        response = ModalityListResponse(
            modalities=[],
            count=0,
        )
        assert response.modalities == []
        assert response.count == 0


class TestValidationResponse:
    """Tests for ValidationResponse model."""

    def test_valid_state(self):
        """Test response for valid environment state."""
        now = datetime.now(timezone.utc)
        response = ValidationResponse(
            valid=True,
            errors=[],
            checked_at=now,
        )
        assert response.valid is True
        assert response.errors == []
        assert response.checked_at == now

    def test_invalid_state(self):
        """Test response for invalid environment state."""
        now = datetime.now(timezone.utc)
        response = ValidationResponse(
            valid=False,
            errors=[
                "Email state missing required field: inbox",
                "Calendar event has end before start",
            ],
            checked_at=now,
        )
        assert response.valid is False
        assert len(response.errors) == 2

    def test_default_errors_list(self):
        """Test that errors defaults to empty list."""
        now = datetime.now(timezone.utc)
        response = ValidationResponse(
            valid=True,
            checked_at=now,
        )
        assert response.errors == []


# =============================================================================
# Chat Response Models
# =============================================================================


class TestChatStateResponse:
    """Tests for ChatStateResponse model."""

    def test_valid_response(self):
        """Test creating a valid chat state response."""
        now = datetime.now(timezone.utc)
        response = ChatStateResponse(
            current_time=now,
            conversations={},
            messages=[],
            total_message_count=0,
            conversation_count=0,
            max_history_size=1000,
        )
        assert response.modality_type == "chat"
        assert response.current_time == now
        assert response.conversations == {}
        assert response.messages == []
        assert response.total_message_count == 0
        assert response.conversation_count == 0
        assert response.max_history_size == 1000

    def test_default_modality_type(self):
        """Test that modality_type defaults to 'chat'."""
        now = datetime.now(timezone.utc)
        response = ChatStateResponse(
            current_time=now,
            conversations={},
            messages=[],
            total_message_count=0,
            conversation_count=0,
            max_history_size=1000,
        )
        assert response.modality_type == "chat"


class TestChatQueryResponse:
    """Tests for ChatQueryResponse model."""

    def test_valid_response(self):
        """Test creating a valid chat query response."""
        response = ChatQueryResponse(
            messages=[],
            total_count=0,
            returned_count=0,
            query={"role": "user", "limit": 10},
        )
        assert response.modality_type == "chat"
        assert response.messages == []
        assert response.total_count == 0
        assert response.returned_count == 0
        assert response.query == {"role": "user", "limit": 10}


# =============================================================================
# Location Response Models
# =============================================================================


class TestLocationStateResponse:
    """Tests for LocationStateResponse model."""

    def test_valid_response(self):
        """Test creating a valid location state response."""
        response = LocationStateResponse(
            modality_type="location",
            last_updated="2024-06-15T10:00:00+00:00",
            update_count=5,
            current={"latitude": 37.7749, "longitude": -122.4194},
            history=[],
        )
        assert response.modality_type == "location"
        assert response.update_count == 5
        assert response.current["latitude"] == 37.7749
        assert response.history == []

    def test_with_history(self):
        """Test response with location history."""
        response = LocationStateResponse(
            modality_type="location",
            last_updated="2024-06-15T10:00:00+00:00",
            update_count=3,
            current={"latitude": 37.7749, "longitude": -122.4194},
            history=[
                {"latitude": 37.7850, "longitude": -122.4000, "timestamp": "2024-06-15T09:00:00+00:00"},
                {"latitude": 37.7800, "longitude": -122.4100, "timestamp": "2024-06-15T09:30:00+00:00"},
            ],
        )
        assert len(response.history) == 2


class TestLocationQueryResponse:
    """Tests for LocationQueryResponse model."""

    def test_valid_response(self):
        """Test creating a valid location query response."""
        response = LocationQueryResponse(
            locations=[{"latitude": 37.7749, "longitude": -122.4194}],
            count=1,
            total_count=10,
        )
        assert len(response.locations) == 1
        assert response.count == 1
        assert response.total_count == 10

    def test_empty_results(self):
        """Test response with no matching locations."""
        response = LocationQueryResponse(
            locations=[],
            count=0,
            total_count=0,
        )
        assert response.locations == []
        assert response.count == 0


# =============================================================================
# Weather Response Models
# =============================================================================


class TestWeatherStateResponse:
    """Tests for WeatherStateResponse model."""

    def test_valid_response(self):
        """Test creating a valid weather state response."""
        response = WeatherStateResponse(
            modality_type="weather",
            last_updated="2024-06-15T10:00:00+00:00",
            update_count=3,
            locations={"37.77,-122.42": {"temp": 68.5, "condition": "sunny"}},
            location_count=1,
        )
        assert response.modality_type == "weather"
        assert response.update_count == 3
        assert response.location_count == 1
        assert "37.77,-122.42" in response.locations

    def test_multiple_locations(self):
        """Test response with multiple tracked locations."""
        response = WeatherStateResponse(
            modality_type="weather",
            last_updated="2024-06-15T10:00:00+00:00",
            update_count=10,
            locations={
                "37.77,-122.42": {"temp": 68.5},
                "40.71,-74.01": {"temp": 75.2},
            },
            location_count=2,
        )
        assert response.location_count == 2


class TestWeatherQueryResponse:
    """Tests for WeatherQueryResponse model."""

    def test_valid_response(self):
        """Test creating a valid weather query response."""
        response = WeatherQueryResponse(
            reports=[],
            count=0,
            total_count=0,
        )
        assert response.reports == []
        assert response.count == 0
        assert response.total_count == 0
        assert response.error is None

    def test_with_error(self):
        """Test response with error message."""
        response = WeatherQueryResponse(
            reports=[],
            count=0,
            total_count=0,
            error="No weather data available for this location",
        )
        assert response.error == "No weather data available for this location"

    def test_default_total_count(self):
        """Test that total_count defaults to 0."""
        response = WeatherQueryResponse(
            reports=[],
            count=0,
        )
        assert response.total_count == 0


# =============================================================================
# Serialization Tests
# =============================================================================


class TestResponseSerialization:
    """Tests for proper serialization of response models."""

    def test_modality_state_response_to_json(self):
        """Test ModalityStateResponse serializes to JSON-compatible dict."""
        now = datetime.now(timezone.utc)
        response = ModalityStateResponse(
            modality_type="email",
            current_time=now,
            state={"key": "value"},
        )
        data = response.model_dump(mode="json")
        assert isinstance(data["current_time"], str)
        assert data["modality_type"] == "email"

    def test_event_response_datetime_serialization(self):
        """Test EventResponse serializes datetimes properly."""
        scheduled = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        created = datetime(2024, 6, 14, 9, 0, 0, tzinfo=timezone.utc)
        response = EventResponse(
            event_id="evt-123",
            scheduled_time=scheduled,
            modality="email",
            status="pending",
            priority=50,
            created_at=created,
        )
        data = response.model_dump(mode="json")
        assert isinstance(data["scheduled_time"], str)
        assert isinstance(data["created_at"], str)
        assert data["executed_at"] is None

    def test_error_response_serialization(self):
        """Test ErrorResponse serializes correctly."""
        response = ErrorResponse(
            error="TEST_ERROR",
            message="This is a test error",
            details={"code": 123, "nested": {"value": True}},
        )
        data = response.model_dump()
        assert data["error"] == "TEST_ERROR"
        assert data["message"] == "This is a test error"
        assert data["details"]["code"] == 123
        assert data["details"]["nested"]["value"] is True
