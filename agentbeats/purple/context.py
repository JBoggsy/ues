"""Assessment context for tracking Purple Agent state.

This module provides the AssessmentContext class that maintains state across
the assessment lifecycle. It tracks timing, actions, and provides convenient
methods for state management.

Example:
    Creating and using an assessment context::

        from datetime import datetime, timezone
        from agentbeats.purple.context import AssessmentContext
        from agentbeats.purple.schemas import InitialStateSummary, ModalityCounts

        # Create context from assessment_start message
        context = AssessmentContext(
            assessment_id="test-001",
            ues_url="http://localhost:8000",
            api_key="ues_user_abc123",
            current_time=datetime(2026, 1, 22, 9, 0, tzinfo=timezone.utc),
            initial_state=InitialStateSummary(
                email=ModalityCounts(total=12, unread=5),
            ),
        )

        # Record actions during a turn
        context.record_action()
        context.record_action()
        print(f"Actions this turn: {context.actions_this_turn}")  # 2

        # Start a new turn (after receiving turn_start)
        new_time = datetime(2026, 1, 22, 10, 0, tzinfo=timezone.utc)
        context.start_new_turn(new_time, events_processed=3)
        print(f"Turn: {context.turn_number}, Actions: {context.actions_this_turn}")  # 1, 0
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from agentbeats.purple.schemas import InitialStateSummary, ParsedUserInstructions


def _utc_now() -> datetime:
    """Get current UTC time.

    Returns:
        Current datetime with UTC timezone.
    """
    return datetime.now(timezone.utc)


@dataclass
class AssessmentContext:
    """Tracks the current state of an assessment.

    This context object is passed to agent lifecycle methods and maintains
    state across the turn loop. Agents can use it to track progress, store
    parsed instructions, and manage action counts.

    Attributes:
        assessment_id: Unique identifier for this assessment (from A2A task ID).
        ues_url: Base URL for UES REST API.
        api_key: API key for UES authentication.
        current_time: Current simulator time.
        turn_number: Current turn number (0 = first turn, increments after each turn_start).
        actions_this_turn: Number of actions taken in current turn.
        total_actions: Total actions across all turns.
        user_instructions: Raw user instructions text from chat (set by agent).
        parsed_instructions: Structured parsed instructions (optional, set by agent).
        initial_state: InitialStateSummary from assessment_start message.
        started_at: Wall-clock time when assessment started.
        events_processed_last_turn: Number of events that fired during last time advance.
        custom_data: Arbitrary agent-specific data storage.

    Example:
        Basic usage in an agent::

            async def execute_turn(self, context: AssessmentContext, ues) -> TurnResponse:
                # Query state
                email_state = ues.email.get_state()

                # Take actions and track them
                for email in email_state.emails:
                    if not email.read:
                        ues.email.mark_read(email.message_id)
                        context.record_action()

                return TurnCompleteMessage(
                    actions_taken=context.actions_this_turn,
                    notes=f"Marked {context.actions_this_turn} emails as read",
                )
    """

    # Required fields (set at assessment start)
    assessment_id: str
    ues_url: str
    api_key: str
    current_time: datetime

    # Turn tracking
    turn_number: int = 0
    actions_this_turn: int = 0
    total_actions: int = 0

    # User instructions (set by agent after retrieval)
    user_instructions: str | None = None
    parsed_instructions: ParsedUserInstructions | None = None

    # Initial state from assessment_start
    initial_state: InitialStateSummary | None = None

    # Timing
    started_at: datetime = field(default_factory=_utc_now)
    events_processed_last_turn: int = 0

    # Agent-specific storage
    custom_data: dict[str, Any] = field(default_factory=dict)

    def record_action(self) -> int:
        """Record that an action was taken.

        Call this method after each UES API action (send email, create event, etc.)
        to track action counts for reporting in turn_complete.

        Returns:
            The new total action count for this turn.

        Example:
            Recording actions during a turn::

                ues.email.send(...)
                context.record_action()

                ues.email.archive(...)
                context.record_action()

                # actions_this_turn is now 2
        """
        self.actions_this_turn += 1
        self.total_actions += 1
        return self.actions_this_turn

    def record_actions(self, count: int) -> int:
        """Record multiple actions at once.

        Convenience method for recording multiple actions in a batch operation.

        Args:
            count: Number of actions to record.

        Returns:
            The new total action count for this turn.

        Raises:
            ValueError: If count is negative.

        Example:
            Recording batch actions::

                # Mark 5 emails as read in a loop
                for email in unread_emails:
                    ues.email.mark_read(email.message_id)
                context.record_actions(len(unread_emails))
        """
        if count < 0:
            raise ValueError(f"Action count cannot be negative: {count}")
        self.actions_this_turn += count
        self.total_actions += count
        return self.actions_this_turn

    def start_new_turn(self, current_time: datetime, events_processed: int) -> None:
        """Begin a new turn, updating time and resetting per-turn counters.

        Called automatically by the executor when a turn_start message is received.
        Agents typically don't need to call this directly.

        Args:
            current_time: The new simulator time after advancement.
            events_processed: Number of events that fired during time advance.

        Example:
            Manual turn start (usually handled by executor)::

                context.start_new_turn(
                    current_time=turn_start_msg.current_time,
                    events_processed=turn_start_msg.events_processed,
                )
        """
        self.turn_number += 1
        self.actions_this_turn = 0
        self.current_time = current_time
        self.events_processed_last_turn = events_processed

    def reset_turn_actions(self) -> None:
        """Reset action counter for current turn without incrementing turn number.

        Useful if an agent needs to retry a turn or reset mid-turn for any reason.
        Note: This does NOT affect total_actions.
        """
        self.actions_this_turn = 0

    @property
    def elapsed_time(self) -> float:
        """Get elapsed wall-clock time since assessment started.

        Returns:
            Elapsed time in seconds.
        """
        return (_utc_now() - self.started_at).total_seconds()

    @property
    def is_first_turn(self) -> bool:
        """Check if this is the first turn of the assessment.

        Returns:
            True if turn_number is 0.
        """
        return self.turn_number == 0

    def set_custom(self, key: str, value: Any) -> None:
        """Store a custom value in the context.

        Agents can use this for any agent-specific state that needs to
        persist across turns.

        Args:
            key: Storage key.
            value: Value to store.

        Example:
            Storing custom state::

                # Track which emails we've already processed
                context.set_custom("processed_email_ids", {"msg-1", "msg-2"})

                # Later...
                processed = context.get_custom("processed_email_ids", set())
        """
        self.custom_data[key] = value

    def get_custom(self, key: str, default: Any = None) -> Any:
        """Retrieve a custom value from the context.

        Args:
            key: Storage key.
            default: Default value if key not found.

        Returns:
            The stored value, or default if not found.
        """
        return self.custom_data.get(key, default)

    def has_custom(self, key: str) -> bool:
        """Check if a custom key exists.

        Args:
            key: Storage key.

        Returns:
            True if the key exists in custom_data.
        """
        return key in self.custom_data

    def clear_custom(self) -> None:
        """Clear all custom data."""
        self.custom_data.clear()


def create_context_from_assessment_start(
    assessment_id: str,
    ues_url: str,
    api_key: str,
    current_time: datetime,
    initial_state: InitialStateSummary | None = None,
) -> AssessmentContext:
    """Create an AssessmentContext from assessment_start message data.

    Factory function for creating a context with the required fields
    from an assessment_start message.

    Args:
        assessment_id: Unique assessment identifier (A2A task ID).
        ues_url: Base URL for UES REST API.
        api_key: API key for UES authentication.
        current_time: Initial simulator time.
        initial_state: Optional initial state summary.

    Returns:
        A new AssessmentContext initialized with the provided values.

    Example:
        Creating context in executor::

            context = create_context_from_assessment_start(
                assessment_id=task.id,
                ues_url=msg.ues_url,
                api_key=msg.api_key,
                current_time=msg.current_time,
                initial_state=msg.initial_state_summary,
            )
    """
    return AssessmentContext(
        assessment_id=assessment_id,
        ues_url=ues_url,
        api_key=api_key,
        current_time=current_time,
        initial_state=initial_state,
    )


__all__ = [
    "AssessmentContext",
    "create_context_from_assessment_start",
]
