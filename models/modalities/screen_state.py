"""Screen simulation state model."""

from models.base_state import ModalityState


class ScreenState(ModalityState):
    """Current screen/UI state.

    Args:
        current_app: Currently active application.
        current_window: Currently active window.
        ui_elements: Dictionary of visible UI elements and their states.
        interaction_history: List of recent interactions.
    """

    pass
