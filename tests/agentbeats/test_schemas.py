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
    EarlyCompletionMessage,
    InitialStateSummary,
    ModalityCounts,
    ScenarioDescription,
    TurnCompleteMessage,
    TurnStartMessage,
)


# =============================================================================
# ScenarioDescription Tests
# =============================================================================


class TestScenarioDescription:
    """Tests for ScenarioDescription model."""

    def test_minimal_valid(self):
        """Create with required fields only."""
        scenario = ScenarioDescription(
            description="Test scenario",
            goals=["Goal 1", "Goal 2"],
        )
        assert scenario.description == "Test scenario"
        assert scenario.goals == ["Goal 1", "Goal 2"]
        assert scenario.constraints is None

    def test_with_constraints(self):
        """Create with optional constraints."""
        scenario = ScenarioDescription(
            description="Test scenario",
            goals=["Goal 1"],
            constraints=["No deleting", "No external emails"],
        )
        assert scenario.constraints == ["No deleting", "No external emails"]

    def test_empty_goals_allowed(self):
        """Empty goals list is valid (though unusual)."""
        scenario = ScenarioDescription(
            description="Test",
            goals=[],
        )
        assert scenario.goals == []

    def test_missing_description_fails(self):
        """Description is required."""
        with pytest.raises(ValidationError):
            ScenarioDescription(goals=["Goal"])

    def test_missing_goals_fails(self):
        """Goals is required."""
        with pytest.raises(ValidationError):
            ScenarioDescription(description="Test")

    def test_serialization_roundtrip(self):
        """Model survives JSON serialization."""
        scenario = ScenarioDescription(
            description="You are managing an inbox",
            goals=["Reply to urgent", "Archive spam"],
            constraints=["No deletions"],
        )
        json_str = scenario.model_dump_json()
        restored = ScenarioDescription.model_validate_json(json_str)
        assert restored == scenario


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
            scenario=ScenarioDescription(
                description="Test scenario",
                goals=["Complete task"],
            ),
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
        assert msg.scenario.goals == ["Complete task"]

    def test_serialization_roundtrip(self, valid_start_message: AssessmentStartMessage):
        """Model survives JSON serialization."""
        json_str = valid_start_message.model_dump_json()
        restored = AssessmentStartMessage.model_validate_json(json_str)
        assert restored.ues_url == valid_start_message.ues_url
        assert restored.scenario.description == valid_start_message.scenario.description

    def test_missing_ues_url_fails(self):
        """UES URL is required."""
        with pytest.raises(ValidationError):
            AssessmentStartMessage(
                api_key="key",
                scenario=ScenarioDescription(description="x", goals=[]),
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
