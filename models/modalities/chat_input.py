"""Chat input model."""

from models.base_input import ModalityInput


class ChatInput(ModalityInput):
    """Input for new chat messages.

    Args:
        role: Role of the message sender (user/assistant).
        content: Message content.
        timestamp: When the message was sent (simulator time).
    """

    pass
