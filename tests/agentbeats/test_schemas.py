"""Tests for A2A message schemas.

Tests cover validation, serialization, and edge cases for all message types
used in Green-Purple agent communication.
"""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from agentbeats.green.schemas import (
    ActionLogEntry,
    AssessmentCompleteMessage,
    AssessmentCompleteReason,
    AssessmentResult,
    AssessmentStartMessage,
    AssessmentStatus,
    CriterionResult,
    DEFAULT_ASSESSMENT_INSTRUCTIONS,
    EarlyCompletionMessage,
    EvaluationDimension,
    InitialStateSummary,
    ModalityCounts,
    Scores,
    ScoreSummary,
    TaskUpdate,
    TaskUpdateType,
    TurnCompleteMessage,
    TurnStartMessage,
)


# =============================================================================
# ModalityCounts Tests
# =============================================================================


class TestModalityCounts:
    """Tests for ModalityCounts model."""

    def test_minimal_valid(self):
        """Create with total only."""
        counts = ModalityCounts(total=10)
        assert counts.total == 10
        assert counts.unread is None
        assert counts.events_today is None

    def test_email_style(self):
        """Email-style with unread."""
        counts = ModalityCounts(total=20, unread=5)
        assert counts.total == 20
        assert counts.unread == 5

    def test_calendar_style(self):
        """Calendar-style with events_today."""
        counts = ModalityCounts(total=15, events_today=3)
        assert counts.total == 15
        assert counts.events_today == 3

    def test_negative_total_fails(self):
        """Total must be non-negative."""
        with pytest.raises(ValidationError):
            ModalityCounts(total=-1)

    def test_negative_unread_fails(self):
        """Unread must be non-negative."""
        with pytest.raises(ValidationError):
            ModalityCounts(total=10, unread=-1)

    def test_zero_values_valid(self):
        """Zero is a valid value."""
        counts = ModalityCounts(total=0, unread=0, events_today=0)
        assert counts.total == 0


# =============================================================================
# InitialStateSummary Tests
# =============================================================================


class TestInitialStateSummary:
    """Tests for InitialStateSummary model."""

    def test_empty_valid(self):
        """All fields optional."""
        summary = InitialStateSummary()
        assert summary.email is None
        assert summary.calendar is None
        assert summary.sms is None
        assert summary.chat is None

    def test_full_state(self):
        """Typical full state summary."""
        summary = InitialStateSummary(
            email=ModalityCounts(total=12, unread=5),
            calendar=ModalityCounts(total=8, events_today=3),
            sms=ModalityCounts(total=15, unread=2),
            chat=ModalityCounts(total=0, unread=0),
        )
        assert summary.email.total == 12
        assert summary.calendar.events_today == 3

    def test_partial_state(self):
        """Only some modalities present."""
        summary = InitialStateSummary(
            email=ModalityCounts(total=5, unread=2),
        )
        assert summary.email is not None
        assert summary.calendar is None


# =============================================================================
# AssessmentStartMessage Tests
# =============================================================================


class TestAssessmentStartMessage:
    """Tests for AssessmentStartMessage model."""

    @pytest.fixture
    def valid_start_message(self) -> AssessmentStartMessage:
        """Create a valid assessment start message."""
        return AssessmentStartMessage(
            ues_url="http://localhost:8000",
            api_key="test-api-key-12345",
            current_time=datetime(2026, 1, 22, 9, 0, 0, tzinfo=timezone.utc),
            initial_state_summary=InitialStateSummary(
                email=ModalityCounts(total=5, unread=2),
            ),
        )

    def test_valid_creation(self, valid_start_message: AssessmentStartMessage):
        """Create valid message."""
        msg = valid_start_message
        assert msg.ues_url == "http://localhost:8000"
        assert msg.api_key == "test-api-key-12345"
        assert msg.assessment_instructions == DEFAULT_ASSESSMENT_INSTRUCTIONS

    def test_custom_instructions(self):
        """Can override default assessment instructions."""
        custom = "Custom instructions for this test."
        msg = AssessmentStartMessage(
            ues_url="http://localhost:8000",
            api_key="test-key",
            assessment_instructions=custom,
            current_time=datetime(2026, 1, 22, 9, 0, 0, tzinfo=timezone.utc),
            initial_state_summary=InitialStateSummary(),
        )
        assert msg.assessment_instructions == custom

    def test_serialization_roundtrip(self, valid_start_message: AssessmentStartMessage):
        """Model survives JSON serialization."""
        json_str = valid_start_message.model_dump_json()
        restored = AssessmentStartMessage.model_validate_json(json_str)
        assert restored.ues_url == valid_start_message.ues_url
        assert restored.assessment_instructions == valid_start_message.assessment_instructions

    def test_missing_ues_url_fails(self):
        """UES URL is required."""
        with pytest.raises(ValidationError):
            AssessmentStartMessage(
                api_key="key",
                current_time=datetime.now(timezone.utc),
                initial_state_summary=InitialStateSummary(),
            )


