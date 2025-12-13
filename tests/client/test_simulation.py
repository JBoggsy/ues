"""Unit tests for the SimulationClient and AsyncSimulationClient.

This module tests the simulation control sub-client that provides methods for
managing the simulation lifecycle: starting, stopping, resetting, clearing,
and undo/redo operations.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from client._simulation import (
    AsyncSimulationClient,
    ClearSimulationResponse,
    RedoResponse,
    ResetSimulationResponse,
    SimulationClient,
    SimulationStatusResponse,
    StartSimulationResponse,
    StopSimulationResponse,
    UndoRedoEventDetail,
    UndoResponse,
)


# =============================================================================
# Response Model Tests
# =============================================================================


class TestUndoRedoEventDetail:
    """Tests for the UndoRedoEventDetail response model."""

    def test_instantiation_with_all_fields(self):
        """Test creating an UndoRedoEventDetail with all fields."""
        detail = UndoRedoEventDetail(
            event_id="evt-123",
            modality="email",
            action="receive",
        )
        assert detail.event_id == "evt-123"
        assert detail.modality == "email"
        assert detail.action == "receive"

    def test_instantiation_with_optional_action_none(self):
        """Test creating an UndoRedoEventDetail with action as None."""
        detail = UndoRedoEventDetail(
            event_id="evt-456",
            modality="sms",
            action=None,
        )
        assert detail.event_id == "evt-456"
        assert detail.modality == "sms"
        assert detail.action is None

    def test_instantiation_without_action(self):
        """Test that action defaults to None when not provided."""
        detail = UndoRedoEventDetail(
            event_id="evt-789",
            modality="calendar",
        )
        assert detail.action is None


class TestStartSimulationResponse:
    """Tests for the StartSimulationResponse model."""

    def test_instantiation_with_all_fields(self):
        """Test creating a StartSimulationResponse with all fields."""
        response = StartSimulationResponse(
            simulation_id="sim-abc-123",
            status="running",
            current_time="2025-01-15T10:00:00",
            auto_advance=True,
            time_scale=10.0,
        )
        assert response.simulation_id == "sim-abc-123"
        assert response.status == "running"
        assert response.current_time == "2025-01-15T10:00:00"
        assert response.auto_advance is True
        assert response.time_scale == 10.0

    def test_instantiation_with_time_scale_none(self):
        """Test that time_scale can be None."""
        response = StartSimulationResponse(
            simulation_id="sim-def-456",
            status="running",
            current_time="2025-01-15T10:00:00",
            auto_advance=False,
            time_scale=None,
        )
        assert response.time_scale is None

    def test_instantiation_without_time_scale(self):
        """Test that time_scale defaults to None."""
        response = StartSimulationResponse(
            simulation_id="sim-ghi-789",
            status="running",
            current_time="2025-01-15T10:00:00",
            auto_advance=False,
        )
        assert response.time_scale is None


class TestStopSimulationResponse:
    """Tests for the StopSimulationResponse model."""

    def test_instantiation_with_all_fields(self):
        """Test creating a StopSimulationResponse with all fields."""
        response = StopSimulationResponse(
            simulation_id="sim-stop-123",
            status="stopped",
            final_time="2025-01-15T12:00:00",
            total_events=100,
            events_executed=95,
            events_failed=5,
        )
        assert response.simulation_id == "sim-stop-123"
        assert response.status == "stopped"
        assert response.final_time == "2025-01-15T12:00:00"
        assert response.total_events == 100
        assert response.events_executed == 95
        assert response.events_failed == 5

    def test_instantiation_with_optional_fields_none(self):
        """Test that optional fields can be None (when wasn't running)."""
        response = StopSimulationResponse(
            simulation_id="sim-stop-456",
            status="not_running",
            final_time=None,
            total_events=None,
            events_executed=None,
            events_failed=None,
        )
        assert response.final_time is None
        assert response.total_events is None
        assert response.events_executed is None
        assert response.events_failed is None

    def test_instantiation_with_minimal_fields(self):
        """Test that optional fields default to None."""
        response = StopSimulationResponse(
            simulation_id="sim-stop-789",
            status="stopped",
        )
        assert response.final_time is None
        assert response.total_events is None


class TestSimulationStatusResponse:
    """Tests for the SimulationStatusResponse model."""

    def test_instantiation_with_all_fields(self):
        """Test creating a SimulationStatusResponse with all fields."""
        response = SimulationStatusResponse(
            is_running=True,
            current_time="2025-01-15T10:30:00",
            is_paused=False,
            auto_advance=True,
            time_scale=5.0,
            pending_events=50,
            executed_events=25,
            failed_events=2,
            next_event_time="2025-01-15T10:31:00",
        )
        assert response.is_running is True
        assert response.current_time == "2025-01-15T10:30:00"
        assert response.is_paused is False
        assert response.auto_advance is True
        assert response.time_scale == 5.0
        assert response.pending_events == 50
        assert response.executed_events == 25
        assert response.failed_events == 2
        assert response.next_event_time == "2025-01-15T10:31:00"

    def test_instantiation_with_next_event_time_none(self):
        """Test that next_event_time can be None (no pending events)."""
        response = SimulationStatusResponse(
            is_running=True,
            current_time="2025-01-15T10:30:00",
            is_paused=False,
            auto_advance=False,
            time_scale=1.0,
            pending_events=0,
            executed_events=100,
            failed_events=0,
            next_event_time=None,
        )
        assert response.next_event_time is None

    def test_instantiation_without_next_event_time(self):
        """Test that next_event_time defaults to None."""
        response = SimulationStatusResponse(
            is_running=False,
            current_time="2025-01-15T10:30:00",
            is_paused=True,
            auto_advance=False,
            time_scale=1.0,
            pending_events=10,
            executed_events=0,
            failed_events=0,
        )
        assert response.next_event_time is None


class TestResetSimulationResponse:
    """Tests for the ResetSimulationResponse model."""

    def test_instantiation_with_all_fields(self):
        """Test creating a ResetSimulationResponse with all fields."""
        response = ResetSimulationResponse(
            status="reset",
            message="Reset complete: reversed 5 state changes, reset 10 events.",
            cleared_events=10,
            events_undone=5,
            undo_errors=["Error 1", "Error 2"],
        )
        assert response.status == "reset"
        assert response.message == "Reset complete: reversed 5 state changes, reset 10 events."
        assert response.cleared_events == 10
        assert response.events_undone == 5
        assert response.undo_errors == ["Error 1", "Error 2"]

    def test_instantiation_with_defaults(self):
        """Test that events_undone and undo_errors have defaults."""
        response = ResetSimulationResponse(
            status="reset",
            message="Reset complete.",
            cleared_events=0,
        )
        assert response.events_undone == 0
        assert response.undo_errors == []

    def test_instantiation_with_empty_undo_errors(self):
        """Test with explicit empty undo_errors list."""
        response = ResetSimulationResponse(
            status="reset",
            message="Reset complete: reset 5 events.",
            cleared_events=5,
            events_undone=0,
            undo_errors=[],
        )
        assert response.undo_errors == []


class TestClearSimulationResponse:
    """Tests for the ClearSimulationResponse model."""

    def test_instantiation_with_all_fields(self):
        """Test creating a ClearSimulationResponse with all fields."""
        response = ClearSimulationResponse(
            status="cleared",
            events_removed=50,
            modalities_cleared=8,
            time_reset="2025-01-01T00:00:00",
            current_time="2025-01-01T00:00:00",
        )
        assert response.status == "cleared"
        assert response.events_removed == 50
        assert response.modalities_cleared == 8
        assert response.time_reset == "2025-01-01T00:00:00"
        assert response.current_time == "2025-01-01T00:00:00"

    def test_instantiation_with_time_reset_none(self):
        """Test that time_reset can be None."""
        response = ClearSimulationResponse(
            status="cleared",
            events_removed=25,
            modalities_cleared=6,
            time_reset=None,
            current_time="2025-01-15T10:00:00",
        )
        assert response.time_reset is None

    def test_instantiation_without_time_reset(self):
        """Test that time_reset defaults to None."""
        response = ClearSimulationResponse(
            status="cleared",
            events_removed=10,
            modalities_cleared=4,
            current_time="2025-01-15T10:00:00",
        )
        assert response.time_reset is None


class TestUndoResponse:
    """Tests for the UndoResponse model."""

    def test_instantiation_with_all_fields(self):
        """Test creating an UndoResponse with all fields."""
        events = [
            UndoRedoEventDetail(event_id="evt-1", modality="email", action="receive"),
            UndoRedoEventDetail(event_id="evt-2", modality="sms", action="send"),
        ]
        response = UndoResponse(
            undone_count=2,
            undone_events=events,
            can_undo=True,
            can_redo=True,
            message="Undone 2 events.",
        )
        assert response.undone_count == 2
        assert len(response.undone_events) == 2
        assert response.undone_events[0].event_id == "evt-1"
        assert response.can_undo is True
        assert response.can_redo is True
        assert response.message == "Undone 2 events."

    def test_instantiation_with_empty_events(self):
        """Test with empty undone_events list."""
        response = UndoResponse(
            undone_count=0,
            undone_events=[],
            can_undo=False,
            can_redo=False,
            message="Nothing to undo.",
        )
        assert response.undone_count == 0
        assert response.undone_events == []
        assert response.message == "Nothing to undo."

    def test_instantiation_without_message(self):
        """Test that message defaults to None."""
        response = UndoResponse(
            undone_count=1,
            undone_events=[
                UndoRedoEventDetail(event_id="evt-3", modality="calendar")
            ],
            can_undo=False,
            can_redo=True,
        )
        assert response.message is None


class TestRedoResponse:
    """Tests for the RedoResponse model."""

    def test_instantiation_with_all_fields(self):
        """Test creating a RedoResponse with all fields."""
        events = [
            UndoRedoEventDetail(event_id="evt-10", modality="chat", action="message"),
        ]
        response = RedoResponse(
            redone_count=1,
            redone_events=events,
            can_undo=True,
            can_redo=False,
            message="Redone 1 event.",
        )
        assert response.redone_count == 1
        assert len(response.redone_events) == 1
        assert response.redone_events[0].modality == "chat"
        assert response.can_undo is True
        assert response.can_redo is False
        assert response.message == "Redone 1 event."

    def test_instantiation_with_empty_events(self):
        """Test with empty redone_events list."""
        response = RedoResponse(
            redone_count=0,
            redone_events=[],
            can_undo=True,
            can_redo=False,
            message="Nothing to redo.",
        )
        assert response.redone_count == 0
        assert response.redone_events == []

    def test_instantiation_without_message(self):
        """Test that message defaults to None."""
        response = RedoResponse(
            redone_count=1,
            redone_events=[
                UndoRedoEventDetail(event_id="evt-20", modality="location")
            ],
            can_undo=True,
            can_redo=True,
        )
        assert response.message is None


# =============================================================================
# SimulationClient Tests
# =============================================================================


class TestSimulationClientStart:
    """Tests for SimulationClient.start() method."""

    def test_start_with_defaults(self):
        """Test starting simulation with default parameters."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "simulation_id": "sim-001",
            "status": "running",
            "current_time": "2025-01-15T10:00:00",
            "auto_advance": False,
            "time_scale": None,
        }

        client = SimulationClient(mock_http)
        result = client.start()

        mock_http.post.assert_called_once_with(
            "/simulation/start",
            json={"auto_advance": False, "time_scale": 1.0},
            params=None,
        )
        assert isinstance(result, StartSimulationResponse)
        assert result.simulation_id == "sim-001"
        assert result.status == "running"
        assert result.auto_advance is False

    def test_start_with_auto_advance_enabled(self):
        """Test starting simulation with auto-advance enabled."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "simulation_id": "sim-002",
            "status": "running",
            "current_time": "2025-01-15T10:00:00",
            "auto_advance": True,
            "time_scale": 10.0,
        }

        client = SimulationClient(mock_http)
        result = client.start(auto_advance=True, time_scale=10.0)

        mock_http.post.assert_called_once_with(
            "/simulation/start",
            json={"auto_advance": True, "time_scale": 10.0},
            params=None,
        )
        assert result.auto_advance is True
        assert result.time_scale == 10.0

    def test_start_with_custom_time_scale(self):
        """Test starting simulation with custom time scale."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "simulation_id": "sim-003",
            "status": "running",
            "current_time": "2025-01-15T10:00:00",
            "auto_advance": True,
            "time_scale": 0.5,
        }

        client = SimulationClient(mock_http)
        result = client.start(auto_advance=True, time_scale=0.5)

        mock_http.post.assert_called_once_with(
            "/simulation/start",
            json={"auto_advance": True, "time_scale": 0.5},
            params=None,
        )
        assert result.time_scale == 0.5


class TestSimulationClientStop:
    """Tests for SimulationClient.stop() method."""

    def test_stop_returns_execution_summary(self):
        """Test stopping simulation returns execution summary."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "simulation_id": "sim-004",
            "status": "stopped",
            "final_time": "2025-01-15T12:00:00",
            "total_events": 100,
            "events_executed": 95,
            "events_failed": 5,
        }

        client = SimulationClient(mock_http)
        result = client.stop()

        mock_http.post.assert_called_once_with("/simulation/stop", json=None, params=None)
        assert isinstance(result, StopSimulationResponse)
        assert result.simulation_id == "sim-004"
        assert result.status == "stopped"
        assert result.final_time == "2025-01-15T12:00:00"
        assert result.total_events == 100
        assert result.events_executed == 95
        assert result.events_failed == 5

    def test_stop_when_not_running(self):
        """Test stopping when simulation wasn't running."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "simulation_id": "sim-005",
            "status": "not_running",
            "final_time": None,
            "total_events": None,
            "events_executed": None,
            "events_failed": None,
        }

        client = SimulationClient(mock_http)
        result = client.stop()

        assert result.final_time is None
        assert result.total_events is None


class TestSimulationClientStatus:
    """Tests for SimulationClient.status() method."""

    def test_status_returns_current_state(self):
        """Test getting simulation status."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "is_running": True,
            "current_time": "2025-01-15T10:30:00",
            "is_paused": False,
            "auto_advance": True,
            "time_scale": 5.0,
            "pending_events": 50,
            "executed_events": 25,
            "failed_events": 2,
            "next_event_time": "2025-01-15T10:31:00",
        }

        client = SimulationClient(mock_http)
        result = client.status()

        mock_http.get.assert_called_once_with("/simulation/status", params=None)
        assert isinstance(result, SimulationStatusResponse)
        assert result.is_running is True
        assert result.current_time == "2025-01-15T10:30:00"
        assert result.is_paused is False
        assert result.auto_advance is True
        assert result.time_scale == 5.0
        assert result.pending_events == 50
        assert result.executed_events == 25
        assert result.failed_events == 2
        assert result.next_event_time == "2025-01-15T10:31:00"

    def test_status_when_not_running(self):
        """Test status when simulation is not running."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "is_running": False,
            "current_time": "2025-01-15T10:00:00",
            "is_paused": False,
            "auto_advance": False,
            "time_scale": 1.0,
            "pending_events": 100,
            "executed_events": 0,
            "failed_events": 0,
            "next_event_time": None,
        }

        client = SimulationClient(mock_http)
        result = client.status()

        assert result.is_running is False
        assert result.next_event_time is None

    def test_status_when_paused(self):
        """Test status when simulation is paused."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "is_running": True,
            "current_time": "2025-01-15T11:00:00",
            "is_paused": True,
            "auto_advance": True,
            "time_scale": 2.0,
            "pending_events": 30,
            "executed_events": 70,
            "failed_events": 0,
            "next_event_time": "2025-01-15T11:01:00",
        }

        client = SimulationClient(mock_http)
        result = client.status()

        assert result.is_paused is True


