"""Tests for Purple Agent context module.

This module tests the AssessmentContext class and related utilities
for tracking state across the assessment lifecycle.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from agentbeats.purple.context import (
    AssessmentContext,
    create_context_from_assessment_start,
)
from agentbeats.purple.schemas import (
    InitialStateSummary,
    ModalityCounts,
    ParsedUserInstructions,
    ParsedGoal,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_time() -> datetime:
    """Sample datetime for tests."""
    return datetime(2026, 1, 22, 9, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def sample_initial_state() -> InitialStateSummary:
    """Sample initial state summary for tests."""
    return InitialStateSummary(
        email=ModalityCounts(total=12, unread=5),
        calendar=ModalityCounts(total=8, events_today=3),
        sms=ModalityCounts(total=15, unread=2),
        chat=ModalityCounts(total=1, unread=1),
    )


@pytest.fixture
def context(sample_time: datetime, sample_initial_state: InitialStateSummary) -> AssessmentContext:
    """Create a sample AssessmentContext for tests."""
    return AssessmentContext(
        assessment_id="test-assessment-001",
        ues_url="http://localhost:8000",
        api_key="ues_user_test_key_123",
        current_time=sample_time,
        initial_state=sample_initial_state,
    )


# =============================================================================
# AssessmentContext Creation Tests
# =============================================================================


class TestAssessmentContextCreation:
    """Tests for creating AssessmentContext instances."""

    def test_create_with_required_fields(self, sample_time: datetime):
        """Create context with only required fields."""
        ctx = AssessmentContext(
            assessment_id="test-001",
            ues_url="http://localhost:8000",
            api_key="test-key",
            current_time=sample_time,
        )
        assert ctx.assessment_id == "test-001"
        assert ctx.ues_url == "http://localhost:8000"
        assert ctx.api_key == "test-key"
        assert ctx.current_time == sample_time

    def test_default_values(self, sample_time: datetime):
        """Verify default values for optional fields."""
        ctx = AssessmentContext(
            assessment_id="test-001",
            ues_url="http://localhost:8000",
            api_key="test-key",
            current_time=sample_time,
        )
        assert ctx.turn_number == 0
        assert ctx.actions_this_turn == 0
        assert ctx.total_actions == 0
        assert ctx.user_instructions is None
        assert ctx.parsed_instructions is None
        assert ctx.initial_state is None
        assert ctx.events_processed_last_turn == 0
        assert ctx.custom_data == {}

    def test_create_with_all_fields(
        self, sample_time: datetime, sample_initial_state: InitialStateSummary
    ):
        """Create context with all fields specified."""
        parsed = ParsedUserInstructions(
            raw_content="Test",
            goals=[ParsedGoal(description="Goal 1")],
        )
        ctx = AssessmentContext(
            assessment_id="test-001",
            ues_url="http://localhost:8000",
            api_key="test-key",
            current_time=sample_time,
            turn_number=2,
            actions_this_turn=5,
            total_actions=15,
            user_instructions="Help me with email",
            parsed_instructions=parsed,
            initial_state=sample_initial_state,
            events_processed_last_turn=3,
            custom_data={"key": "value"},
        )
        assert ctx.turn_number == 2
        assert ctx.actions_this_turn == 5
        assert ctx.total_actions == 15
        assert ctx.user_instructions == "Help me with email"
        assert ctx.parsed_instructions is parsed
        assert ctx.initial_state is sample_initial_state
        assert ctx.events_processed_last_turn == 3
        assert ctx.custom_data == {"key": "value"}

    def test_started_at_is_set_automatically(self, sample_time: datetime):
        """started_at is set to current time when context is created."""
        before = datetime.now(timezone.utc)
        ctx = AssessmentContext(
            assessment_id="test-001",
            ues_url="http://localhost:8000",
            api_key="test-key",
            current_time=sample_time,
        )
        after = datetime.now(timezone.utc)

        assert before <= ctx.started_at <= after


# =============================================================================
# Action Recording Tests
# =============================================================================


class TestActionRecording:
    """Tests for action recording methods."""

    def test_record_action_increments_counters(self, context: AssessmentContext):
        """record_action increments both action counters."""
        assert context.actions_this_turn == 0
        assert context.total_actions == 0

        context.record_action()

        assert context.actions_this_turn == 1
        assert context.total_actions == 1

    def test_record_action_returns_turn_count(self, context: AssessmentContext):
        """record_action returns the new turn action count."""
        result = context.record_action()
        assert result == 1

        result = context.record_action()
        assert result == 2

    def test_record_multiple_actions(self, context: AssessmentContext):
        """Multiple record_action calls accumulate correctly."""
        for _ in range(5):
            context.record_action()

        assert context.actions_this_turn == 5
        assert context.total_actions == 5

    def test_record_actions_batch(self, context: AssessmentContext):
        """record_actions records multiple actions at once."""
        context.record_actions(3)

        assert context.actions_this_turn == 3
        assert context.total_actions == 3

    def test_record_actions_returns_turn_count(self, context: AssessmentContext):
        """record_actions returns the new turn action count."""
        context.record_action()  # 1 action
        result = context.record_actions(5)  # +5 actions

        assert result == 6

    def test_record_actions_zero(self, context: AssessmentContext):
        """record_actions with zero count is valid."""
        context.record_action()  # 1 action
        result = context.record_actions(0)

        assert result == 1
        assert context.actions_this_turn == 1

    def test_record_actions_negative_raises(self, context: AssessmentContext):
        """record_actions with negative count raises ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            context.record_actions(-1)


