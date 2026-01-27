"""A2A message schemas for Purple Agent communication.

This module re-exports the shared message schemas from the green agent module
and adds any purple-specific schemas needed for agent implementations.

The shared schemas define the A2A message format for Green-Purple communication:
    - Green → Purple: AssessmentStartMessage, TurnStartMessage, AssessmentCompleteMessage
    - Purple → Green: TurnCompleteMessage, EarlyCompletionMessage

Example:
    Importing schemas for use in a Purple Agent::

        from agentbeats.purple.schemas import (
            AssessmentStartMessage,
            TurnStartMessage,
            TurnCompleteMessage,
            EarlyCompletionMessage,
        )

    Creating a turn complete response::

        from datetime import timedelta

        response = TurnCompleteMessage(
            actions_taken=3,
            notes="Replied to 2 urgent emails, archived 1 spam thread",
            time_step=timedelta(hours=1),
        )
"""

from datetime import timedelta
from typing import Any

from pydantic import BaseModel, Field

# =============================================================================
# Re-exports from Green Agent Schemas
# =============================================================================

# These are the canonical message definitions shared between Green and Purple agents.
# We re-export them here so Purple agent developers can import from a single location.

from agentbeats.green.schemas import (
    # Initial state summary
    ModalityCounts,
    InitialStateSummary,
    # Green → Purple messages
    AssessmentStartMessage,
    TurnStartMessage,
    AssessmentCompleteMessage,
    AssessmentCompleteReason,
    DEFAULT_ASSESSMENT_INSTRUCTIONS,
    # Purple → Green messages
    TurnCompleteMessage,
    EarlyCompletionMessage,
    # Type aliases
    GreenToPurpleMessage,
    PurpleToGreenMessage,
)


# =============================================================================
# Purple-Specific Schemas
# =============================================================================


class ParsedGoal(BaseModel):
    """A single goal parsed from user instructions.

    Attributes:
        description: Human-readable description of the goal.
        priority: Optional priority level (higher = more important).
        completed: Whether this goal has been achieved.
    """

    description: str = Field(..., description="Human-readable description of the goal")
    priority: int = Field(default=0, ge=0, description="Priority level (higher = more important)")
    completed: bool = Field(default=False, description="Whether this goal has been achieved")


class ParsedConstraint(BaseModel):
    """A constraint/rule parsed from user instructions.

    Attributes:
        description: Human-readable description of the constraint.
        violated: Whether this constraint has been violated.
    """

    description: str = Field(..., description="Human-readable description of the constraint")
    violated: bool = Field(default=False, description="Whether this constraint has been violated")


class ParsedUserInstructions(BaseModel):
    """Structured representation of user instructions from chat.

    This is an optional convenience model for agents that want to parse
    user instructions into a structured format. Agents can use their own
    parsing approach if preferred.

    Attributes:
        raw_content: The original raw text from the chat message.
        goals: List of parsed goals/objectives.
        constraints: List of parsed constraints/rules.
        context: Any additional context or background information.
        metadata: Arbitrary additional data from parsing.
    """

    raw_content: str = Field(..., description="Original raw text from chat message")
    goals: list[ParsedGoal] = Field(
        default_factory=list,
        description="Parsed goals/objectives",
    )
    constraints: list[ParsedConstraint] = Field(
        default_factory=list,
        description="Parsed constraints/rules",
    )
    context: str | None = Field(
        default=None,
        description="Additional context or background information",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary additional data from parsing",
    )

    def mark_goal_completed(self, index: int) -> None:
        """Mark a goal as completed by index.

        Args:
            index: Index of the goal to mark as completed.

        Raises:
            IndexError: If index is out of range.
        """
        self.goals[index].completed = True

    def mark_constraint_violated(self, index: int) -> None:
        """Mark a constraint as violated by index.

        Args:
            index: Index of the constraint to mark as violated.

        Raises:
            IndexError: If index is out of range.
        """
        self.constraints[index].violated = True

    @property
    def all_goals_completed(self) -> bool:
        """Check if all goals have been completed.

        Returns:
            True if all goals are marked as completed (or no goals exist).
        """
        return all(goal.completed for goal in self.goals)

    @property
    def any_constraint_violated(self) -> bool:
        """Check if any constraint has been violated.

        Returns:
            True if any constraint is marked as violated.
        """
        return any(constraint.violated for constraint in self.constraints)

    @property
    def pending_goals(self) -> list[ParsedGoal]:
        """Get list of goals that haven't been completed yet.

        Returns:
            List of incomplete goals, sorted by priority (highest first).
        """
        return sorted(
            [g for g in self.goals if not g.completed],
            key=lambda g: g.priority,
            reverse=True,
        )


# =============================================================================
# Convenience Type Aliases
# =============================================================================

# Response type for execute_turn method
TurnResponse = TurnCompleteMessage | EarlyCompletionMessage


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Re-exported from green schemas
    "ModalityCounts",
    "InitialStateSummary",
    "AssessmentStartMessage",
    "TurnStartMessage",
    "AssessmentCompleteMessage",
    "AssessmentCompleteReason",
    "DEFAULT_ASSESSMENT_INSTRUCTIONS",
    "TurnCompleteMessage",
    "EarlyCompletionMessage",
    "GreenToPurpleMessage",
    "PurpleToGreenMessage",
    # Purple-specific
    "ParsedGoal",
    "ParsedConstraint",
    "ParsedUserInstructions",
    "TurnResponse",
]