class TestSimulationClientReset:
    """Tests for SimulationClient.reset() method."""

    def test_reset_returns_summary(self):
        """Test resetting simulation returns summary."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "status": "reset",
            "message": "Reset complete: reversed 10 state changes, reset 15 events.",
            "cleared_events": 15,
            "events_undone": 10,
            "undo_errors": [],
        }

        client = SimulationClient(mock_http)
        result = client.reset()

        mock_http.post.assert_called_once_with("/simulation/reset", json=None, params=None)
        assert isinstance(result, ResetSimulationResponse)
        assert result.status == "reset"
        assert result.cleared_events == 15
        assert result.events_undone == 10
        assert result.undo_errors == []

    def test_reset_with_undo_errors(self):
        """Test reset when some undos fail."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "status": "reset",
            "message": "Reset complete with errors.",
            "cleared_events": 10,
            "events_undone": 8,
            "undo_errors": ["Failed to undo event evt-5", "Failed to undo event evt-7"],
        }

        client = SimulationClient(mock_http)
        result = client.reset()

        assert len(result.undo_errors) == 2
        assert "evt-5" in result.undo_errors[0]


class TestSimulationClientClear:
    """Tests for SimulationClient.clear() method."""

    def test_clear_without_time_reset(self):
        """Test clearing simulation without resetting time."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "status": "cleared",
            "events_removed": 50,
            "modalities_cleared": 8,
            "time_reset": None,
            "current_time": "2025-01-15T10:00:00",
        }

        client = SimulationClient(mock_http)
        result = client.clear()

        mock_http.post.assert_called_once_with("/simulation/clear", json=None, params=None)
        assert isinstance(result, ClearSimulationResponse)
        assert result.status == "cleared"
        assert result.events_removed == 50
        assert result.modalities_cleared == 8
        assert result.time_reset is None

    def test_clear_with_time_reset(self):
        """Test clearing simulation with time reset."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "status": "cleared",
            "events_removed": 25,
            "modalities_cleared": 6,
            "time_reset": "2025-01-01T00:00:00",
            "current_time": "2025-01-01T00:00:00",
        }

        reset_time = datetime(2025, 1, 1, 0, 0, 0)
        client = SimulationClient(mock_http)
        result = client.clear(reset_time_to=reset_time)

        mock_http.post.assert_called_once_with(
            "/simulation/clear",
            json={"reset_time_to": "2025-01-01T00:00:00"},
            params=None,
        )
        assert result.time_reset == "2025-01-01T00:00:00"
        assert result.current_time == "2025-01-01T00:00:00"


