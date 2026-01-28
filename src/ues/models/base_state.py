"""Base class for all modality state models."""

from abc import abstractmethod
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from ues.models.base_input import ModalityInput


class ModalityState(BaseModel):
    """Base class for current state of each modality.

    Each subclass tracks the current state of that modality (e.g., EmailState with inbox contents,
    CalendarState with all events). Events apply ModalityInput instances to modify these states.
    Queried by AI agents via API.

    States represent what currently exists in a modality. They are mutable containers
    that are modified in-place by applying ModalityInput instances.

    Args:
        modality_type: Identifies which modality this state represents.
        last_updated: Simulator time when this state was last modified.
        update_count: Number of times this state has been modified.
    """

    modality_type: str = Field(
        description="Identifies which modality this state represents"
    )
    last_updated: datetime = Field(
        description="Simulator time when this state was last modified"
    )
    update_count: int = Field(
        default=0, description="Number of times this state has been modified"
    )

    @field_validator("last_updated", mode="before")
    @classmethod
    def validate_timezone_aware(cls, v: datetime | str) -> datetime:
        """Ensure datetime is timezone-aware, converting naive to UTC if needed."""
        if isinstance(v, str):
            v = datetime.fromisoformat(v.replace("Z", "+00:00"))
        if isinstance(v, datetime) and v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v

    @abstractmethod
    def apply_input(self, input_data: "ModalityInput") -> None:
        """Apply a ModalityInput to modify this state.

        This is the core state mutation method. Each subclass implements
        the specific logic for how inputs change state. This method modifies
        state in-place rather than returning a new state.

        The implementation should:
        1. Validate that input_data is the correct type
        2. Apply the changes described by input_data
        3. Update last_updated timestamp
        4. Increment update_count

        Examples:
            - EmailState.apply_input(EmailInput): Add email to inbox, update thread
            - LocationState.apply_input(LocationInput): Update current location, add to history
            - SMSState.apply_input(SMSInput): Add message to conversation

        Args:
            input_data: The ModalityInput to apply to this state.

        Raises:
            ValueError: If input_data is wrong type or incompatible.
            RuntimeError: If state is in invalid condition for this input.
        """
        pass

    @abstractmethod
    def get_snapshot(self) -> dict[str, Any]:
        """Return a complete snapshot of current state for API responses.

        This is what external agents see when they query the modality.
        Should include all relevant information but may omit internal metadata.

        The snapshot should be JSON-serializable and suitable for transmission
        over REST API.

        Examples:
            - EmailState: Returns {inbox: [...], sent: [...], unread_count: 5}
            - LocationState: Returns {current: {...}, history: [...]}

        Returns:
            Dictionary representation of current state suitable for API responses.
        """
        pass

    @abstractmethod
    def validate_state(self) -> list[str]:
        """Validate internal state consistency and return any issues.

        After applying many inputs, state might become inconsistent. This method
        catches corruption and helps with debugging.

        Examples:
            - EmailState: Check all thread_ids reference existing threads
            - CalendarState: Check no overlapping events (if that's a constraint)
            - SMSState: Verify all conversations have at least one message

        Returns:
            List of validation error messages (empty list if valid).
        """
        pass

    @abstractmethod
    def query(self, query_params: dict[str, Any]) -> dict[str, Any]:
        """Execute a query against this state.

        Allows filtering, searching, and aggregating state data without
        exposing internal structure. States can be large (thousands of emails),
        so agents need efficient querying.

        Each modality defines its own query parameters based on its needs.

        Examples:
            - EmailState.query({type: "unread", limit: 10}): Get 10 unread emails
            - SMSState.query({from: "555-1234", since: datetime(...)}): Get messages from number
            - CalendarState.query({date: "2024-03-15"}): Get events on specific date

        Args:
            query_params: Dictionary of query parameters (modality-specific).

        Returns:
            Dictionary containing query results.
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Reset this state to its empty default.

        Clears all data from this modality state, returning it to the same
        condition as a freshly created instance. This is used by the simulation
        clear functionality to completely empty the environment.

        The implementation should:
        1. Clear all stored data (messages, events, history, etc.)
        2. Reset any counters or metadata to initial values
        3. Keep modality_type unchanged (it's frozen)
        4. Update last_updated to current time
        5. Reset update_count to 0

        Examples:
            - EmailState.clear(): Empty inbox, sent, drafts; clear all threads
            - LocationState.clear(): Reset current location to None, clear history
            - ChatState.clear(): Clear all conversations and messages

        After calling clear(), the state should pass validate_state() with no errors.
        """
        pass

    @abstractmethod
    def create_undo_data(self, input_data: "ModalityInput") -> dict[str, Any]:
        """Capture minimal data needed to undo applying the given input.

        Called BEFORE apply_input() to capture current state that will be lost.
        The returned data should be as space-efficient as possible:
        - For additive operations: Store only IDs/keys to remove
        - For destructive operations: Store full objects being replaced/deleted

        This method should NOT modify state - it only captures undo information.

        Examples:
            - EmailState receiving new email: Return {"action": "remove", "email_id": "..."}
            - EmailState deleting email: Return {"action": "restore", "email": {...full email...}}
            - WeatherState updating location: Return previous report if updating, or location key if new

        Args:
            input_data: The ModalityInput that will be applied.

        Returns:
            Dictionary containing minimal data needed to undo the operation.
            Must include an "action" key describing the undo operation type.
        """
        pass

    @abstractmethod
    def apply_undo(self, undo_data: dict[str, Any]) -> None:
        """Apply undo data to reverse a previous input application.

        Restores the state to what it was before the corresponding apply_input() call.
        The undo_data comes from a previous create_undo_data() call.

        This method modifies state in-place. After applying undo, the state should
        be identical to what it was before the original input was applied.

        Args:
            undo_data: Dictionary returned by create_undo_data() for the operation to undo.

        Raises:
            ValueError: If undo_data is invalid or corrupted.
            RuntimeError: If state has been modified in a way that prevents undo.
        """
        pass

    def get_diff(self, other: "ModalityState") -> dict[str, Any]:
        """Calculate difference between this state and another state.

        Useful for showing what changed, implementing undo, or incremental updates.
        This is an optional method that subclasses can override if needed.

        Args:
            other: Another state of the same type to compare against.

        Returns:
            Dictionary describing the differences.
        """
        return {"error": "get_diff not implemented for this modality"}

    def get_compact_snapshot(self, current_time: datetime) -> dict[str, Any]:
        """Return a compact, LLM-context-optimized snapshot of this modality's state.

        Unlike get_snapshot() which returns complete state, this method returns
        only the most relevant information for AI agent context injection.
        This is used by the compact=true parameter on /environment/state.

        The compact snapshot should include:
        - A brief summary string
        - Key statistics (counts, unread, etc.)
        - Recent/relevant items without full content
        - Current state essentials (location, weather conditions, etc.)

        Subclasses should override this to provide meaningful compact data
        specific to their modality. The default implementation returns just
        the summary property for graceful degradation.

        Args:
            current_time: The current simulator time (for calculating relative times).

        Returns:
            Dictionary with compact state suitable for LLM context windows.
            Should be significantly smaller than get_snapshot() output.
        """
        return {"summary": self.summary}

    @staticmethod
    def _format_relative_time(dt: datetime, current_time: datetime) -> str:
        """Format a datetime as a human-readable relative time string.

        Helper method for get_compact_snapshot() implementations.

        Args:
            dt: The datetime to format.
            current_time: The current simulator time to calculate relative to.

        Returns:
            Human-readable string like "2 hours ago", "in 30 minutes", "just now".
        """
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        diff = current_time - dt
        total_seconds = diff.total_seconds()
        abs_seconds = abs(total_seconds)

        # Future times
        if total_seconds < 0:
            if abs_seconds < 60:
                return "in less than a minute"
            elif abs_seconds < 3600:
                minutes = int(abs_seconds / 60)
                return f"in {minutes} minute{'s' if minutes != 1 else ''}"
            elif abs_seconds < 86400:
                hours = int(abs_seconds / 3600)
                return f"in {hours} hour{'s' if hours != 1 else ''}"
            else:
                days = int(abs_seconds / 86400)
                return f"in {days} day{'s' if days != 1 else ''}"

        # Past times
        if abs_seconds < 60:
            return "just now"
        elif abs_seconds < 3600:
            minutes = int(abs_seconds / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif abs_seconds < 86400:
            hours = int(abs_seconds / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = int(abs_seconds / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"

    @property
    def summary(self) -> str:
        """Return a brief human-readable summary of the current state.

        This is used by the /environment/state endpoint to provide quick
        overviews of each modality without returning full state data.

        Subclasses should override this to provide meaningful summaries
        specific to their modality (e.g., "3 unread emails, 5 total" for email).

        Returns:
            A brief summary string describing the current state.
        """
        return f"{self.modality_type} state (override summary property for details)"
