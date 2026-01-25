"""Tests for A2A message schemas.

Tests cover validation, serialization, and edge cases for all message types
used in Green-Purple agent communication.
"""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from agentbeats.green.schemas import (
    AssessmentCompleteMessage,
    AssessmentCompleteReason,
    AssessmentStartMessage,
    DEFAULT_ASSESSMENT_INSTRUCTIONS,
    EarlyCompletionMessage,
    InitialStateSummary,
    ModalityCounts,
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