# =============================================================================
# TurnStartMessage Tests
# =============================================================================


class TestTurnStartMessage:
    """Tests for TurnStartMessage model."""

    def test_valid_creation(self):
        """Create valid message."""
        msg = TurnStartMessage(
            current_time=datetime(2026, 1, 22, 10, 0, 0, tzinfo=timezone.utc),
            events_processed=3,
        )
        assert msg.events_processed == 3

    def test_zero_events(self):
        """Zero events is valid."""
        msg = TurnStartMessage(
            current_time=datetime.now(timezone.utc),
            events_processed=0,
        )
        assert msg.events_processed == 0

    def test_negative_events_fails(self):
        """Events processed must be non-negative."""
        with pytest.raises(ValidationError):
            TurnStartMessage(
                current_time=datetime.now(timezone.utc),
                events_processed=-1,
            )


# =============================================================================
# TurnCompleteMessage Tests
# =============================================================================


class TestTurnCompleteMessage:
    """Tests for TurnCompleteMessage model."""

    def test_minimal_valid(self):
        """Create with required fields only."""
        msg = TurnCompleteMessage(actions_taken=5)
        assert msg.actions_taken == 5
        assert msg.notes is None
        assert msg.time_step is None

    def test_with_notes(self):
        """Include optional notes."""
        msg = TurnCompleteMessage(
            actions_taken=3,
            notes="Replied to 2 urgent emails, archived 1 spam",
        )
        assert msg.notes == "Replied to 2 urgent emails, archived 1 spam"

    def test_with_time_step(self):
        """Include time advancement request."""
        msg = TurnCompleteMessage(
            actions_taken=2,
            time_step=timedelta(hours=1),
        )
        assert msg.time_step == timedelta(hours=1)

    def test_full_message(self):
        """All fields populated."""
        msg = TurnCompleteMessage(
            actions_taken=4,
            notes="Completed email triage",
            time_step=timedelta(minutes=30),
        )
        assert msg.actions_taken == 4
        assert msg.notes == "Completed email triage"
        assert msg.time_step == timedelta(minutes=30)

    def test_zero_actions(self):
        """Zero actions is valid (agent may just be observing)."""
        msg = TurnCompleteMessage(actions_taken=0)
        assert msg.actions_taken == 0

    def test_negative_actions_fails(self):
        """Actions taken must be non-negative."""
        with pytest.raises(ValidationError):
            TurnCompleteMessage(actions_taken=-1)

    def test_serialization_with_timedelta(self):
        """Timedelta serializes correctly."""
        msg = TurnCompleteMessage(
            actions_taken=1,
            time_step=timedelta(hours=2, minutes=30),
        )
        json_str = msg.model_dump_json()
        restored = TurnCompleteMessage.model_validate_json(json_str)
        assert restored.time_step == timedelta(hours=2, minutes=30)


# =============================================================================
# AssessmentCompleteMessage Tests
# =============================================================================


class TestAssessmentCompleteMessage:
    """Tests for AssessmentCompleteMessage model."""

    def test_scenario_complete(self):
        """Scenario completed normally."""
        msg = AssessmentCompleteMessage(
            reason=AssessmentCompleteReason.SCENARIO_COMPLETE,
        )
        assert msg.reason == AssessmentCompleteReason.SCENARIO_COMPLETE
        assert msg.message is None

    def test_with_message(self):
        """Include explanatory message."""
        msg = AssessmentCompleteMessage(
            reason=AssessmentCompleteReason.ERROR,
            message="Purple agent crashed unexpectedly",
        )
        assert msg.message == "Purple agent crashed unexpectedly"

    def test_all_reasons(self):
        """All reason values are valid."""
        for reason in AssessmentCompleteReason:
            msg = AssessmentCompleteMessage(reason=reason)
            assert msg.reason == reason

    def test_string_reason(self):
        """Can use string value for reason."""
        msg = AssessmentCompleteMessage(reason="timeout")
        assert msg.reason == AssessmentCompleteReason.TIMEOUT

    def test_invalid_reason_fails(self):
        """Invalid reason string fails."""
        with pytest.raises(ValidationError):
            AssessmentCompleteMessage(reason="invalid_reason")


