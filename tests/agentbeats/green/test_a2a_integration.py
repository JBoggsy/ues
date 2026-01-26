"""Tests for the A2A integration module.

This module tests:
- Message serialization
- Response parsing (TurnCompleteMessage, EarlyCompletionMessage)
- Time step parsing (ISO 8601 durations)
- TurnResult extraction
- Result artifact production
- AssessmentUpdateEmitter
"""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from agentbeats.green.a2a_integration import (
    AssessmentUpdateEmitter,
    MessageParseError,
    TurnResult,
    parse_purple_response,
    parse_time_step,
    produce_result_artifact,
    reason_to_status,
    serialize_message,
)
from agentbeats.green.schemas import (
    AssessmentCompleteReason,
    AssessmentResult,
    AssessmentStartMessage,
    AssessmentStatus,
    CriterionResult,
    EarlyCompletionMessage,
    EvaluationDimension,
    InitialStateSummary,
    ModalityCounts,
    TurnCompleteMessage,
    TurnStartMessage,
)
from agentbeats.green.session import ActionLogEntry, AssessmentSession
from agentbeats.green.updates import TaskUpdateEmitter


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_session() -> AssessmentSession:
    """Create a sample assessment session for testing."""
    session = AssessmentSession(
        assessment_id="test-assessment-001",
        scenario_id="test-scenario",
        participant_url="http://localhost:9000",
        proctor_key="proctor-key-123",
        user_key="user-key-456",
        purple_agent_id="purple-agent-001",
        current_turn=3,
    )
    
    # Add some actions to the log
    session.action_log = [
        ActionLogEntry(
            turn=1,
            event_id="evt-001",
            modality="email",
            action_type="send",
            timestamp=datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc),
            summary="Sent email to bob@example.com",
            details={"to": "bob@example.com", "subject": "Hello"},
        ),
        ActionLogEntry(
            turn=2,
            event_id="evt-002",
            modality="calendar",
            action_type="create",
            timestamp=datetime(2024, 6, 15, 11, 0, 0, tzinfo=timezone.utc),
            summary="Created calendar event",
            details={"title": "Meeting"},
        ),
    ]
    
    return session


@pytest.fixture
def sample_criteria_results() -> list[CriterionResult]:
    """Create sample criterion results for testing."""
    return [
        CriterionResult(
            id="email_sent",
            name="Email Sent",
            dimension=EvaluationDimension.ACCURACY,
            score=10,
            max_score=10,
            explanation="Email sent successfully",
        ),
        CriterionResult(
            id="calendar_created",
            name="Calendar Event Created",
            dimension=EvaluationDimension.ACCURACY,
            score=8,
            max_score=10,
            explanation="Event created but wrong time",
        ),
        CriterionResult(
            id="efficiency",
            name="Action Efficiency",
            dimension=EvaluationDimension.EFFICIENCY,
            score=5,
            max_score=10,
            explanation="Too many actions",
        ),
    ]


# =============================================================================
# Message Serialization Tests
# =============================================================================


class TestSerializeMessage:
    """Tests for message serialization."""

    def test_serialize_assessment_start_message(self):
        """Test serializing AssessmentStartMessage."""
        message = AssessmentStartMessage(
            ues_url="http://localhost:8000",
            api_key="user-key-123",
            current_time=datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc),
            initial_state_summary=InitialStateSummary(),
        )
        
        json_str = serialize_message(message)
        data = json.loads(json_str)
        
        assert data["ues_url"] == "http://localhost:8000"
        assert data["api_key"] == "user-key-123"
        assert "current_time" in data

    def test_serialize_turn_start_message(self):
        """Test serializing TurnStartMessage."""
        message = TurnStartMessage(
            current_time=datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc),
            events_processed=5,
        )
        
        json_str = serialize_message(message)
        data = json.loads(json_str)
        
        assert data["events_processed"] == 5
        assert "current_time" in data

    def test_serialize_roundtrip(self):
        """Test that serialized messages can be parsed back."""
        original = TurnCompleteMessage(
            actions_taken=3,
            notes="Replied to emails",
            time_step=timedelta(hours=1),
        )
        
        json_str = serialize_message(original)
        data = json.loads(json_str)
        restored = TurnCompleteMessage.model_validate(data)
        
        assert restored.actions_taken == original.actions_taken
        assert restored.notes == original.notes