# =============================================================================
# Turn Management Tests
# =============================================================================


class TestTurnManagement:
    """Tests for turn management methods."""

    def test_start_new_turn_increments_turn_number(
        self, context: AssessmentContext, sample_time: datetime
    ):
        """start_new_turn increments the turn number."""
        assert context.turn_number == 0

        new_time = sample_time + timedelta(hours=1)
        context.start_new_turn(new_time, events_processed=0)

        assert context.turn_number == 1

    def test_start_new_turn_resets_actions_this_turn(
        self, context: AssessmentContext, sample_time: datetime
    ):
        """start_new_turn resets actions_this_turn to zero."""
        context.record_action()
        context.record_action()
        assert context.actions_this_turn == 2

        new_time = sample_time + timedelta(hours=1)
        context.start_new_turn(new_time, events_processed=0)

        assert context.actions_this_turn == 0

    def test_start_new_turn_preserves_total_actions(
        self, context: AssessmentContext, sample_time: datetime
    ):
        """start_new_turn preserves total_actions count."""
        context.record_action()
        context.record_action()
        assert context.total_actions == 2

        new_time = sample_time + timedelta(hours=1)
        context.start_new_turn(new_time, events_processed=0)

        assert context.total_actions == 2

    def test_start_new_turn_updates_current_time(
        self, context: AssessmentContext, sample_time: datetime
    ):
        """start_new_turn updates current_time."""
        new_time = sample_time + timedelta(hours=2)
        context.start_new_turn(new_time, events_processed=0)

        assert context.current_time == new_time

    def test_start_new_turn_updates_events_processed(
        self, context: AssessmentContext, sample_time: datetime
    ):
        """start_new_turn updates events_processed_last_turn."""
        new_time = sample_time + timedelta(hours=1)
        context.start_new_turn(new_time, events_processed=5)

        assert context.events_processed_last_turn == 5

    def test_multiple_turn_transitions(
        self, context: AssessmentContext, sample_time: datetime
    ):
        """Multiple turn transitions work correctly."""
        # Turn 0: take some actions
        context.record_action()
        context.record_action()
        assert context.turn_number == 0
        assert context.actions_this_turn == 2
        assert context.total_actions == 2

        # Turn 1
        context.start_new_turn(sample_time + timedelta(hours=1), events_processed=3)
        context.record_action()
        assert context.turn_number == 1
        assert context.actions_this_turn == 1
        assert context.total_actions == 3
        assert context.events_processed_last_turn == 3

        # Turn 2
        context.start_new_turn(sample_time + timedelta(hours=2), events_processed=0)
        context.record_action()
        context.record_action()
        context.record_action()
        assert context.turn_number == 2
        assert context.actions_this_turn == 3
        assert context.total_actions == 6
        assert context.events_processed_last_turn == 0

    def test_reset_turn_actions(self, context: AssessmentContext):
        """reset_turn_actions resets only actions_this_turn."""
        context.record_action()
        context.record_action()
        assert context.actions_this_turn == 2
        assert context.total_actions == 2

        context.reset_turn_actions()

        assert context.actions_this_turn == 0
        assert context.total_actions == 2  # Preserved