class TestSimulationClientUndo:
    """Tests for SimulationClient.undo() method."""

    def test_undo_single_event_default(self):
        """Test undoing single event (default count=1)."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "undone_count": 1,
            "undone_events": [
                {"event_id": "evt-100", "modality": "email", "action": "receive"}
            ],
            "can_undo": True,
            "can_redo": True,
            "message": None,
        }

        client = SimulationClient(mock_http)
        result = client.undo()

        # Default count=1 sends no body
        mock_http.post.assert_called_once_with("/simulation/undo", json=None, params=None)
        assert isinstance(result, UndoResponse)
        assert result.undone_count == 1
        assert len(result.undone_events) == 1
        assert result.undone_events[0].event_id == "evt-100"
        assert result.can_undo is True
        assert result.can_redo is True

    def test_undo_multiple_events(self):
        """Test undoing multiple events."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "undone_count": 3,
            "undone_events": [
                {"event_id": "evt-101", "modality": "email", "action": "receive"},
                {"event_id": "evt-102", "modality": "sms", "action": "send"},
                {"event_id": "evt-103", "modality": "calendar", "action": None},
            ],
            "can_undo": False,
            "can_redo": True,
            "message": None,
        }

        client = SimulationClient(mock_http)
        result = client.undo(count=3)

        mock_http.post.assert_called_once_with(
            "/simulation/undo",
            json={"count": 3},
            params=None,
        )
        assert result.undone_count == 3
        assert len(result.undone_events) == 3
        assert result.can_undo is False

    def test_undo_when_nothing_to_undo(self):
        """Test undo when there's nothing to undo."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "undone_count": 0,
            "undone_events": [],
            "can_undo": False,
            "can_redo": False,
            "message": "Nothing to undo.",
        }

        client = SimulationClient(mock_http)
        result = client.undo()

        assert result.undone_count == 0
        assert result.undone_events == []
        assert result.message == "Nothing to undo."


class TestSimulationClientRedo:
    """Tests for SimulationClient.redo() method."""

    def test_redo_single_event_default(self):
        """Test redoing single event (default count=1)."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "redone_count": 1,
            "redone_events": [
                {"event_id": "evt-200", "modality": "chat", "action": "message"}
            ],
            "can_undo": True,
            "can_redo": True,
            "message": None,
        }

        client = SimulationClient(mock_http)
        result = client.redo()

        # Default count=1 sends no body
        mock_http.post.assert_called_once_with("/simulation/redo", json=None, params=None)
        assert isinstance(result, RedoResponse)
        assert result.redone_count == 1
        assert len(result.redone_events) == 1
        assert result.redone_events[0].event_id == "evt-200"

    def test_redo_multiple_events(self):
        """Test redoing multiple events."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "redone_count": 2,
            "redone_events": [
                {"event_id": "evt-201", "modality": "location", "action": None},
                {"event_id": "evt-202", "modality": "weather", "action": None},
            ],
            "can_undo": True,
            "can_redo": False,
            "message": None,
        }

        client = SimulationClient(mock_http)
        result = client.redo(count=2)

        mock_http.post.assert_called_once_with(
            "/simulation/redo",
            json={"count": 2},
            params=None,
        )
        assert result.redone_count == 2
        assert result.can_redo is False

    def test_redo_when_nothing_to_redo(self):
        """Test redo when there's nothing to redo."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "redone_count": 0,
            "redone_events": [],
            "can_undo": True,
            "can_redo": False,
            "message": "Nothing to redo.",
        }

        client = SimulationClient(mock_http)
        result = client.redo()

        assert result.redone_count == 0
        assert result.redone_events == []
        assert result.message == "Nothing to redo."