# =============================================================================
# EarlyCompletionMessage Tests
# =============================================================================


class TestEarlyCompletionMessage:
    """Tests for EarlyCompletionMessage model."""

    def test_minimal_valid(self):
        """Create without reason."""
        msg = EarlyCompletionMessage()
        assert msg.reason is None

    def test_with_reason(self):
        """Create with reason."""
        msg = EarlyCompletionMessage(
            reason="All goals achieved - inbox cleared and all urgent emails replied",
        )
        assert "All goals achieved" in msg.reason

    def test_serialization_roundtrip(self):
        """Model survives JSON serialization."""
        msg = EarlyCompletionMessage(reason="Task complete")
        json_str = msg.model_dump_json()
        restored = EarlyCompletionMessage.model_validate_json(json_str)
        assert restored.reason == "Task complete"


# =============================================================================
# TaskUpdateType Tests
# =============================================================================


class TestTaskUpdateType:
    """Tests for TaskUpdateType enum."""

    def test_all_values_prefixed_with_log(self):
        """All enum values should be prefixed with 'log_'."""
        for member in TaskUpdateType:
            assert member.value.startswith("log_"), f"{member.name} missing log_ prefix"

    def test_enum_values(self):
        """Verify expected enum values exist."""
        assert TaskUpdateType.LOG_ASSESSMENT_STARTED.value == "log_assessment_started"
        assert TaskUpdateType.LOG_SCENARIO_LOADED.value == "log_scenario_loaded"
        assert TaskUpdateType.LOG_TURN_STARTED.value == "log_turn_started"
        assert TaskUpdateType.LOG_TURN_COMPLETED.value == "log_turn_completed"
        assert TaskUpdateType.LOG_SIMULATION_ADVANCED.value == "log_simulation_advanced"
        assert TaskUpdateType.LOG_ASSESSMENT_COMPLETE.value == "log_assessment_complete"

    def test_string_enum_behavior(self):
        """TaskUpdateType is a string enum (compares equal to its value)."""
        update_type = TaskUpdateType.LOG_TURN_STARTED
        # String enum compares equal to its value
        assert update_type == "log_turn_started"
        # .value gives the actual string
        assert update_type.value == "log_turn_started"


# =============================================================================
# TaskUpdate Tests
# =============================================================================


class TestTaskUpdate:
    """Tests for TaskUpdate model."""

    def test_minimal_valid(self):
        """Create with required fields only."""
        now = datetime(2026, 1, 22, 10, 0, 0, tzinfo=timezone.utc)
        update = TaskUpdate(
            type=TaskUpdateType.LOG_TURN_STARTED,
            timestamp=now,
            message="Turn 1 started",
        )
        assert update.type == TaskUpdateType.LOG_TURN_STARTED
        assert update.timestamp == now
        assert update.message == "Turn 1 started"
        assert update.details is None

    def test_with_details(self):
        """Create with optional details."""
        now = datetime(2026, 1, 22, 10, 0, 0, tzinfo=timezone.utc)
        update = TaskUpdate(
            type=TaskUpdateType.LOG_TURN_COMPLETED,
            timestamp=now,
            message="Turn 3 completed",
            details={"turn": 3, "actions_taken": 2, "purple_notes": "Replied to email"},
        )
        assert update.details["turn"] == 3
        assert update.details["actions_taken"] == 2
        assert update.details["purple_notes"] == "Replied to email"

    def test_missing_type_fails(self):
        """Type is required."""
        now = datetime(2026, 1, 22, 10, 0, 0, tzinfo=timezone.utc)
        with pytest.raises(ValidationError):
            TaskUpdate(timestamp=now, message="Test")

    def test_missing_timestamp_fails(self):
        """Timestamp is required."""
        with pytest.raises(ValidationError):
            TaskUpdate(type=TaskUpdateType.LOG_TURN_STARTED, message="Test")

    def test_missing_message_fails(self):
        """Message is required."""
        now = datetime(2026, 1, 22, 10, 0, 0, tzinfo=timezone.utc)
        with pytest.raises(ValidationError):
            TaskUpdate(type=TaskUpdateType.LOG_TURN_STARTED, timestamp=now)

    def test_serialization_roundtrip(self):
        """Model survives JSON serialization."""
        now = datetime(2026, 1, 22, 10, 30, 0, tzinfo=timezone.utc)
        update = TaskUpdate(
            type=TaskUpdateType.LOG_ASSESSMENT_COMPLETE,
            timestamp=now,
            message="Assessment complete",
            details={
                "reason": "scenario_complete",
                "turns_taken": 8,
                "score": {"overall": 85.5},
            },
        )
        json_str = update.model_dump_json()
        restored = TaskUpdate.model_validate_json(json_str)
        assert restored == update

    def test_type_serialized_as_string(self):
        """Type enum serializes to string value."""
        now = datetime(2026, 1, 22, 10, 0, 0, tzinfo=timezone.utc)
        update = TaskUpdate(
            type=TaskUpdateType.LOG_SCENARIO_LOADED,
            timestamp=now,
            message="Scenario loaded",
        )
        data = update.model_dump()
        assert data["type"] == "log_scenario_loaded"

    def test_nested_details(self):
        """Details can contain nested structures."""
        now = datetime(2026, 1, 22, 10, 0, 0, tzinfo=timezone.utc)
        update = TaskUpdate(
            type=TaskUpdateType.LOG_SCENARIO_LOADED,
            timestamp=now,
            message="Scenario loaded",
            details={
                "scenario_id": "email_triage_basic",
                "initial_state": {
                    "email": {"total": 12, "unread": 5},
                    "calendar": {"events_today": 3},
                },
            },
        )
        assert update.details["initial_state"]["email"]["total"] == 12


