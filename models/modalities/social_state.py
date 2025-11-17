"""Social media state model."""

from models.base_state import ModalityState


class SocialMediaState(ModalityState):
    """Current social media state.

    Args:
        feeds: Dictionary mapping platform names to feed content.
        posts: Dictionary mapping post IDs to post data.
        follows: Dictionary mapping platform names to list of followed accounts.
        notifications: List of social media notifications.
    """

    pass
