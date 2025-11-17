"""Chat state model."""

from models.base_state import ModalityState


class ChatState(ModalityState):
    """Current chat conversation state.

    Args:
        conversation_history: List of all messages in the conversation.
        current_turn: Whose turn it is (user/assistant).
        is_active: Whether a conversation is currently active.
    """

    pass
