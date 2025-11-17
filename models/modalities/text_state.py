"""Text (SMS/RCS) state model."""

from models.base_state import ModalityState


class TextState(ModalityState):
    """Current text message state.

    Args:
        conversations: Dictionary mapping conversation ID to list of messages.
        read_status: Dictionary mapping message ID to read status.
        contacts: Dictionary mapping phone numbers to contact names.
    """

    pass
