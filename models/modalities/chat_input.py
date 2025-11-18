"""Chat input model."""

from typing import Literal, Optional, Union
from uuid import uuid4

from pydantic import Field, field_validator

from models.base_input import ModalityInput


class ChatInput(ModalityInput):
    """Input for new chat messages.

    Represents a chat message from either the user or the assistant. Supports both
    simple text content and multimodal content for future extensibility.

    Args:
        modality_type: Always "chat" for this input type.
        timestamp: When this message was sent (simulator time).
        input_id: Unique identifier for this input.
        role: Message sender role - "user" or "assistant".
        content: Message content (string for text, or list of content blocks for multimodal).
        message_id: Optional explicit message ID (auto-generated if not provided).
        conversation_id: Optional conversation/thread identifier (default: "default").
        metadata: Optional dictionary for additional data (token count, model info, etc.).
    """

    modality_type: str = Field(default="chat", frozen=True)
    role: Literal["user", "assistant"] = Field(
        description="Message sender role - 'user' or 'assistant'"
    )
    content: Union[str, list[dict]] = Field(
        description="Message content (string for text, or list of content blocks for multimodal)"
    )
    message_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique message identifier (auto-generated if not provided)",
    )
    conversation_id: str = Field(
        default="default",
        description="Conversation/thread identifier for multi-conversation support",
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Optional additional data (token count, model info, etc.)",
    )

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: Union[str, list[dict]]) -> Union[str, list[dict]]:
        """Validate content structure.

        For text content, accepts any non-empty string.
        For multimodal content, validates that each block has a 'type' field.

        Args:
            value: Content to validate.

        Returns:
            The validated content value.

        Raises:
            ValueError: If content is invalid.
        """
        if isinstance(value, str):
            if not value.strip():
                raise ValueError("Text content cannot be empty")
            return value

        if isinstance(value, list):
            if not value:
                raise ValueError("Content list cannot be empty")

            for i, block in enumerate(value):
                if not isinstance(block, dict):
                    raise ValueError(
                        f"Content block {i} must be a dictionary, got {type(block)}"
                    )
                if "type" not in block:
                    raise ValueError(f"Content block {i} missing required 'type' field")

                block_type = block["type"]
                if block_type == "text":
                    if "text" not in block:
                        raise ValueError(
                            f"Text content block {i} missing required 'text' field"
                        )
                elif block_type in ("image", "audio", "video"):
                    if "source" not in block:
                        raise ValueError(
                            f"{block_type.capitalize()} content block {i} missing required 'source' field"
                        )
                    if block["source"] == "url" and "url" not in block:
                        raise ValueError(
                            f"{block_type.capitalize()} content block {i} with source='url' missing 'url' field"
                        )
                    elif block["source"] == "base64" and "data" not in block:
                        raise ValueError(
                            f"{block_type.capitalize()} content block {i} with source='base64' missing 'data' field"
                        )

            return value

        raise ValueError(f"Content must be string or list of dicts, got {type(value)}")

    @field_validator("conversation_id")
    @classmethod
    def validate_conversation_id(cls, value: str) -> str:
        """Validate conversation ID is non-empty.

        Args:
            value: Conversation ID to validate.

        Returns:
            The validated conversation ID.

        Raises:
            ValueError: If conversation ID is empty.
        """
        if not value.strip():
            raise ValueError("Conversation ID cannot be empty")
        return value

    def validate_input(self) -> None:
        """Perform modality-specific validation beyond Pydantic field validation.

        For ChatInput, all validation is handled by Pydantic field validators.
        This method is provided for consistency with the base class interface.

        Raises:
            ValueError: Never raised (all validation in field validators).
        """
        pass

    def get_affected_entities(self) -> list[str]:
        """Return list of entity IDs affected by this input.

        For chat messages, we track the conversation as the affected entity.

        Returns:
            List containing the conversation identifier.
        """
        return [f"conversation:{self.conversation_id}"]

    def get_summary(self) -> str:
        """Return human-readable one-line summary of this input.

        Examples:
            - "User: 'What's the weather today?'"
            - "Assistant: 'It's sunny and 72°F.'"
            - "User: [multimodal message with 2 parts]"

        Returns:
            Brief description of the message for logging/UI display.
        """
        role_display = self.role.capitalize()

        if isinstance(self.content, str):
            preview = self.content
            if len(preview) > 50:
                preview = preview[:47] + "..."
            return f"{role_display}: '{preview}'"
        else:
            text_blocks = [
                block.get("text", "") for block in self.content if block.get("type") == "text"
            ]
            if text_blocks:
                preview = " ".join(text_blocks)
                if len(preview) > 50:
                    preview = preview[:47] + "..."
                return f"{role_display}: '{preview}' [multimodal: {len(self.content)} parts]"
            else:
                return f"{role_display}: [multimodal message with {len(self.content)} parts]"

    def should_merge_with(self, other: "ModalityInput") -> bool:
        """Determine if this input should be merged with another input.

        Chat messages should not be merged as each represents a distinct
        message in the conversation that should be tracked separately.

        Args:
            other: Another input to compare against.

        Returns:
            Always False for chat messages.
        """
        return False
