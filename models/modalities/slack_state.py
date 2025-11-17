"""Slack state model."""

from models.base_state import ModalityState


class SlackState(ModalityState):
    """Current Slack state.

    Args:
        workspaces: Dictionary mapping workspace IDs to workspace information.
        channels: Dictionary mapping channel IDs to channel information.
        message_history: Dictionary mapping channel IDs to message lists.
        threads: Dictionary mapping thread timestamps to message lists.
        users: Dictionary mapping user IDs to user information.
    """

    pass