# =============================================================================
# Response Parsing Tests
# =============================================================================


class TestParsePurpleResponse:
    """Tests for parsing Purple agent responses."""

    def test_parse_turn_complete_minimal(self):
        """Test parsing a minimal TurnCompleteMessage."""
        response = '{"actions_taken": 3}'
        message = parse_purple_response(response)
        
        assert isinstance(message, TurnCompleteMessage)
        assert message.actions_taken == 3
        assert message.notes is None
        assert message.time_step is None

    def test_parse_turn_complete_full(self):
        """Test parsing a full TurnCompleteMessage."""
        response = json.dumps({
            "actions_taken": 5,
            "notes": "Completed all urgent tasks",
            "time_step": "PT2H",
        })
        message = parse_purple_response(response)
        
        assert isinstance(message, TurnCompleteMessage)
        assert message.actions_taken == 5
        assert message.notes == "Completed all urgent tasks"

    def test_parse_early_completion_with_reason(self):
        """Test parsing EarlyCompletionMessage with reason."""
        response = '{"reason": "All goals achieved"}'
        message = parse_purple_response(response)
        
        assert isinstance(message, EarlyCompletionMessage)
        assert message.reason == "All goals achieved"

    def test_parse_early_completion_empty(self):
        """Test parsing empty EarlyCompletionMessage."""
        response = '{}'
        message = parse_purple_response(response)
        
        assert isinstance(message, EarlyCompletionMessage)
        assert message.reason is None

    def test_parse_invalid_json_raises(self):
        """Test that invalid JSON raises MessageParseError."""
        with pytest.raises(MessageParseError) as exc_info:
            parse_purple_response("not valid json")
        
        assert "Invalid JSON" in str(exc_info.value)
        assert exc_info.value.raw_response == "not valid json"

    def test_parse_non_object_raises(self):
        """Test that non-object JSON raises MessageParseError."""
        with pytest.raises(MessageParseError) as exc_info:
            parse_purple_response('"just a string"')
        
        assert "Expected object" in str(exc_info.value)

    def test_parse_ambiguous_message_raises(self):
        """Test that ambiguous messages raise MessageParseError."""
        # Has neither actions_taken nor reason
        response = '{"unknown_field": "value"}'
        with pytest.raises(MessageParseError) as exc_info:
            parse_purple_response(response)
        
        assert "Cannot determine message type" in str(exc_info.value)

    def test_parse_invalid_turn_complete_raises(self):
        """Test that invalid TurnCompleteMessage raises MessageParseError."""
        # actions_taken must be >= 0
        response = '{"actions_taken": -1}'
        with pytest.raises(MessageParseError) as exc_info:
            parse_purple_response(response)
        
        assert "Invalid TurnCompleteMessage" in str(exc_info.value)


# =============================================================================
# Time Step Parsing Tests
# =============================================================================


class TestParseTimeStep:
    """Tests for ISO 8601 duration parsing."""

    def test_parse_timedelta_passthrough(self):
        """Test that timedelta objects pass through unchanged."""
        td = timedelta(hours=2, minutes=30)
        result = parse_time_step(td)
        
        assert result == td

    def test_parse_none(self):
        """Test that None returns None."""
        assert parse_time_step(None) is None

    def test_parse_hours_only(self):
        """Test parsing hours-only duration."""
        result = parse_time_step("PT2H")
        
        assert result == timedelta(hours=2)

    def test_parse_minutes_only(self):
        """Test parsing minutes-only duration."""
        result = parse_time_step("PT30M")
        
        assert result == timedelta(minutes=30)

    def test_parse_seconds_only(self):
        """Test parsing seconds-only duration."""
        result = parse_time_step("PT45S")
        
        assert result == timedelta(seconds=45)

    def test_parse_combined_hms(self):
        """Test parsing combined hours, minutes, seconds."""
        result = parse_time_step("PT1H30M45S")
        
        assert result == timedelta(hours=1, minutes=30, seconds=45)

    def test_parse_hours_minutes(self):
        """Test parsing hours and minutes."""
        result = parse_time_step("PT2H15M")
        
        assert result == timedelta(hours=2, minutes=15)

    def test_parse_invalid_format_returns_none(self):
        """Test that invalid format returns None."""
        assert parse_time_step("invalid") is None
        assert parse_time_step("2H") is None  # Missing PT prefix


