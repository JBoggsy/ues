"""Text (SMS/RCS) input model."""

from models.base_input import ModalityInput


class TextInput(ModalityInput):
    """Input for new text messages.

    Args:
        from_number: Sender phone number.
        to_number: Recipient phone number.
        body: Message text content.
        media: Optional list of media attachments.
        group_id: Optional group conversation ID.
    """

    pass