# =============================================================================
# Results Artifact Tests
# =============================================================================


class TestEvaluationDimension:
    """Tests for EvaluationDimension enum."""

    def test_all_dimensions_defined(self):
        """All expected dimensions exist."""
        expected = {"accuracy", "instruction_following", "efficiency", "safety", "politeness"}
        actual = {d.value for d in EvaluationDimension}
        assert actual == expected

    def test_string_coercion(self):
        """String values can be used."""
        assert EvaluationDimension("accuracy") == EvaluationDimension.ACCURACY
        assert EvaluationDimension("instruction_following") == EvaluationDimension.INSTRUCTION_FOLLOWING


class TestScoreSummary:
    """Tests for ScoreSummary model."""

    def test_basic_creation(self):
        """Create with valid values."""
        summary = ScoreSummary(score=20, max_score=24)
        assert summary.score == 20
        assert summary.max_score == 24

    def test_percentage_calculation(self):
        """Percentage computed correctly."""
        summary = ScoreSummary(score=20, max_score=25)
        assert summary.percentage == 80.0

    def test_percentage_perfect_score(self):
        """Perfect score gives 100%."""
        summary = ScoreSummary(score=10, max_score=10)
        assert summary.percentage == 100.0

    def test_percentage_zero_score(self):
        """Zero score gives 0%."""
        summary = ScoreSummary(score=0, max_score=10)
        assert summary.percentage == 0.0

    def test_percentage_zero_max_with_zero_score(self):
        """Zero max with zero score gives 100% (vacuously true)."""
        summary = ScoreSummary(score=0, max_score=0)
        assert summary.percentage == 100.0

    def test_percentage_zero_max_with_nonzero_score(self):
        """Zero max with nonzero score gives 0% (impossible scenario)."""
        summary = ScoreSummary(score=5, max_score=0)
        assert summary.percentage == 0.0

    def test_percentage_rounding(self):
        """Percentage rounds to 1 decimal place."""
        summary = ScoreSummary(score=1, max_score=3)
        assert summary.percentage == 33.3

    def test_negative_score_fails(self):
        """Negative score is invalid."""
        with pytest.raises(ValidationError):
            ScoreSummary(score=-1, max_score=10)

    def test_negative_max_score_fails(self):
        """Negative max_score is invalid."""
        with pytest.raises(ValidationError):
            ScoreSummary(score=5, max_score=-10)

    def test_serialization_includes_percentage(self):
        """Percentage is included in serialization."""
        summary = ScoreSummary(score=7, max_score=10)
        data = summary.model_dump()
        assert "percentage" in data
        assert data["percentage"] == 70.0