# =============================================================================
# TurnResult Tests
# =============================================================================


class TestTurnResult:
    """Tests for TurnResult class."""

    def test_from_turn_complete_message(self):
        """Test creating TurnResult from TurnCompleteMessage."""
        message = TurnCompleteMessage(
            actions_taken=3,
            notes="Test notes",
            time_step=timedelta(hours=1),
        )
        
        result = TurnResult.from_message(message)
        
        assert result.is_early_completion is False
        assert result.actions_taken == 3
        assert result.notes == "Test notes"
        assert result.time_step == timedelta(hours=1)
        assert result.early_completion_reason is None

    def test_from_early_completion_message(self):
        """Test creating TurnResult from EarlyCompletionMessage."""
        message = EarlyCompletionMessage(reason="Goals achieved")
        
        result = TurnResult.from_message(message)
        
        assert result.is_early_completion is True
        assert result.actions_taken == 0
        assert result.notes is None
        assert result.time_step is None
        assert result.early_completion_reason == "Goals achieved"

    def test_from_response_turn_complete(self):
        """Test creating TurnResult from raw response string."""
        response = '{"actions_taken": 5, "notes": "Done"}'
        
        result = TurnResult.from_response(response)
        
        assert result.is_early_completion is False
        assert result.actions_taken == 5
        assert result.notes == "Done"

    def test_from_response_early_completion(self):
        """Test creating TurnResult from early completion response."""
        response = '{"reason": "Finished early"}'
        
        result = TurnResult.from_response(response)
        
        assert result.is_early_completion is True
        assert result.early_completion_reason == "Finished early"

    def test_to_dict(self):
        """Test converting TurnResult to dictionary."""
        result = TurnResult(
            is_early_completion=False,
            actions_taken=3,
            notes="Test",
            time_step=timedelta(hours=1),
        )
        
        d = result.to_dict()
        
        assert d["early_completion"] is False
        assert d["actions_taken"] == 3
        assert d["notes"] == "Test"
        assert d["time_step"] == timedelta(hours=1)


# =============================================================================
# Result Artifact Production Tests
# =============================================================================


class TestReasonToStatus:
    """Tests for reason_to_status conversion."""

    def test_scenario_complete_to_completed(self):
        """Test SCENARIO_COMPLETE maps to COMPLETED."""
        status = reason_to_status(AssessmentCompleteReason.SCENARIO_COMPLETE)
        assert status == AssessmentStatus.COMPLETED

    def test_early_completion_to_completed(self):
        """Test EARLY_COMPLETION maps to COMPLETED."""
        status = reason_to_status(AssessmentCompleteReason.EARLY_COMPLETION)
        assert status == AssessmentStatus.COMPLETED

    def test_timeout_to_timeout(self):
        """Test TIMEOUT maps to TIMEOUT."""
        status = reason_to_status(AssessmentCompleteReason.TIMEOUT)
        assert status == AssessmentStatus.TIMEOUT

    def test_error_to_error(self):
        """Test ERROR maps to ERROR."""
        status = reason_to_status(AssessmentCompleteReason.ERROR)
        assert status == AssessmentStatus.ERROR