# =============================================================================
# AsyncSimulationClient Tests
# =============================================================================


class TestAsyncSimulationClientStart:
    """Tests for AsyncSimulationClient.start() method."""

    async def test_start_with_defaults(self):
        """Test starting simulation with default parameters."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "simulation_id": "async-sim-001",
            "status": "running",
            "current_time": "2025-01-15T10:00:00",
            "auto_advance": False,
            "time_scale": None,
        }

        client = AsyncSimulationClient(mock_http)
        result = await client.start()

        mock_http.post.assert_called_once_with(
            "/simulation/start",
            json={"auto_advance": False, "time_scale": 1.0},
            params=None,
        )
        assert isinstance(result, StartSimulationResponse)
        assert result.simulation_id == "async-sim-001"

    async def test_start_with_auto_advance_enabled(self):
        """Test starting simulation with auto-advance enabled."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "simulation_id": "async-sim-002",
            "status": "running",
            "current_time": "2025-01-15T10:00:00",
            "auto_advance": True,
            "time_scale": 15.0,
        }

        client = AsyncSimulationClient(mock_http)
        result = await client.start(auto_advance=True, time_scale=15.0)

        mock_http.post.assert_called_once_with(
            "/simulation/start",
            json={"auto_advance": True, "time_scale": 15.0},
            params=None,
        )
        assert result.auto_advance is True
        assert result.time_scale == 15.0


