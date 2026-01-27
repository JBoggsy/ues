"""Tests for Purple Agent schemas.

This module tests the schema definitions for Purple Agent A2A messages,
including re-exported green schemas and purple-specific models.
"""

from datetime import timedelta

import pytest

from agentbeats.purple.schemas import (
    # Re-exported from green
    ModalityCounts,
    InitialStateSummary,
    AssessmentStartMessage,
    TurnStartMessage,
    AssessmentCompleteMessage,
    AssessmentCompleteReason,
    TurnCompleteMessage,
    EarlyCompletionMessage,
    DEFAULT_ASSESSMENT_INSTRUCTIONS,
    GreenToPurpleMessage,
    PurpleToGreenMessage,
    # Purple-specific
    ParsedGoal,
    ParsedConstraint,
    ParsedUserInstructions,
    TurnResponse,
)


# =============================================================================
# Re-exported Schema Tests (verify imports work)
# =============================================================================


class TestReExportedSchemas:
    """Tests verifying that green schemas are properly re-exported."""

    def test_modality_counts_import(self):
        """ModalityCounts can be imported from purple.schemas."""
        counts = ModalityCounts(total=10, unread=5)
        assert counts.total == 10
        assert counts.unread == 5

    def test_initial_state_summary_import(self):
        """InitialStateSummary can be imported from purple.schemas."""
        summary = InitialStateSummary(
            email=ModalityCounts(total=12, unread=5),
            calendar=ModalityCounts(total=8, events_today=3),
        )
        assert summary.email.total == 12
        assert summary.calendar.events_today == 3

    def test_assessment_start_message_import(self):
        """AssessmentStartMessage can be imported from purple.schemas."""
        from datetime import datetime, timezone

        msg = AssessmentStartMessage(
            ues_url="http://localhost:8000",
            api_key="test-key",
            current_time=datetime(2026, 1, 22, 9, 0, tzinfo=timezone.utc),
            initial_state_summary=InitialStateSummary(),
        )
        assert msg.ues_url == "http://localhost:8000"
        assert msg.assessment_instructions == DEFAULT_ASSESSMENT_INSTRUCTIONS

    def test_turn_start_message_import(self):
        """TurnStartMessage can be imported from purple.schemas."""
        from datetime import datetime, timezone

        msg = TurnStartMessage(
            current_time=datetime(2026, 1, 22, 10, 0, tzinfo=timezone.utc),
            events_processed=3,
        )
        assert msg.events_processed == 3

    def test_assessment_complete_message_import(self):
        """AssessmentCompleteMessage can be imported from purple.schemas."""
        msg = AssessmentCompleteMessage(
            reason=AssessmentCompleteReason.SCENARIO_COMPLETE,
            message="Assessment finished successfully",
        )
        assert msg.reason == AssessmentCompleteReason.SCENARIO_COMPLETE

    def test_turn_complete_message_import(self):
        """TurnCompleteMessage can be imported from purple.schemas."""
        msg = TurnCompleteMessage(
            actions_taken=3,
            notes="Processed 3 emails",
            time_step=timedelta(hours=1),
        )
        assert msg.actions_taken == 3
        assert msg.time_step == timedelta(hours=1)

    def test_early_completion_message_import(self):
        """EarlyCompletionMessage can be imported from purple.schemas."""
        msg = EarlyCompletionMessage(reason="All goals achieved")
        assert msg.reason == "All goals achieved"

    def test_default_instructions_constant(self):
        """DEFAULT_ASSESSMENT_INSTRUCTIONS is available."""
        assert "chat" in DEFAULT_ASSESSMENT_INSTRUCTIONS.lower()
        assert "user" in DEFAULT_ASSESSMENT_INSTRUCTIONS.lower()

    def test_type_aliases_exist(self):
        """Type aliases are properly exported."""
        # These are type aliases, so we just verify they exist
        assert GreenToPurpleMessage is not None
        assert PurpleToGreenMessage is not None
        assert TurnResponse is not None


# =============================================================================
# ParsedGoal Tests
# =============================================================================