# =============================================================================
# Property Tests
# =============================================================================


class TestContextProperties:
    """Tests for AssessmentContext properties."""

    def test_elapsed_time(self, sample_time: datetime):
        """elapsed_time returns seconds since started_at."""
        fixed_start = datetime(2026, 1, 22, 9, 0, 0, tzinfo=timezone.utc)

        # Create context with explicit started_at
        ctx = AssessmentContext(
            assessment_id="test",
            ues_url="http://localhost:8000",
            api_key="key",
            current_time=sample_time,
            started_at=fixed_start,
        )

        with patch("agentbeats.purple.context._utc_now") as mock_now:
            # Check elapsed time 1 minute later
            mock_now.return_value = fixed_start + timedelta(minutes=1)
            assert ctx.elapsed_time == pytest.approx(60.0)

            # Check elapsed time 1 hour later
            mock_now.return_value = fixed_start + timedelta(hours=1)
            assert ctx.elapsed_time == pytest.approx(3600.0)

    def test_is_first_turn_true_on_turn_zero(self, context: AssessmentContext):
        """is_first_turn returns True when turn_number is 0."""
        assert context.turn_number == 0
        assert context.is_first_turn is True

    def test_is_first_turn_false_after_turn_start(
        self, context: AssessmentContext, sample_time: datetime
    ):
        """is_first_turn returns False after first turn."""
        context.start_new_turn(sample_time + timedelta(hours=1), events_processed=0)
        assert context.turn_number == 1
        assert context.is_first_turn is False


# =============================================================================
# Custom Data Tests
# =============================================================================


