"""Screen simulation input model."""

from models.base_input import ModalityInput


class ScreenInput(ModalityInput):
    """Input for screen/UI interactions.

    Args:
        app: Application name.
        window: Window identifier.
        interaction_type: Type of interaction (click, type, scroll, etc.).
        target_element: Target UI element identifier.
        interaction_data: Additional interaction-specific data.
    """

    pass