class TestProduceResultArtifact:
    """Tests for result artifact production."""

    def test_produces_valid_result(
        self,
        sample_session: AssessmentSession,
        sample_criteria_results: list[CriterionResult],
    ):
        """Test producing a valid AssessmentResult."""
        result = produce_result_artifact(
            session=sample_session,
            reason=AssessmentCompleteReason.SCENARIO_COMPLETE,
            criteria_results=sample_criteria_results,
        )
        
        assert isinstance(result, AssessmentResult)
        assert result.assessment_id == "test-assessment-001"
        assert result.scenario_id == "test-scenario"
        assert result.participant == "http://localhost:9000"
        assert result.status == AssessmentStatus.COMPLETED
        assert result.turns_taken == 3

    def test_computes_scores_correctly(
        self,
        sample_session: AssessmentSession,
        sample_criteria_results: list[CriterionResult],
    ):
        """Test that scores are computed correctly from criteria."""
        result = produce_result_artifact(
            session=sample_session,
            reason=AssessmentCompleteReason.SCENARIO_COMPLETE,
            criteria_results=sample_criteria_results,
        )
        
        # Total: 10 + 8 + 5 = 23 out of 30
        assert result.scores.overall.score == 23
        assert result.scores.overall.max_score == 30
        
        # Accuracy: 10 + 8 = 18 out of 20
        assert result.scores.dimensions[EvaluationDimension.ACCURACY].score == 18
        assert result.scores.dimensions[EvaluationDimension.ACCURACY].max_score == 20
        
        # Efficiency: 5 out of 10
        assert result.scores.dimensions[EvaluationDimension.EFFICIENCY].score == 5

    def test_includes_criteria_results(
        self,
        sample_session: AssessmentSession,
        sample_criteria_results: list[CriterionResult],
    ):
        """Test that criteria results are included."""
        result = produce_result_artifact(
            session=sample_session,
            reason=AssessmentCompleteReason.SCENARIO_COMPLETE,
            criteria_results=sample_criteria_results,
        )
        
        assert len(result.criteria_results) == 3
        assert result.criteria_results[0].id == "email_sent"

    def test_includes_action_log(
        self,
        sample_session: AssessmentSession,
        sample_criteria_results: list[CriterionResult],
    ):
        """Test that action log is included."""
        result = produce_result_artifact(
            session=sample_session,
            reason=AssessmentCompleteReason.SCENARIO_COMPLETE,
            criteria_results=sample_criteria_results,
        )
        
        assert len(result.action_log) == 2
        assert result.action_log[0].action == "email.send"
        assert result.action_log[1].action == "calendar.create"

    def test_timeout_status(
        self,
        sample_session: AssessmentSession,
        sample_criteria_results: list[CriterionResult],
    ):
        """Test that TIMEOUT reason produces TIMEOUT status."""
        result = produce_result_artifact(
            session=sample_session,
            reason=AssessmentCompleteReason.TIMEOUT,
            criteria_results=sample_criteria_results,
        )
        
        assert result.status == AssessmentStatus.TIMEOUT

    def test_calculates_duration(
        self,
        sample_session: AssessmentSession,
        sample_criteria_results: list[CriterionResult],
    ):
        """Test that duration is calculated."""
        result = produce_result_artifact(
            session=sample_session,
            reason=AssessmentCompleteReason.SCENARIO_COMPLETE,
            criteria_results=sample_criteria_results,
        )
        
        # Duration should be positive (time since session start)
        assert result.duration_seconds >= 0


# =============================================================================
# AssessmentUpdateEmitter Tests
# =============================================================================


