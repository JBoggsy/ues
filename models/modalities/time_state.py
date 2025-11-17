"""Time state model."""

from models.base_state import ModalityState


class TimeState(ModalityState):
    """Current time-related state.

    Args:
        timezone: Current timezone identifier.
        format_preference: Current time format preference (12h/24h).
    """

    pass
