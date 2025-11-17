"""Calendar state model."""

from models.base_state import ModalityState


class CalendarState(ModalityState):
    """Current calendar state.

    Args:
        events: List of all calendar events.
        recurring_events: List of recurring event definitions.
    """

    pass