class TestAssessmentUpdateEmitter:
    """Tests for AssessmentUpdateEmitter."""

    @pytest.fixture
    def mock_task_emitter(self) -> TaskUpdateEmitter:
        """Create a mock TaskUpdateEmitter."""
        emitter = MagicMock(spec=TaskUpdateEmitter)
        emitter.emit = AsyncMock()
        return emitter

    @pytest.fixture
    def assessment_emitter(
        self,
        mock_task_emitter: TaskUpdateEmitter,
    ) -> AssessmentUpdateEmitter:
        """Create an AssessmentUpdateEmitter with mock dependencies."""
        return AssessmentUpdateEmitter(
            task_emitter=mock_task_emitter,
            assessment_id="test-assessment",
            context_id="test-context",
        )

    @pytest.mark.asyncio
    async def test_emit_assessment_started(
        self,
        assessment_emitter: AssessmentUpdateEmitter,
        mock_task_emitter: MagicMock,
        sample_session: AssessmentSession,
    ):
        """Test emitting assessment started update."""
        await assessment_emitter.emit_assessment_started(
            session=sample_session,
            user_prompt="Test the AI assistant",
        )
        
        mock_task_emitter.emit.assert_called_once()
        update = mock_task_emitter.emit.call_args[0][0]
        assert "assessment_id" in update.details
        assert update.details["user_prompt"] == "Test the AI assistant"

    @pytest.mark.asyncio
    async def test_emit_scenario_loaded(
        self,
        assessment_emitter: AssessmentUpdateEmitter,
        mock_task_emitter: MagicMock,
        sample_session: AssessmentSession,
    ):
        """Test emitting scenario loaded update."""
        initial_state = {"email": {"total": 5, "unread": 2}}
        
        await assessment_emitter.emit_scenario_loaded(
            session=sample_session,
            initial_state=initial_state,
        )
        
        mock_task_emitter.emit.assert_called_once()
        update = mock_task_emitter.emit.call_args[0][0]
        assert update.details["initial_state"] == initial_state

    @pytest.mark.asyncio
    async def test_emit_turn_started(
        self,
        assessment_emitter: AssessmentUpdateEmitter,
        mock_task_emitter: MagicMock,
        sample_session: AssessmentSession,
    ):
        """Test emitting turn started update."""
        current_time = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        
        await assessment_emitter.emit_turn_started(
            session=sample_session,
            current_time=current_time,
        )
        
        mock_task_emitter.emit.assert_called_once()
        update = mock_task_emitter.emit.call_args[0][0]
        assert update.details["turn"] == 3  # sample_session.current_turn

    @pytest.mark.asyncio
    async def test_emit_turn_completed(
        self,
        assessment_emitter: AssessmentUpdateEmitter,
        mock_task_emitter: MagicMock,
        sample_session: AssessmentSession,
    ):
        """Test emitting turn completed update."""
        turn_result = TurnResult(
            is_early_completion=False,
            actions_taken=5,
            notes="Test notes",
        )
        
        await assessment_emitter.emit_turn_completed(
            session=sample_session,
            turn_result=turn_result,
        )
        
        mock_task_emitter.emit.assert_called_once()
        update = mock_task_emitter.emit.call_args[0][0]
        assert update.details["actions_taken"] == 5
        assert update.details["purple_notes"] == "Test notes"

    @pytest.mark.asyncio
    async def test_emit_simulation_advanced(
        self,
        assessment_emitter: AssessmentUpdateEmitter,
        mock_task_emitter: MagicMock,
    ):
        """Test emitting simulation advanced update."""
        from_time = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        to_time = datetime(2024, 6, 15, 11, 0, 0, tzinfo=timezone.utc)
        
        await assessment_emitter.emit_simulation_advanced(
            from_time=from_time,
            to_time=to_time,
            events_processed=3,
        )
        
        mock_task_emitter.emit.assert_called_once()
        update = mock_task_emitter.emit.call_args[0][0]
        assert update.details["events_processed"] == 3

    @pytest.mark.asyncio
    async def test_emit_assessment_complete_without_result(
        self,
        assessment_emitter: AssessmentUpdateEmitter,
        mock_task_emitter: MagicMock,
        sample_session: AssessmentSession,
    ):
        """Test emitting assessment complete without result."""
        await assessment_emitter.emit_assessment_complete(
            session=sample_session,
            reason=AssessmentCompleteReason.SCENARIO_COMPLETE,
        )
        
        mock_task_emitter.emit.assert_called_once()
        update = mock_task_emitter.emit.call_args[0][0]
        assert update.details["reason"] == "scenario_complete"
        assert "score" not in update.details

    @pytest.mark.asyncio
    async def test_emit_assessment_complete_with_result(
        self,
        assessment_emitter: AssessmentUpdateEmitter,
        mock_task_emitter: MagicMock,
        sample_session: AssessmentSession,
        sample_criteria_results: list[CriterionResult],
    ):
        """Test emitting assessment complete with result including score."""
        result = produce_result_artifact(
            session=sample_session,
            reason=AssessmentCompleteReason.SCENARIO_COMPLETE,
            criteria_results=sample_criteria_results,
        )
        
        await assessment_emitter.emit_assessment_complete(
            session=sample_session,
            reason=AssessmentCompleteReason.SCENARIO_COMPLETE,
            result=result,
        )
        
        mock_task_emitter.emit.assert_called_once()
        update = mock_task_emitter.emit.call_args[0][0]
        assert "score" in update.details
        assert update.details["score"]["overall"]["score"] == 23

    def test_get_a2a_event(
        self,
        assessment_emitter: AssessmentUpdateEmitter,
    ):
        """Test converting task update to A2A event."""
        from agentbeats.green.schemas import TaskUpdate, TaskUpdateType
        
        update = TaskUpdate(
            type=TaskUpdateType.LOG_TURN_STARTED,
            timestamp=datetime.now(timezone.utc),
            message="Turn 1 started",
            details={"turn": 1},
        )
        
        event = assessment_emitter.get_a2a_event(update)
        
        assert event["task_id"] == "test-assessment"
        assert event["context_id"] == "test-context"
        assert event["state"] == "input_required"  # LOG_TURN_STARTED maps to input_required
        assert event["metadata"]["ues_update_type"] == "log_turn_started"


