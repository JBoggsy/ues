"""Base class for all modality state models."""

from abc import abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from models.base_input import ModalityInput


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
