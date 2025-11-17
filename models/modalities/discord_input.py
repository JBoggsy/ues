"""Discord input model."""

from models.base_input import ModalityInput


class DiscordInput(ModalityInput):
    """Input for Discord events.

    Args:
        server_id: Discord server ID.
        channel_id: Discord channel ID.
        message_content: Message content (for new messages).
        author: Message author information.
        event_type: Type of event (message, reaction, etc.).
    """

    pass
