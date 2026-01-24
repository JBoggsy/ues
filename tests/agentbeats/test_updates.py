"""Tests for task update streaming infrastructure.

Tests cover TaskUpdateEmitter behavior and A2A conversion functions.
"""

import asyncio
from datetime import datetime, timezone

import pytest

from agentbeats.green.schemas import TaskUpdate, TaskUpdateType
from agentbeats.green.updates import (
    A2ATaskStatusUpdate,
    TaskUpdateEmitter,
    create_assessment_complete_update,
    create_assessment_started_update,
    create_scenario_loaded_update,
    create_simulation_advanced_update,
    create_turn_completed_update,
    create_turn_started_update,
    task_update_to_a2a_event,
)


# =============================================================================
# TaskUpdateEmitter Tests
# =============================================================================


class TestTaskUpdateEmitter:
    """Tests for TaskUpdateEmitter class."""

    @pytest.mark.asyncio
    async def test_emit_and_stream_single_update(self):
        """Single update can be emitted and consumed."""
        emitter = TaskUpdateEmitter()
        update = TaskUpdate(
            type=TaskUpdateType.LOG_TURN_STARTED,
            timestamp=datetime.now(timezone.utc),
            message="Turn 1 started",
        )

        # Emit in background
        async def emit_and_close():
            await emitter.emit(update)
            await emitter.close()

        asyncio.create_task(emit_and_close())

        # Consume
        received = []
        async for u in emitter.stream():
            received.append(u)

        assert len(received) == 1
        assert received[0] == update

    @pytest.mark.asyncio
    async def test_emit_multiple_updates(self):
        """Multiple updates are received in order."""
        emitter = TaskUpdateEmitter()
        updates = [
            TaskUpdate(
                type=TaskUpdateType.LOG_ASSESSMENT_STARTED,
                timestamp=datetime.now(timezone.utc),
                message="Assessment started",
            ),
            TaskUpdate(
                type=TaskUpdateType.LOG_TURN_STARTED,
                timestamp=datetime.now(timezone.utc),
                message="Turn 1",
            ),
            TaskUpdate(
                type=TaskUpdateType.LOG_TURN_COMPLETED,
                timestamp=datetime.now(timezone.utc),
                message="Turn 1 done",
            ),
        ]

        async def emit_all():
            for u in updates:
                await emitter.emit(u)
            await emitter.close()

        asyncio.create_task(emit_all())

        received = []
        async for u in emitter.stream():
            received.append(u)

        assert len(received) == 3
        assert received[0].type == TaskUpdateType.LOG_ASSESSMENT_STARTED
        assert received[1].type == TaskUpdateType.LOG_TURN_STARTED
        assert received[2].type == TaskUpdateType.LOG_TURN_COMPLETED

    @pytest.mark.asyncio
    async def test_verbose_mode_emits_all(self):
        """Verbose mode (default) emits all update types."""
        emitter = TaskUpdateEmitter(verbose=True)

        async def emit_various():
            await emitter.emit(
                TaskUpdate(
                    type=TaskUpdateType.LOG_TURN_STARTED,
                    timestamp=datetime.now(timezone.utc),
                    message="Turn",
                )
            )
            await emitter.emit(
                TaskUpdate(
                    type=TaskUpdateType.LOG_SIMULATION_ADVANCED,
                    timestamp=datetime.now(timezone.utc),
                    message="Advanced",
                )
            )
            await emitter.close()

        asyncio.create_task(emit_various())

        received = []
        async for u in emitter.stream():
            received.append(u)

        assert len(received) == 2

    @pytest.mark.asyncio
    async def test_non_verbose_filters_updates(self):
        """Non-verbose mode only emits start and complete updates."""
        emitter = TaskUpdateEmitter(verbose=False)

        async def emit_various():
            # Should be emitted
            await emitter.emit(
                TaskUpdate(
                    type=TaskUpdateType.LOG_ASSESSMENT_STARTED,
                    timestamp=datetime.now(timezone.utc),
                    message="Started",
                )
            )
            # Should be filtered
            await emitter.emit(
                TaskUpdate(
                    type=TaskUpdateType.LOG_TURN_STARTED,
                    timestamp=datetime.now(timezone.utc),
                    message="Turn",
                )
            )
            # Should be filtered
            await emitter.emit(
                TaskUpdate(
                    type=TaskUpdateType.LOG_SIMULATION_ADVANCED,
                    timestamp=datetime.now(timezone.utc),
                    message="Advanced",
                )
            )
            # Should be emitted
            await emitter.emit(
                TaskUpdate(
                    type=TaskUpdateType.LOG_ASSESSMENT_COMPLETE,
                    timestamp=datetime.now(timezone.utc),
                    message="Complete",
                )
            )
            await emitter.close()

        asyncio.create_task(emit_various())

        received = []
        async for u in emitter.stream():
            received.append(u)

        assert len(received) == 2
        assert received[0].type == TaskUpdateType.LOG_ASSESSMENT_STARTED
        assert received[1].type == TaskUpdateType.LOG_ASSESSMENT_COMPLETE

    @pytest.mark.asyncio
    async def test_emit_after_close_raises(self):
        """Emitting after close raises RuntimeError."""
        emitter = TaskUpdateEmitter()
        await emitter.close()

        with pytest.raises(RuntimeError, match="closed"):
            await emitter.emit(
                TaskUpdate(
                    type=TaskUpdateType.LOG_TURN_STARTED,
                    timestamp=datetime.now(timezone.utc),
                    message="Should fail",
                )
            )

    @pytest.mark.asyncio
    async def test_is_closed_property(self):
        """is_closed returns correct state."""
        emitter = TaskUpdateEmitter()
        assert emitter.is_closed() is False
        await emitter.close()
        assert emitter.is_closed() is True

    @pytest.mark.asyncio
    async def test_verbose_property(self):
        """verbose property returns configured value."""
        verbose_emitter = TaskUpdateEmitter(verbose=True)
        assert verbose_emitter.verbose is True

        quiet_emitter = TaskUpdateEmitter(verbose=False)
        assert quiet_emitter.verbose is False


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestCreateUpdateHelpers:
    """Tests for task update creation helper functions."""

    def test_create_assessment_started_update(self):
        """create_assessment_started_update creates correct structure."""
        update = create_assessment_started_update(
            assessment_id="assess-123",
            scenario_id="email_triage_basic",
            participant="personal_assistant",
            verbose_updates=True,
        )
        assert update.type == TaskUpdateType.LOG_ASSESSMENT_STARTED
        assert "email_triage_basic" in update.message
        assert update.details["assessment_id"] == "assess-123"
        assert update.details["scenario_id"] == "email_triage_basic"
        assert update.details["participant"] == "personal_assistant"
        assert update.details["verbose_updates"] is True

    def test_create_scenario_loaded_update(self):
        """create_scenario_loaded_update creates correct structure."""
        initial_state = {"email": {"total": 12, "unread": 5}}
        update = create_scenario_loaded_update(
            scenario_id="email_triage_basic",
            initial_state=initial_state,
        )
        assert update.type == TaskUpdateType.LOG_SCENARIO_LOADED
        assert update.details["scenario_id"] == "email_triage_basic"
        assert update.details["initial_state"] == initial_state

    def test_create_turn_started_update(self):
        """create_turn_started_update creates correct structure."""
        sim_time = datetime(2026, 1, 22, 10, 0, 0, tzinfo=timezone.utc)
        update = create_turn_started_update(turn=3, current_time=sim_time)
        assert update.type == TaskUpdateType.LOG_TURN_STARTED
        assert "Turn 3" in update.message
        assert update.details["turn"] == 3
        assert update.details["current_time"] == sim_time.isoformat()

    def test_create_turn_completed_update_minimal(self):
        """create_turn_completed_update works without notes."""
        update = create_turn_completed_update(turn=3, actions_taken=5)
        assert update.type == TaskUpdateType.LOG_TURN_COMPLETED
        assert update.details["turn"] == 3
        assert update.details["actions_taken"] == 5
        assert "purple_notes" not in update.details

    def test_create_turn_completed_update_with_notes(self):
        """create_turn_completed_update includes notes when provided."""
        update = create_turn_completed_update(
            turn=3,
            actions_taken=2,
            purple_notes="Replied to urgent email",
        )
        assert update.details["purple_notes"] == "Replied to urgent email"

    def test_create_simulation_advanced_update(self):
        """create_simulation_advanced_update creates correct structure."""
        from_time = datetime(2026, 1, 22, 10, 0, 0, tzinfo=timezone.utc)
        to_time = datetime(2026, 1, 22, 11, 0, 0, tzinfo=timezone.utc)
        update = create_simulation_advanced_update(
            from_time=from_time,
            to_time=to_time,
            events_processed=3,
        )
        assert update.type == TaskUpdateType.LOG_SIMULATION_ADVANCED
        assert "11:00:00" in update.message
        assert update.details["events_processed"] == 3

    def test_create_assessment_complete_update_minimal(self):
        """create_assessment_complete_update works without score."""
        update = create_assessment_complete_update(
            reason="scenario_complete",
            turns_taken=8,
            actions_taken=15,
        )
        assert update.type == TaskUpdateType.LOG_ASSESSMENT_COMPLETE
        assert update.details["reason"] == "scenario_complete"
        assert update.details["turns_taken"] == 8
        assert update.details["actions_taken"] == 15
        assert "score" not in update.details

    def test_create_assessment_complete_update_with_score(self):
        """create_assessment_complete_update includes score when provided."""
        score = {"overall": 85.5, "dimensions": {"accuracy": 90}}
        update = create_assessment_complete_update(
            reason="early_completion",
            turns_taken=5,
            actions_taken=10,
            score=score,
        )
        assert update.details["score"] == score


