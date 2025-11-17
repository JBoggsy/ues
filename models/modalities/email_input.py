"""Email input model."""

from models.base_input import ModalityInput


class EmailInput(ModalityInput):
    """Input for new email messages.

    Args:
        from_address: Sender email address.
        to_addresses: List of recipient email addresses.
        cc_addresses: List of CC email addresses.
        bcc_addresses: List of BCC email addresses.
        subject: Email subject line.
        body: Email body content.
        attachments: List of attachment metadata.
        thread_id: Optional thread ID for grouping related emails.
    """

    pass
