"""Email state model."""

from models.base_state import ModalityState


class EmailState(ModalityState):
    """Current email state.

    Args:
        inbox: List of emails in the inbox.
        sent: List of sent emails.
        drafts: List of draft emails.
        threads: Dictionary mapping thread_id to list of emails in that thread.
    """

    pass