# =============================================================================
# A2A Conversion Tests
# =============================================================================


class TestTaskUpdateToA2AEvent:
    """Tests for task_update_to_a2a_event conversion function."""

    def test_working_state_for_generic_update(self):
        """Generic updates map to 'working' state."""
        update = TaskUpdate(
            type=TaskUpdateType.LOG_SCENARIO_LOADED,
            timestamp=datetime(2026, 1, 22, 10, 0, 0, tzinfo=timezone.utc),
            message="Scenario loaded",
        )
        a2a = task_update_to_a2a_event(update, task_id="task-1", context_id="ctx-1")

        assert a2a.state == "working"
        assert a2a.final is False
        assert a2a.task_id == "task-1"
        assert a2a.context_id == "ctx-1"
        assert a2a.message == "Scenario loaded"

    def test_completed_state_for_assessment_complete(self):
        """LOG_ASSESSMENT_COMPLETE maps to 'completed' with final=True."""
        update = TaskUpdate(
            type=TaskUpdateType.LOG_ASSESSMENT_COMPLETE,
            timestamp=datetime(2026, 1, 22, 11, 0, 0, tzinfo=timezone.utc),
            message="Assessment complete",
            details={"reason": "scenario_complete"},
        )
        a2a = task_update_to_a2a_event(update, task_id="task-1", context_id="ctx-1")

        assert a2a.state == "completed"
        assert a2a.final is True

    def test_input_required_state_for_turn_started(self):
        """LOG_TURN_STARTED maps to 'input_required' (waiting for Purple)."""
        update = TaskUpdate(
            type=TaskUpdateType.LOG_TURN_STARTED,
            timestamp=datetime(2026, 1, 22, 10, 0, 0, tzinfo=timezone.utc),
            message="Turn 1 started",
        )
        a2a = task_update_to_a2a_event(update, task_id="task-1", context_id="ctx-1")

        assert a2a.state == "input_required"
        assert a2a.final is False

    def test_metadata_includes_update_type(self):
        """Metadata always includes ues_update_type."""
        update = TaskUpdate(
            type=TaskUpdateType.LOG_TURN_COMPLETED,
            timestamp=datetime(2026, 1, 22, 10, 0, 0, tzinfo=timezone.utc),
            message="Turn done",
        )
        a2a = task_update_to_a2a_event(update, task_id="task-1", context_id="ctx-1")

        assert a2a.metadata["ues_update_type"] == "log_turn_completed"

    def test_metadata_includes_details(self):
        """Details are merged into metadata."""
        update = TaskUpdate(
            type=TaskUpdateType.LOG_TURN_COMPLETED,
            timestamp=datetime(2026, 1, 22, 10, 0, 0, tzinfo=timezone.utc),
            message="Turn done",
            details={"turn": 3, "actions_taken": 2},
        )
        a2a = task_update_to_a2a_event(update, task_id="task-1", context_id="ctx-1")

        assert a2a.metadata["turn"] == 3
        assert a2a.metadata["actions_taken"] == 2

    def test_timestamp_preserved(self):
        """Timestamp is preserved in conversion."""
        ts = datetime(2026, 1, 22, 10, 30, 0, tzinfo=timezone.utc)
        update = TaskUpdate(
            type=TaskUpdateType.LOG_SIMULATION_ADVANCED,
            timestamp=ts,
            message="Time advanced",
        )
        a2a = task_update_to_a2a_event(update, task_id="task-1", context_id="ctx-1")

        assert a2a.timestamp == ts


class TestA2ATaskStatusUpdate:
    """Tests for A2ATaskStatusUpdate model."""

    def test_serialization_roundtrip(self):
        """Model survives JSON serialization."""
        a2a = A2ATaskStatusUpdate(
            task_id="task-123",
            context_id="ctx-abc",
            state="working",
            message="Processing turn 3",
            timestamp=datetime(2026, 1, 22, 10, 0, 0, tzinfo=timezone.utc),
            final=False,
            metadata={"ues_update_type": "log_turn_started", "turn": 3},
        )
        json_str = a2a.model_dump_json()
        restored = A2ATaskStatusUpdate.model_validate_json(json_str)
        assert restored == a2a

    def test_empty_metadata_default(self):
        """Metadata defaults to empty dict."""
        a2a = A2ATaskStatusUpdate(
            task_id="task-1",
            context_id="ctx-1",
            state="working",
            message="Test",
            timestamp=datetime.now(timezone.utc),
        )
        assert a2a.metadata == {}