class TestParsedGoal:
    """Tests for the ParsedGoal model."""

    def test_create_basic_goal(self):
        """Create a goal with required fields only."""
        goal = ParsedGoal(description="Reply to urgent emails")
        assert goal.description == "Reply to urgent emails"
        assert goal.priority == 0  # default
        assert goal.completed is False  # default

    def test_create_goal_with_all_fields(self):
        """Create a goal with all fields specified."""
        goal = ParsedGoal(
            description="Schedule meeting",
            priority=5,
            completed=True,
        )
        assert goal.description == "Schedule meeting"
        assert goal.priority == 5
        assert goal.completed is True

    def test_goal_priority_must_be_non_negative(self):
        """Priority cannot be negative."""
        with pytest.raises(ValueError):
            ParsedGoal(description="Test", priority=-1)

    def test_goal_is_mutable(self):
        """Goal completed status can be changed."""
        goal = ParsedGoal(description="Test")
        assert goal.completed is False
        goal.completed = True
        assert goal.completed is True


# =============================================================================
# ParsedConstraint Tests
# =============================================================================


class TestParsedConstraint:
    """Tests for the ParsedConstraint model."""

    def test_create_basic_constraint(self):
        """Create a constraint with required fields only."""
        constraint = ParsedConstraint(description="Don't delete emails")
        assert constraint.description == "Don't delete emails"
        assert constraint.violated is False  # default

    def test_create_constraint_with_violated_flag(self):
        """Create a constraint marked as violated."""
        constraint = ParsedConstraint(
            description="Stay under budget",
            violated=True,
        )
        assert constraint.violated is True

    def test_constraint_is_mutable(self):
        """Constraint violated status can be changed."""
        constraint = ParsedConstraint(description="Test")
        assert constraint.violated is False
        constraint.violated = True
        assert constraint.violated is True


# =============================================================================
# ParsedUserInstructions Tests
# =============================================================================


