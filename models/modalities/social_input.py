"""Social media input model."""

from models.base_input import ModalityInput


class SocialMediaInput(ModalityInput):
    """Input for social media events.

    Args:
        platform: Social media platform (twitter, instagram, facebook, etc.).
        content: Content of the post/interaction.
        interaction_type: Type of interaction (post, comment, like, follow, etc.).
        author: Author information.
        target_id: Optional target post/user ID for interactions.
    """

    pass