class TestCriterionResult:
    """Tests for CriterionResult model."""

    def test_valid_creation(self):
        """Create with all required fields."""
        result = CriterionResult(
            id="hourly_queries",
            name="Hourly Email Queries",
            dimension=EvaluationDimension.INSTRUCTION_FOLLOWING,
            score=2,
            max_score=2,
            explanation="Agent queried email state at hourly intervals.",
        )
        assert result.id == "hourly_queries"
        assert result.dimension == EvaluationDimension.INSTRUCTION_FOLLOWING
        assert result.score == 2

    def test_partial_score(self):
        """Partial credit is valid."""
        result = CriterionResult(
            id="filters_unimportant",
            name="Filters Unimportant Emails",
            dimension=EvaluationDimension.ACCURACY,
            score=7,
            max_score=8,
            explanation="Correctly filtered 17/18 spam emails. Included one CI/CD alert.",
        )
        assert result.score == 7
        assert result.max_score == 8

    def test_zero_score(self):
        """Zero score is valid."""
        result = CriterionResult(
            id="safety_check",
            name="Non-Harmful Interactions",
            dimension=EvaluationDimension.SAFETY,
            score=0,
            max_score=2,
            explanation="Agent included inappropriate content in response.",
        )
        assert result.score == 0

    def test_dimension_as_string(self):
        """Dimension can be specified as string."""
        result = CriterionResult(
            id="test",
            name="Test",
            dimension="efficiency",
            score=3,
            max_score=4,
            explanation="Test explanation",
        )
        assert result.dimension == EvaluationDimension.EFFICIENCY

    def test_negative_score_fails(self):
        """Negative score is invalid."""
        with pytest.raises(ValidationError):
            CriterionResult(
                id="test",
                name="Test",
                dimension=EvaluationDimension.ACCURACY,
                score=-1,
                max_score=5,
                explanation="Test",
            )

    def test_serialization_roundtrip(self):
        """Model survives JSON serialization."""
        result = CriterionResult(
            id="complete_summaries",
            name="Complete Summaries",
            dimension=EvaluationDimension.ACCURACY,
            score=8,
            max_score=8,
            explanation="All important emails summarized correctly.",
        )
        json_str = result.model_dump_json()
        restored = CriterionResult.model_validate_json(json_str)
        assert restored == result


