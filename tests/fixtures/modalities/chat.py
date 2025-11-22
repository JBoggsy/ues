"""Fixtures for Chat modality."""

from datetime import datetime, timezone

from models.modalities.chat_input import ChatInput
from models.modalities.chat_state import ChatState


def create_chat_input(
    role: str = "user",
    content: str | list[dict] = "Hello, assistant!",
    timestamp: datetime | None = None,
    conversation_id: str = "default",
    **kwargs,
) -> ChatInput:
    """Create a ChatInput with sensible defaults.

    Args:
        role: Message sender role - "user" or "assistant".
        content: Message content (string or multimodal content blocks).
        timestamp: When message was sent (defaults to now).
        conversation_id: Conversation identifier (default: "default").
        **kwargs: Additional fields to override.

    Returns:
        ChatInput instance ready for testing.
    """
    return ChatInput(
        role=role,
        content=content,
        timestamp=timestamp or datetime.now(timezone.utc),
        conversation_id=conversation_id,
        **kwargs,
    )


def create_chat_state(
    last_updated: datetime | None = None,
    **kwargs,
) -> ChatState:
    """Create a ChatState with sensible defaults.

    Args:
        last_updated: When state was last updated (defaults to now).
        **kwargs: Additional fields to override.

    Returns:
        ChatState instance ready for testing.
    """
    return ChatState(
        last_updated=last_updated or datetime.now(timezone.utc),
        **kwargs,
    )


# Pre-built message examples
USER_GREETING = create_chat_input(
    role="user",
    content="Hello! How are you today?",
)

ASSISTANT_RESPONSE = create_chat_input(
    role="assistant",
    content="I'm doing well, thank you for asking! How can I help you today?",
)

USER_QUESTION = create_chat_input(
    role="user",
    content="What's the weather like today?",
)

ASSISTANT_WEATHER_RESPONSE = create_chat_input(
    role="assistant",
    content="Based on current data, it's sunny with a temperature of 72°F.",
)

USER_TASK = create_chat_input(
    role="user",
    content="Can you remind me about my meeting at 2pm?",
)

ASSISTANT_CONFIRMATION = create_chat_input(
    role="assistant",
    content="I've set a reminder for your 2pm meeting.",
)

MULTIMODAL_IMAGE = create_chat_input(
    role="user",
    content=[
        {"type": "text", "text": "What's in this image?"},
        {
            "type": "image",
            "source": "url",
            "url": "https://example.com/image.jpg",
        },
    ],
)

MULTIMODAL_AUDIO = create_chat_input(
    role="user",
    content=[
        {"type": "text", "text": "Transcribe this audio"},
        {
            "type": "audio",
            "source": "url",
            "url": "https://example.com/audio.mp3",
        },
    ],
)

LONG_CONVERSATION_MESSAGE = create_chat_input(
    role="user",
    content="This is a longer message that contains multiple sentences. "
    "It might include questions, statements, and requests. "
    "The assistant should handle this appropriately.",
)


# Multi-conversation examples
WORK_CONVERSATION = create_chat_input(
    role="user",
    content="Review the quarterly report",
    conversation_id="work",
)

PERSONAL_CONVERSATION = create_chat_input(
    role="user",
    content="Plan my weekend trip",
    conversation_id="personal",
)


# State examples
EMPTY_CHAT_STATE = create_chat_state()


# Invalid examples for validation testing
INVALID_CHAT_INPUTS = {
    "empty_content": {
        "role": "user",
        "content": "",
        "timestamp": datetime.now(timezone.utc),
    },
    "empty_content_list": {
        "role": "user",
        "content": [],
        "timestamp": datetime.now(timezone.utc),
    },
    "missing_type_in_block": {
        "role": "user",
        "content": [{"text": "missing type field"}],
        "timestamp": datetime.now(timezone.utc),
    },
    "text_block_missing_text": {
        "role": "user",
        "content": [{"type": "text"}],
        "timestamp": datetime.now(timezone.utc),
    },
}


# JSON fixtures for API testing
CHAT_JSON_EXAMPLES = {
    "simple_user": {
        "modality_type": "chat",
        "timestamp": "2025-01-15T10:30:00Z",
        "role": "user",
        "content": "Hello, assistant!",
        "conversation_id": "default",
    },
    "simple_assistant": {
        "modality_type": "chat",
        "timestamp": "2025-01-15T10:30:05Z",
        "role": "assistant",
        "content": "Hello! How can I help you?",
        "conversation_id": "default",
    },
    "multimodal": {
        "modality_type": "chat",
        "timestamp": "2025-01-15T14:00:00Z",
        "role": "user",
        "content": [
            {"type": "text", "text": "What's in this image?"},
            {"type": "image", "source": "url", "url": "https://example.com/image.jpg"},
        ],
        "conversation_id": "default",
    },
}
