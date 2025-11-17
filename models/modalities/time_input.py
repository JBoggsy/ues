"""Time input model."""

from models.base_input import ModalityInput


class TimeInput(ModalityInput):
    """Input for updating time-related settings.

    Args:
        timezone: New timezone identifier (e.g., "America/New_York").
        format_preference: Optional time format preference (12h/24h).
    """

    pass