class TestAsyncSimulationClientStop:
    """Tests for AsyncSimulationClient.stop() method."""

    async def test_stop_returns_execution_summary(self):
        """Test stopping simulation returns execution summary."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "simulation_id": "async-sim-003",
            "status": "stopped",
            "final_time": "2025-01-15T14:00:00",
            "total_events": 200,
            "events_executed": 190,
            "events_failed": 10,
        }

        client = AsyncSimulationClient(mock_http)
        result = await client.stop()

        mock_http.post.assert_called_once_with("/simulation/stop", json=None, params=None)
        assert isinstance(result, StopSimulationResponse)
        assert result.events_executed == 190


class TestAsyncSimulationClientStatus:
    """Tests for AsyncSimulationClient.status() method."""

    async def test_status_returns_current_state(self):
        """Test getting simulation status."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {
            "is_running": True,
            "current_time": "2025-01-15T11:30:00",
            "is_paused": False,
            "auto_advance": True,
            "time_scale": 3.0,
            "pending_events": 40,
            "executed_events": 60,
            "failed_events": 0,
            "next_event_time": "2025-01-15T11:32:00",
        }

        client = AsyncSimulationClient(mock_http)
        result = await client.status()

        mock_http.get.assert_called_once_with("/simulation/status", params=None)
        assert isinstance(result, SimulationStatusResponse)
        assert result.is_running is True
        assert result.pending_events == 40