# =============================================================================
# Integration Tests
# =============================================================================


class TestA2AIntegration:
    """Integration tests for complete A2A workflows."""

    def test_full_message_flow(self):
        """Test a complete message serialization and parsing flow."""
        # Simulate Green sending AssessmentStartMessage
        start_msg = AssessmentStartMessage(
            ues_url="http://localhost:8000",
            api_key="user-key",
            current_time=datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc),
            initial_state_summary=InitialStateSummary(
                email=ModalityCounts(total=5, unread=2),
                calendar=ModalityCounts(total=3, events_today=1),
            ),
        )
        start_json = serialize_message(start_msg)
        
        # Purple would receive and process...
        # Then send TurnCompleteMessage
        turn_complete = TurnCompleteMessage(
            actions_taken=3,
            notes="Processed emails",
            time_step=timedelta(hours=1),
        )
        turn_json = serialize_message(turn_complete)
        
        # Green parses the response
        result = TurnResult.from_response(turn_json)
        
        assert result.is_early_completion is False
        assert result.actions_taken == 3
        assert result.notes == "Processed emails"

    def test_early_completion_flow(self):
        """Test early completion message flow."""
        # Purple decides to complete early
        early_msg = EarlyCompletionMessage(reason="All tasks completed")
        early_json = serialize_message(early_msg)
        
        # Green parses the response
        result = TurnResult.from_response(early_json)
        
        assert result.is_early_completion is True
        assert result.early_completion_reason == "All tasks completed"

    def test_full_assessment_result_flow(
        self,
        sample_session: AssessmentSession,
        sample_criteria_results: list[CriterionResult],
    ):
        """Test producing and serializing assessment result."""
        result = produce_result_artifact(
            session=sample_session,
            reason=AssessmentCompleteReason.SCENARIO_COMPLETE,
            criteria_results=sample_criteria_results,
        )
        
        # Serialize for transmission
        result_json = result.model_dump_json()
        
        # Verify it can be parsed back
        parsed = AssessmentResult.model_validate_json(result_json)
        
        assert parsed.assessment_id == result.assessment_id
        assert parsed.scores.overall.score == result.scores.overall.score
        assert len(parsed.criteria_results) == len(result.criteria_results)