class TestCustomData:
    """Tests for custom data storage methods."""

    def test_set_custom(self, context: AssessmentContext):
        """set_custom stores a value."""
        context.set_custom("my_key", "my_value")
        assert context.custom_data["my_key"] == "my_value"

    def test_set_custom_overwrites(self, context: AssessmentContext):
        """set_custom overwrites existing values."""
        context.set_custom("key", "value1")
        context.set_custom("key", "value2")
        assert context.custom_data["key"] == "value2"

    def test_get_custom_existing(self, context: AssessmentContext):
        """get_custom returns stored value."""
        context.set_custom("key", "value")
        assert context.get_custom("key") == "value"

    def test_get_custom_missing_returns_none(self, context: AssessmentContext):
        """get_custom returns None for missing key."""
        assert context.get_custom("missing_key") is None

    def test_get_custom_missing_returns_default(self, context: AssessmentContext):
        """get_custom returns default for missing key."""
        assert context.get_custom("missing_key", "default") == "default"

    def test_has_custom_true(self, context: AssessmentContext):
        """has_custom returns True for existing key."""
        context.set_custom("key", "value")
        assert context.has_custom("key") is True

    def test_has_custom_false(self, context: AssessmentContext):
        """has_custom returns False for missing key."""
        assert context.has_custom("missing_key") is False

    def test_has_custom_with_none_value(self, context: AssessmentContext):
        """has_custom returns True even if value is None."""
        context.set_custom("key", None)
        assert context.has_custom("key") is True

    def test_clear_custom(self, context: AssessmentContext):
        """clear_custom removes all custom data."""
        context.set_custom("key1", "value1")
        context.set_custom("key2", "value2")
        assert len(context.custom_data) == 2

        context.clear_custom()

        assert len(context.custom_data) == 0
        assert context.get_custom("key1") is None

    def test_custom_data_various_types(self, context: AssessmentContext):
        """Custom data can store various types."""
        context.set_custom("string", "hello")
        context.set_custom("int", 42)
        context.set_custom("list", [1, 2, 3])
        context.set_custom("dict", {"nested": "value"})
        context.set_custom("set", {"a", "b"})

        assert context.get_custom("string") == "hello"
        assert context.get_custom("int") == 42
        assert context.get_custom("list") == [1, 2, 3]
        assert context.get_custom("dict") == {"nested": "value"}
        assert context.get_custom("set") == {"a", "b"}


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestCreateContextFromAssessmentStart:
    """Tests for the create_context_from_assessment_start factory function."""

    def test_creates_context_with_required_fields(self, sample_time: datetime):
        """Factory creates context with all required fields."""
        ctx = create_context_from_assessment_start(
            assessment_id="factory-test-001",
            ues_url="http://localhost:9000",
            api_key="factory-key",
            current_time=sample_time,
        )

        assert ctx.assessment_id == "factory-test-001"
        assert ctx.ues_url == "http://localhost:9000"
        assert ctx.api_key == "factory-key"
        assert ctx.current_time == sample_time

    def test_creates_context_with_initial_state(
        self, sample_time: datetime, sample_initial_state: InitialStateSummary
    ):
        """Factory accepts optional initial_state."""
        ctx = create_context_from_assessment_start(
            assessment_id="factory-test-002",
            ues_url="http://localhost:8000",
            api_key="key",
            current_time=sample_time,
            initial_state=sample_initial_state,
        )

        assert ctx.initial_state is sample_initial_state
        assert ctx.initial_state.email.total == 12

    def test_creates_context_with_default_values(self, sample_time: datetime):
        """Factory-created context has correct defaults."""
        ctx = create_context_from_assessment_start(
            assessment_id="test",
            ues_url="http://localhost:8000",
            api_key="key",
            current_time=sample_time,
        )

        assert ctx.turn_number == 0
        assert ctx.actions_this_turn == 0
        assert ctx.total_actions == 0
        assert ctx.user_instructions is None
        assert ctx.parsed_instructions is None
        assert ctx.events_processed_last_turn == 0
        assert ctx.custom_data == {}


# =============================================================================
# Integration Tests
# =============================================================================


class TestContextIntegration:
    """Integration tests simulating real assessment flows."""

    def test_full_assessment_simulation(
        self, sample_time: datetime, sample_initial_state: InitialStateSummary
    ):
        """Simulate a complete multi-turn assessment."""
        # Create context
        ctx = create_context_from_assessment_start(
            assessment_id="integration-test-001",
            ues_url="http://localhost:8000",
            api_key="test-key",
            current_time=sample_time,
            initial_state=sample_initial_state,
        )

        # Verify initial state
        assert ctx.is_first_turn
        assert ctx.turn_number == 0

        # Turn 0: Agent retrieves instructions and takes actions
        ctx.user_instructions = "Help me with my email inbox"
        ctx.set_custom("processed_emails", set())
        ctx.record_action()  # Read chat
        ctx.record_action()  # Query email
        ctx.record_action()  # Mark email as read

        assert ctx.actions_this_turn == 3
        assert ctx.total_actions == 3

        # Turn 1: Time advances, more work
        new_time = sample_time + timedelta(hours=1)
        ctx.start_new_turn(new_time, events_processed=2)

        assert not ctx.is_first_turn
        assert ctx.turn_number == 1
        assert ctx.actions_this_turn == 0
        assert ctx.events_processed_last_turn == 2

        # Agent does more work
        processed = ctx.get_custom("processed_emails")
        processed.add("email-001")
        ctx.set_custom("processed_emails", processed)
        ctx.record_actions(2)  # Batch operation

        assert ctx.actions_this_turn == 2
        assert ctx.total_actions == 5

        # Turn 2: Final turn
        ctx.start_new_turn(new_time + timedelta(hours=1), events_processed=0)

        assert ctx.turn_number == 2
        assert ctx.total_actions == 5  # Preserved

        # No more actions needed
        assert ctx.actions_this_turn == 0

        # Verify custom data persisted
        assert "email-001" in ctx.get_custom("processed_emails")