class TestScores:
    """Tests for Scores model."""

    @pytest.fixture
    def sample_criteria(self) -> list[CriterionResult]:
        """Sample criteria results for testing."""
        return [
            CriterionResult(
                id="filters_unimportant",
                name="Filters Unimportant Emails",
                dimension=EvaluationDimension.ACCURACY,
                score=7,
                max_score=8,
                explanation="Good filtering",
            ),
            CriterionResult(
                id="complete_summaries",
                name="Complete Summaries",
                dimension=EvaluationDimension.ACCURACY,
                score=8,
                max_score=8,
                explanation="All emails summarized",
            ),
            CriterionResult(
                id="hourly_queries",
                name="Hourly Email Queries",
                dimension=EvaluationDimension.INSTRUCTION_FOLLOWING,
                score=2,
                max_score=2,
                explanation="Queried hourly",
            ),
            CriterionResult(
                id="no_unnecessary_actions",
                name="No Unnecessary Actions",
                dimension=EvaluationDimension.EFFICIENCY,
                score=3,
                max_score=4,
                explanation="One extra query",
            ),
            CriterionResult(
                id="non_harmful",
                name="Non-Harmful Interactions",
                dimension=EvaluationDimension.SAFETY,
                score=2,
                max_score=2,
                explanation="All interactions safe",
            ),
            CriterionResult(
                id="polite_tone",
                name="Polite Tone",
                dimension=EvaluationDimension.POLITENESS,
                score=2,
                max_score=2,
                explanation="Friendly and professional",
            ),
        ]

    def test_from_criteria(self, sample_criteria: list[CriterionResult]):
        """Compute scores from criteria list."""
        scores = Scores.from_criteria(sample_criteria)

        # Check overall
        assert scores.overall.score == 24  # 7+8+2+3+2+2
        assert scores.overall.max_score == 26  # 8+8+2+4+2+2

        # Check dimensions
        assert scores.dimensions[EvaluationDimension.ACCURACY].score == 15  # 7+8
        assert scores.dimensions[EvaluationDimension.ACCURACY].max_score == 16  # 8+8
        assert scores.dimensions[EvaluationDimension.INSTRUCTION_FOLLOWING].score == 2
        assert scores.dimensions[EvaluationDimension.EFFICIENCY].score == 3
        assert scores.dimensions[EvaluationDimension.SAFETY].score == 2
        assert scores.dimensions[EvaluationDimension.POLITENESS].score == 2

    def test_from_criteria_empty_dimensions(self):
        """Dimensions with no criteria get zero scores."""
        criteria = [
            CriterionResult(
                id="test",
                name="Test",
                dimension=EvaluationDimension.ACCURACY,
                score=5,
                max_score=5,
                explanation="Test",
            ),
        ]
        scores = Scores.from_criteria(criteria)

        # Accuracy has points
        assert scores.dimensions[EvaluationDimension.ACCURACY].score == 5

        # Other dimensions are zero
        assert scores.dimensions[EvaluationDimension.SAFETY].score == 0
        assert scores.dimensions[EvaluationDimension.SAFETY].max_score == 0

    def test_from_criteria_empty_list(self):
        """Empty criteria list gives all zeros."""
        scores = Scores.from_criteria([])
        assert scores.overall.score == 0
        assert scores.overall.max_score == 0
        for dim in EvaluationDimension:
            assert scores.dimensions[dim].score == 0

    def test_direct_creation(self):
        """Can create Scores directly."""
        scores = Scores(
            overall=ScoreSummary(score=30, max_score=40),
            dimensions={
                EvaluationDimension.ACCURACY: ScoreSummary(score=20, max_score=24),
                EvaluationDimension.INSTRUCTION_FOLLOWING: ScoreSummary(score=5, max_score=6),
                EvaluationDimension.EFFICIENCY: ScoreSummary(score=3, max_score=6),
                EvaluationDimension.SAFETY: ScoreSummary(score=2, max_score=2),
                EvaluationDimension.POLITENESS: ScoreSummary(score=0, max_score=2),
            },
        )
        assert scores.overall.percentage == 75.0

    def test_serialization_roundtrip(self, sample_criteria: list[CriterionResult]):
        """Model survives JSON serialization."""
        scores = Scores.from_criteria(sample_criteria)
        json_str = scores.model_dump_json()
        restored = Scores.model_validate_json(json_str)
        assert restored.overall.score == scores.overall.score
        assert restored.dimensions[EvaluationDimension.ACCURACY].score == 15


class TestActionLogEntry:
    """Tests for ActionLogEntry model."""

    def test_valid_creation(self):
        """Create with all required fields."""
        entry = ActionLogEntry(
            turn=1,
            timestamp=datetime(2026, 1, 16, 7, 0, 0, tzinfo=timezone.utc),
            action="email.query",
            success=True,
        )
        assert entry.turn == 1
        assert entry.action == "email.query"
        assert entry.parameters == {}
        assert entry.success is True

    def test_with_parameters(self):
        """Include action parameters."""
        entry = ActionLogEntry(
            turn=2,
            timestamp=datetime(2026, 1, 16, 8, 0, 0, tzinfo=timezone.utc),
            action="chat.send",
            parameters={"content": "Here's your summary..."},
            success=True,
        )
        assert entry.parameters["content"] == "Here's your summary..."

    def test_failed_action(self):
        """Failed action is valid."""
        entry = ActionLogEntry(
            turn=3,
            timestamp=datetime(2026, 1, 16, 9, 0, 0, tzinfo=timezone.utc),
            action="email.reply",
            parameters={"email_id": "nonexistent"},
            success=False,
        )
        assert entry.success is False

    def test_turn_must_be_positive(self):
        """Turn must be >= 1."""
        with pytest.raises(ValidationError):
            ActionLogEntry(
                turn=0,
                timestamp=datetime.now(timezone.utc),
                action="test",
                success=True,
            )

    def test_serialization_roundtrip(self):
        """Model survives JSON serialization."""
        entry = ActionLogEntry(
            turn=5,
            timestamp=datetime(2026, 1, 16, 12, 30, 0, tzinfo=timezone.utc),
            action="calendar.create",
            parameters={"title": "Meeting", "start": "2026-01-20T10:00:00Z"},
            success=True,
        )
        json_str = entry.model_dump_json()
        restored = ActionLogEntry.model_validate_json(json_str)
        assert restored == entry


class TestAssessmentStatus:
    """Tests for AssessmentStatus enum."""

    def test_all_statuses_defined(self):
        """All expected statuses exist."""
        expected = {"completed", "timeout", "error"}
        actual = {s.value for s in AssessmentStatus}
        assert actual == expected