class TestAsyncSimulationClientReset:
    """Tests for AsyncSimulationClient.reset() method."""

    async def test_reset_returns_summary(self):
        """Test resetting simulation returns summary."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "status": "reset",
            "message": "Reset complete: reset 20 events.",
            "cleared_events": 20,
            "events_undone": 15,
            "undo_errors": [],
        }

        client = AsyncSimulationClient(mock_http)
        result = await client.reset()

        mock_http.post.assert_called_once_with("/simulation/reset", json=None, params=None)
        assert isinstance(result, ResetSimulationResponse)
        assert result.cleared_events == 20


class TestAsyncSimulationClientClear:
    """Tests for AsyncSimulationClient.clear() method."""

    async def test_clear_without_time_reset(self):
        """Test clearing simulation without resetting time."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "status": "cleared",
            "events_removed": 75,
            "modalities_cleared": 10,
            "time_reset": None,
            "current_time": "2025-01-15T10:00:00",
        }

        client = AsyncSimulationClient(mock_http)
        result = await client.clear()

        mock_http.post.assert_called_once_with("/simulation/clear", json=None, params=None)
        assert isinstance(result, ClearSimulationResponse)
        assert result.events_removed == 75

    async def test_clear_with_time_reset(self):
        """Test clearing simulation with time reset."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "status": "cleared",
            "events_removed": 30,
            "modalities_cleared": 8,
            "time_reset": "2024-06-01T08:00:00",
            "current_time": "2024-06-01T08:00:00",
        }

        reset_time = datetime(2024, 6, 1, 8, 0, 0)
        client = AsyncSimulationClient(mock_http)
        result = await client.clear(reset_time_to=reset_time)

        mock_http.post.assert_called_once_with(
            "/simulation/clear",
            json={"reset_time_to": "2024-06-01T08:00:00"},
            params=None,
        )
        assert result.time_reset == "2024-06-01T08:00:00"


class TestAsyncSimulationClientUndo:
    """Tests for AsyncSimulationClient.undo() method."""

    async def test_undo_single_event_default(self):
        """Test undoing single event (default count=1)."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "undone_count": 1,
            "undone_events": [
                {"event_id": "async-evt-1", "modality": "email", "action": "receive"}
            ],
            "can_undo": True,
            "can_redo": True,
            "message": None,
        }

        client = AsyncSimulationClient(mock_http)
        result = await client.undo()

        mock_http.post.assert_called_once_with("/simulation/undo", json=None, params=None)
        assert isinstance(result, UndoResponse)
        assert result.undone_count == 1

    async def test_undo_multiple_events(self):
        """Test undoing multiple events."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "undone_count": 5,
            "undone_events": [
                {"event_id": f"async-evt-{i}", "modality": "email", "action": "receive"}
                for i in range(5)
            ],
            "can_undo": False,
            "can_redo": True,
            "message": None,
        }

        client = AsyncSimulationClient(mock_http)
        result = await client.undo(count=5)

        mock_http.post.assert_called_once_with(
            "/simulation/undo",
            json={"count": 5},
            params=None,
        )
        assert result.undone_count == 5
        assert len(result.undone_events) == 5


class TestAsyncSimulationClientRedo:
    """Tests for AsyncSimulationClient.redo() method."""

    async def test_redo_single_event_default(self):
        """Test redoing single event (default count=1)."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "redone_count": 1,
            "redone_events": [
                {"event_id": "async-evt-10", "modality": "sms", "action": "send"}
            ],
            "can_undo": True,
            "can_redo": True,
            "message": None,
        }

        client = AsyncSimulationClient(mock_http)
        result = await client.redo()

        mock_http.post.assert_called_once_with("/simulation/redo", json=None, params=None)
        assert isinstance(result, RedoResponse)
        assert result.redone_count == 1

    async def test_redo_multiple_events(self):
        """Test redoing multiple events."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "redone_count": 4,
            "redone_events": [
                {"event_id": f"async-evt-{i}", "modality": "chat", "action": None}
                for i in range(4)
            ],
            "can_undo": True,
            "can_redo": False,
            "message": None,
        }

        client = AsyncSimulationClient(mock_http)
        result = await client.redo(count=4)

        mock_http.post.assert_called_once_with(
            "/simulation/redo",
            json={"count": 4},
            params=None,
        )
        assert result.redone_count == 4
        assert result.can_redo is False
