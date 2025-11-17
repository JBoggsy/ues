"""Slack input model."""

from models.base_input import ModalityInput


class SlackInput(ModalityInput):
    """Input for Slack events.

    Args:
        workspace_id: Slack workspace ID.
        channel_id: Slack channel ID.
        message_content: Message content (for new messages).
        author: Message author information.
        thread_ts: Optional thread timestamp for threaded messages.
        event_type: Type of event (message, reaction, etc.).
    """

    pass