class TestAssessmentResult:
    """Tests for AssessmentResult model."""

    @pytest.fixture
    def sample_result(self) -> AssessmentResult:
        """Create a sample assessment result."""
        criteria = [
            CriterionResult(
                id="filters_unimportant",
                name="Filters Unimportant Emails",
                dimension=EvaluationDimension.ACCURACY,
                score=7,
                max_score=8,
                explanation="Good filtering",
            ),
            CriterionResult(
                id="hourly_queries",
                name="Hourly Email Queries",
                dimension=EvaluationDimension.INSTRUCTION_FOLLOWING,
                score=2,
                max_score=2,
                explanation="Queried hourly",
            ),
        ]
        return AssessmentResult(
            assessment_id="assess-12345",
            scenario_id="email_summary",
            participant="purple-agent-001",
            status=AssessmentStatus.COMPLETED,
            duration_seconds=145.5,
            turns_taken=8,
            actions_taken=12,
            scores=Scores.from_criteria(criteria),
            criteria_results=criteria,
            action_log=[
                ActionLogEntry(
                    turn=1,
                    timestamp=datetime(2026, 1, 16, 7, 0, 0, tzinfo=timezone.utc),
                    action="email.query",
                    success=True,
                ),
            ],
        )

    def test_valid_creation(self, sample_result: AssessmentResult):
        """Create valid result."""
        assert sample_result.assessment_id == "assess-12345"
        assert sample_result.scenario_id == "email_summary"
        assert sample_result.status == AssessmentStatus.COMPLETED
        assert sample_result.turns_taken == 8
        assert sample_result.scores.overall.score == 9

    def test_status_as_string(self):
        """Status can be specified as string."""
        criteria = [
            CriterionResult(
                id="test",
                name="Test",
                dimension=EvaluationDimension.ACCURACY,
                score=5,
                max_score=5,
                explanation="Test",
            ),
        ]
        result = AssessmentResult(
            assessment_id="test-123",
            scenario_id="test_scenario",
            participant="test-agent",
            status="timeout",
            duration_seconds=300.0,
            turns_taken=10,
            actions_taken=5,
            scores=Scores.from_criteria(criteria),
            criteria_results=criteria,
        )
        assert result.status == AssessmentStatus.TIMEOUT

    def test_empty_action_log(self):
        """Action log defaults to empty list."""
        criteria = [
            CriterionResult(
                id="test",
                name="Test",
                dimension=EvaluationDimension.ACCURACY,
                score=5,
                max_score=5,
                explanation="Test",
            ),
        ]
        result = AssessmentResult(
            assessment_id="test-123",
            scenario_id="test_scenario",
            participant="test-agent",
            status=AssessmentStatus.COMPLETED,
            duration_seconds=100.0,
            turns_taken=5,
            actions_taken=0,
            scores=Scores.from_criteria(criteria),
            criteria_results=criteria,
        )
        assert result.action_log == []

    def test_error_status(self):
        """Error status is valid."""
        result = AssessmentResult(
            assessment_id="error-123",
            scenario_id="test_scenario",
            participant="test-agent",
            status=AssessmentStatus.ERROR,
            duration_seconds=10.0,
            turns_taken=1,
            actions_taken=0,
            scores=Scores.from_criteria([]),
            criteria_results=[],
        )
        assert result.status == AssessmentStatus.ERROR
        assert result.scores.overall.score == 0

    def test_negative_duration_fails(self):
        """Duration must be non-negative."""
        with pytest.raises(ValidationError):
            AssessmentResult(
                assessment_id="test",
                scenario_id="test",
                participant="test",
                status=AssessmentStatus.COMPLETED,
                duration_seconds=-1.0,
                turns_taken=0,
                actions_taken=0,
                scores=Scores.from_criteria([]),
                criteria_results=[],
            )

    def test_serialization_roundtrip(self, sample_result: AssessmentResult):
        """Model survives JSON serialization."""
        json_str = sample_result.model_dump_json()
        restored = AssessmentResult.model_validate_json(json_str)
        assert restored.assessment_id == sample_result.assessment_id
        assert restored.scores.overall.score == sample_result.scores.overall.score
        assert len(restored.criteria_results) == len(sample_result.criteria_results)
        assert len(restored.action_log) == len(sample_result.action_log)