class TestParsedUserInstructions:
    """Tests for the ParsedUserInstructions model."""

    def test_create_with_raw_content_only(self):
        """Create instructions with just raw content."""
        instructions = ParsedUserInstructions(raw_content="Help me with email")
        assert instructions.raw_content == "Help me with email"
        assert instructions.goals == []
        assert instructions.constraints == []
        assert instructions.context is None
        assert instructions.metadata == {}

    def test_create_with_all_fields(self):
        """Create instructions with all fields specified."""
        instructions = ParsedUserInstructions(
            raw_content="Help me with email",
            goals=[
                ParsedGoal(description="Goal 1", priority=2),
                ParsedGoal(description="Goal 2", priority=1),
            ],
            constraints=[
                ParsedConstraint(description="Constraint 1"),
            ],
            context="User is on vacation",
            metadata={"source": "chat"},
        )
        assert len(instructions.goals) == 2
        assert len(instructions.constraints) == 1
        assert instructions.context == "User is on vacation"
        assert instructions.metadata["source"] == "chat"

    def test_mark_goal_completed(self):
        """mark_goal_completed sets the correct goal's completed flag."""
        instructions = ParsedUserInstructions(
            raw_content="Test",
            goals=[
                ParsedGoal(description="Goal 1"),
                ParsedGoal(description="Goal 2"),
            ],
        )
        assert instructions.goals[0].completed is False
        assert instructions.goals[1].completed is False

        instructions.mark_goal_completed(0)

        assert instructions.goals[0].completed is True
        assert instructions.goals[1].completed is False

    def test_mark_goal_completed_invalid_index(self):
        """mark_goal_completed raises IndexError for invalid index."""
        instructions = ParsedUserInstructions(
            raw_content="Test",
            goals=[ParsedGoal(description="Goal 1")],
        )
        with pytest.raises(IndexError):
            instructions.mark_goal_completed(5)

    def test_mark_constraint_violated(self):
        """mark_constraint_violated sets the correct constraint's violated flag."""
        instructions = ParsedUserInstructions(
            raw_content="Test",
            constraints=[
                ParsedConstraint(description="Constraint 1"),
                ParsedConstraint(description="Constraint 2"),
            ],
        )
        assert instructions.constraints[0].violated is False
        assert instructions.constraints[1].violated is False

        instructions.mark_constraint_violated(1)

        assert instructions.constraints[0].violated is False
        assert instructions.constraints[1].violated is True

    def test_mark_constraint_violated_invalid_index(self):
        """mark_constraint_violated raises IndexError for invalid index."""
        instructions = ParsedUserInstructions(
            raw_content="Test",
            constraints=[ParsedConstraint(description="Constraint 1")],
        )
        with pytest.raises(IndexError):
            instructions.mark_constraint_violated(5)

    def test_all_goals_completed_with_no_goals(self):
        """all_goals_completed returns True when there are no goals."""
        instructions = ParsedUserInstructions(raw_content="Test")
        assert instructions.all_goals_completed is True

    def test_all_goals_completed_when_none_completed(self):
        """all_goals_completed returns False when no goals are completed."""
        instructions = ParsedUserInstructions(
            raw_content="Test",
            goals=[
                ParsedGoal(description="Goal 1"),
                ParsedGoal(description="Goal 2"),
            ],
        )
        assert instructions.all_goals_completed is False

    def test_all_goals_completed_when_some_completed(self):
        """all_goals_completed returns False when only some goals are completed."""
        instructions = ParsedUserInstructions(
            raw_content="Test",
            goals=[
                ParsedGoal(description="Goal 1", completed=True),
                ParsedGoal(description="Goal 2", completed=False),
            ],
        )
        assert instructions.all_goals_completed is False

    def test_all_goals_completed_when_all_completed(self):
        """all_goals_completed returns True when all goals are completed."""
        instructions = ParsedUserInstructions(
            raw_content="Test",
            goals=[
                ParsedGoal(description="Goal 1", completed=True),
                ParsedGoal(description="Goal 2", completed=True),
            ],
        )
        assert instructions.all_goals_completed is True

    def test_any_constraint_violated_with_no_constraints(self):
        """any_constraint_violated returns False when there are no constraints."""
        instructions = ParsedUserInstructions(raw_content="Test")
        assert instructions.any_constraint_violated is False

    def test_any_constraint_violated_when_none_violated(self):
        """any_constraint_violated returns False when no constraints are violated."""
        instructions = ParsedUserInstructions(
            raw_content="Test",
            constraints=[
                ParsedConstraint(description="Constraint 1"),
                ParsedConstraint(description="Constraint 2"),
            ],
        )
        assert instructions.any_constraint_violated is False

    def test_any_constraint_violated_when_one_violated(self):
        """any_constraint_violated returns True when at least one is violated."""
        instructions = ParsedUserInstructions(
            raw_content="Test",
            constraints=[
                ParsedConstraint(description="Constraint 1", violated=False),
                ParsedConstraint(description="Constraint 2", violated=True),
            ],
        )
        assert instructions.any_constraint_violated is True

    def test_pending_goals_with_no_goals(self):
        """pending_goals returns empty list when there are no goals."""
        instructions = ParsedUserInstructions(raw_content="Test")
        assert instructions.pending_goals == []

    def test_pending_goals_returns_incomplete_goals(self):
        """pending_goals returns only goals that are not completed."""
        instructions = ParsedUserInstructions(
            raw_content="Test",
            goals=[
                ParsedGoal(description="Goal 1", completed=True),
                ParsedGoal(description="Goal 2", completed=False),
                ParsedGoal(description="Goal 3", completed=False),
            ],
        )
        pending = instructions.pending_goals
        assert len(pending) == 2
        assert pending[0].description == "Goal 2"
        assert pending[1].description == "Goal 3"

    def test_pending_goals_sorted_by_priority(self):
        """pending_goals returns goals sorted by priority (highest first)."""
        instructions = ParsedUserInstructions(
            raw_content="Test",
            goals=[
                ParsedGoal(description="Low priority", priority=1),
                ParsedGoal(description="High priority", priority=10),
                ParsedGoal(description="Medium priority", priority=5),
            ],
        )
        pending = instructions.pending_goals
        assert len(pending) == 3
        assert pending[0].description == "High priority"
        assert pending[1].description == "Medium priority"
        assert pending[2].description == "Low priority"

    def test_pending_goals_excludes_completed(self):
        """pending_goals excludes completed goals from result."""
        instructions = ParsedUserInstructions(
            raw_content="Test",
            goals=[
                ParsedGoal(description="Completed high", priority=10, completed=True),
                ParsedGoal(description="Pending low", priority=1, completed=False),
            ],
        )
        pending = instructions.pending_goals
        assert len(pending) == 1
        assert pending[0].description == "Pending low"


# =============================================================================
# TurnResponse Type Alias Tests
# =============================================================================


class TestTurnResponseTypeAlias:
    """Tests for the TurnResponse type alias."""

    def test_turn_complete_is_valid_turn_response(self):
        """TurnCompleteMessage is a valid TurnResponse."""
        response: TurnResponse = TurnCompleteMessage(actions_taken=1)
        assert isinstance(response, TurnCompleteMessage)

    def test_early_completion_is_valid_turn_response(self):
        """EarlyCompletionMessage is a valid TurnResponse."""
        response: TurnResponse = EarlyCompletionMessage(reason="Done")
        assert isinstance(response, EarlyCompletionMessage)
