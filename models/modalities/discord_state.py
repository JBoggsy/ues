"""Discord state model."""

from models.base_state import ModalityState


class DiscordState(ModalityState):
    """Current Discord state.

    Args:
        servers: Dictionary mapping server IDs to server information.
        channels: Dictionary mapping channel IDs to channel information.
        message_history: Dictionary mapping channel IDs to message lists.
        users: Dictionary mapping user IDs to user information.
    """

    pass
