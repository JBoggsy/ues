"""Unit tests for ChatInput.

This test suite covers:
1. General ModalityInput behavior (applicable to all modalities)
2. Chat-specific validation and features
"""

from datetime import datetime, timezone

import pytest

from models.modalities.chat_input import ChatInput
from tests.fixtures.modalities.chat import (
    ASSISTANT_RESPONSE,
    MULTIMODAL_AUDIO,
    MULTIMODAL_IMAGE,
    USER_GREETING,
    USER_QUESTION,
    create_chat_input,
)


class TestChatInputInstantiation:
    """Test ChatInput instantiation and basic properties.
    
    GENERAL PATTERN: All ModalityInput subclasses should test instantiation,
    default values, required fields, and proper inheritance from ModalityInput.
    """

    def test_instantiation_with_minimal_fields(self):
        """Test creating ChatInput with only required fields."""
        timestamp = datetime.now(timezone.utc)
        chat_input = ChatInput(
            role="user",
            content="Hello!",
            timestamp=timestamp,
        )
        
        assert chat_input.role == "user"
        assert chat_input.content == "Hello!"
        assert chat_input.timestamp == timestamp
        assert chat_input.modality_type == "chat"
        assert chat_input.input_id is not None
        assert chat_input.conversation_id == "default"
        assert chat_input.metadata == {}

    def test_instantiation_with_all_fields(self):
        """Test creating ChatInput with all optional fields."""
        timestamp = datetime.now(timezone.utc)
        chat_input = ChatInput(
            role="assistant",
            content="How can I help?",
            timestamp=timestamp,
            message_id="msg-123",
            conversation_id="work-chat",
            metadata={"tokens": 10, "model": "gpt-4"},
            input_id="input-456",
        )
        
        assert chat_input.role == "assistant"
        assert chat_input.content == "How can I help?"
        assert chat_input.message_id == "msg-123"
        assert chat_input.conversation_id == "work-chat"
        assert chat_input.metadata["tokens"] == 10
        assert chat_input.input_id == "input-456"

    def test_instantiation_modality_type_is_frozen(self):
        """Test that modality_type cannot be changed after instantiation."""
        chat_input = create_chat_input()
        
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            chat_input.modality_type = "other"

    def test_instantiation_auto_generates_message_id(self):
        """Test that message_id is auto-generated when validate_input() is called."""
        chat_input1 = create_chat_input()
        chat_input2 = create_chat_input()
        
        # validate_input() auto-generates message_id for send_message operation
        chat_input1.validate_input()
        chat_input2.validate_input()
        
        assert chat_input1.message_id is not None
        assert chat_input2.message_id is not None
        assert chat_input1.message_id != chat_input2.message_id


class TestChatInputValidation:
    """Test ChatInput field validation.
    
    CHAT-SPECIFIC: These tests verify role validation, content structure validation
    (text vs multimodal), and conversation ID validation.
    """

    def test_validate_role_user(self):
        """Test that 'user' role is accepted."""
        chat_input = create_chat_input(role="user")
        assert chat_input.role == "user"

    def test_validate_role_assistant(self):
        """Test that 'assistant' role is accepted."""
        chat_input = create_chat_input(role="assistant")
        assert chat_input.role == "assistant"

    def test_validate_role_invalid(self):
        """Test that invalid role is rejected."""
        with pytest.raises(ValueError):
            create_chat_input(role="system")

    def test_validate_text_content_non_empty(self):
        """Test that non-empty text content is accepted."""
        chat_input = create_chat_input(content="Hello, world!")
        assert chat_input.content == "Hello, world!"

    def test_validate_text_content_empty_rejected(self):
        """Test that empty text content is rejected."""
        with pytest.raises(ValueError, match="Text content cannot be empty"):
            create_chat_input(content="")

    def test_validate_text_content_whitespace_only_rejected(self):
        """Test that whitespace-only content is rejected."""
        with pytest.raises(ValueError, match="Text content cannot be empty"):
            create_chat_input(content="   ")

    def test_validate_multimodal_content_list(self):
        """Test that multimodal content as list is accepted."""
        content = [
            {"type": "text", "text": "Hello"},
            {"type": "image", "source": "url", "url": "https://example.com/img.jpg"},
        ]
        chat_input = create_chat_input(content=content)
        assert isinstance(chat_input.content, list)
        assert len(chat_input.content) == 2

    def test_validate_multimodal_empty_list_rejected(self):
        """Test that empty content list is rejected."""
        with pytest.raises(ValueError, match="Content list cannot be empty"):
            create_chat_input(content=[])

    def test_validate_multimodal_block_must_be_dict(self):
        """Test that non-dict content blocks are rejected."""
        with pytest.raises(ValueError, match="Input should be a valid dictionary"):
            create_chat_input(content=["not a dict"])

    def test_validate_multimodal_block_requires_type(self):
        """Test that content blocks must have 'type' field."""
        with pytest.raises(ValueError, match="missing required 'type' field"):
            create_chat_input(content=[{"text": "missing type"}])

    def test_validate_text_block_requires_text_field(self):
        """Test that text blocks must have 'text' field."""
        with pytest.raises(ValueError, match="missing required 'text' field"):
            create_chat_input(content=[{"type": "text"}])

    def test_validate_image_block_requires_source(self):
        """Test that image blocks must have 'source' field."""
        with pytest.raises(ValueError, match="missing required 'source' field"):
            create_chat_input(content=[{"type": "image"}])

    def test_validate_image_url_requires_url_field(self):
        """Test that image blocks with source='url' must have 'url' field."""
        with pytest.raises(ValueError, match="missing 'url' field"):
            create_chat_input(content=[{"type": "image", "source": "url"}])

    def test_validate_image_base64_requires_data_field(self):
        """Test that image blocks with source='base64' must have 'data' field."""
        with pytest.raises(ValueError, match="missing 'data' field"):
            create_chat_input(content=[{"type": "image", "source": "base64"}])

    def test_validate_audio_block_validation(self):
        """Test that audio blocks follow same validation as images."""
        with pytest.raises(ValueError, match="missing 'url' field"):
            create_chat_input(content=[{"type": "audio", "source": "url"}])

    def test_validate_video_block_validation(self):
        """Test that video blocks follow same validation as images."""
        with pytest.raises(ValueError, match="missing 'url' field"):
            create_chat_input(content=[{"type": "video", "source": "url"}])

    def test_validate_conversation_id_non_empty(self):
        """Test that non-empty conversation ID is accepted."""
        chat_input = create_chat_input(conversation_id="work-chat")
        assert chat_input.conversation_id == "work-chat"

    def test_validate_conversation_id_empty_rejected(self):
        """Test that empty conversation ID is rejected."""
        with pytest.raises(ValueError, match="Conversation ID cannot be empty"):
            create_chat_input(conversation_id="")

    def test_validate_conversation_id_whitespace_rejected(self):
        """Test that whitespace-only conversation ID is rejected."""
        with pytest.raises(ValueError, match="Conversation ID cannot be empty"):
            create_chat_input(conversation_id="   ")

    def test_validate_operation_send_message_default(self):
        """Test that default operation is 'send_message'."""
        chat_input = create_chat_input()
        assert chat_input.operation == "send_message"

    def test_validate_operation_send_message_explicit(self):
        """Test that 'send_message' operation is accepted."""
        chat_input = ChatInput(
            operation="send_message",
            role="user",
            content="Hello",
            timestamp=datetime.now(timezone.utc),
        )
        assert chat_input.operation == "send_message"

    def test_validate_operation_delete_message(self):
        """Test that 'delete_message' operation is accepted."""
        chat_input = ChatInput(
            operation="delete_message",
            message_id="msg-123",
            timestamp=datetime.now(timezone.utc),
        )
        assert chat_input.operation == "delete_message"

    def test_validate_operation_clear_conversation(self):
        """Test that 'clear_conversation' operation is accepted."""
        chat_input = ChatInput(
            operation="clear_conversation",
            conversation_id="test",
            timestamp=datetime.now(timezone.utc),
        )
        assert chat_input.operation == "clear_conversation"

    def test_validate_send_message_requires_role(self):
        """Test that send_message operation requires role."""
        chat_input = ChatInput(
            operation="send_message",
            content="Hello",
            timestamp=datetime.now(timezone.utc),
        )
        with pytest.raises(ValueError, match="requires 'role' field"):
            chat_input.validate_input()

    def test_validate_send_message_requires_content(self):
        """Test that send_message operation requires content."""
        chat_input = ChatInput(
            operation="send_message",
            role="user",
            timestamp=datetime.now(timezone.utc),
        )
        with pytest.raises(ValueError, match="requires 'content' field"):
            chat_input.validate_input()

    def test_validate_delete_message_requires_message_id(self):
        """Test that delete_message operation requires message_id."""
        chat_input = ChatInput(
            operation="delete_message",
            timestamp=datetime.now(timezone.utc),
        )
        with pytest.raises(ValueError, match="requires 'message_id' field"):
            chat_input.validate_input()

    def test_validate_clear_conversation_succeeds(self):
        """Test that clear_conversation operation doesn't require extra fields."""
        chat_input = ChatInput(
            operation="clear_conversation",
            conversation_id="test",
            timestamp=datetime.now(timezone.utc),
        )
        # Should not raise
        chat_input.validate_input()


class TestChatInputAbstractMethods:
    """Test implementation of ModalityInput abstract methods.
    
    GENERAL PATTERN: All ModalityInput subclasses must implement validate_input(),
    get_affected_entities(), get_summary(), and should_merge_with().
    """

    def test_validate_input_succeeds(self):
        """Test that validate_input() does not raise errors for valid input."""
        chat_input = create_chat_input()
        chat_input.validate_input()  # Should not raise

    def test_get_affected_entities_returns_conversation(self):
        """Test get_affected_entities() returns conversation identifier."""
        chat_input = create_chat_input(conversation_id="work-chat")
        entities = chat_input.get_affected_entities()
        
        assert "conversation:work-chat" in entities
        assert len(entities) == 1

    def test_get_summary_user_text_message(self):
        """Test get_summary() for user text message."""
        chat_input = create_chat_input(
            role="user",
            content="What's the weather today?",
        )
        summary = chat_input.get_summary()
        
        assert "User:" in summary
        assert "weather" in summary

    def test_get_summary_assistant_text_message(self):
        """Test get_summary() for assistant text message."""
        chat_input = create_chat_input(
            role="assistant",
            content="It's sunny and 72°F.",
        )
        summary = chat_input.get_summary()
        
        assert "Assistant:" in summary
        assert "sunny" in summary

    def test_get_summary_long_message_truncated(self):
        """Test that long messages are truncated in summary."""
        long_content = "A" * 100
        chat_input = create_chat_input(content=long_content)
        summary = chat_input.get_summary()
        
        assert "..." in summary
        assert len(summary) < len(long_content) + 20

    def test_get_summary_multimodal_with_text(self):
        """Test get_summary() for multimodal message with text."""
        chat_input = create_chat_input(
            content=[
                {"type": "text", "text": "Check this image"},
                {"type": "image", "source": "url", "url": "https://example.com/img.jpg"},
            ]
        )
        summary = chat_input.get_summary()
        
        assert "Check this image" in summary
        assert "multimodal" in summary
        assert "2 parts" in summary

    def test_get_summary_multimodal_without_text(self):
        """Test get_summary() for multimodal message without text."""
        chat_input = create_chat_input(
            content=[
                {"type": "image", "source": "url", "url": "https://example.com/img.jpg"},
                {"type": "audio", "source": "url", "url": "https://example.com/audio.mp3"},
            ]
        )
        summary = chat_input.get_summary()
        
        assert "multimodal message" in summary
        assert "2 parts" in summary

    def test_should_merge_with_returns_false(self):
        """Test that chat messages never merge."""
        chat_input1 = create_chat_input(content="Message 1")
        chat_input2 = create_chat_input(content="Message 2")
        
        assert not chat_input1.should_merge_with(chat_input2)

    def test_should_merge_with_different_type(self):
        """Test that chat messages don't merge with other modality types."""
        from models.modalities.location_input import LocationInput
        
        chat_input = create_chat_input()
        location_input = LocationInput(
            latitude=37.7749,
            longitude=-122.4194,
            timestamp=chat_input.timestamp,
        )
        
        assert not chat_input.should_merge_with(location_input)


class TestChatInputSerialization:
    """Test ChatInput serialization and deserialization.
    
    GENERAL PATTERN: All ModalityInput subclasses should be serializable to/from
    JSON via Pydantic's model_dump() and model_validate().
    """

    def test_serialization_to_dict(self):
        """Test serializing ChatInput to dictionary."""
        chat_input = create_chat_input(
            role="user",
            content="Hello!",
            conversation_id="work",
            metadata={"tokens": 5},
        )
        data = chat_input.model_dump()
        
        assert data["role"] == "user"
        assert data["content"] == "Hello!"
        assert data["conversation_id"] == "work"
        assert data["metadata"]["tokens"] == 5
        assert data["modality_type"] == "chat"

    def test_deserialization_from_dict(self):
        """Test deserializing ChatInput from dictionary."""
        timestamp = datetime.now(timezone.utc)
        data = {
            "role": "assistant",
            "content": "How can I help?",
            "timestamp": timestamp,
            "conversation_id": "support",
            "modality_type": "chat",
        }
        
        chat_input = ChatInput.model_validate(data)
        
        assert chat_input.role == "assistant"
        assert chat_input.content == "How can I help?"
        assert chat_input.conversation_id == "support"

    def test_serialization_roundtrip_text(self):
        """Test that serialization and deserialization preserves text data."""
        original = create_chat_input(
            role="user",
            content="Test message",
            conversation_id="test-conv",
            metadata={"key": "value"},
        )
        
        data = original.model_dump()
        restored = ChatInput.model_validate(data)
        
        assert restored.role == original.role
        assert restored.content == original.content
        assert restored.conversation_id == original.conversation_id
        assert restored.metadata == original.metadata

    def test_serialization_roundtrip_multimodal(self):
        """Test that serialization preserves multimodal content."""
        original = create_chat_input(
            content=[
                {"type": "text", "text": "Check this"},
                {"type": "image", "source": "url", "url": "https://example.com/img.jpg"},
            ]
        )
        
        data = original.model_dump()
        restored = ChatInput.model_validate(data)
        
        assert isinstance(restored.content, list)
        assert len(restored.content) == 2
        assert restored.content[0]["type"] == "text"
        assert restored.content[1]["type"] == "image"


class TestChatInputFixtures:
    """Test the pre-built fixture chat inputs.
    
    CHAT-SPECIFIC: Verify that fixture data is correctly structured.
    """

    def test_user_greeting_fixture(self):
        """Test USER_GREETING fixture has expected values."""
        assert USER_GREETING.role == "user"
        assert "Hello" in USER_GREETING.content
        assert isinstance(USER_GREETING.content, str)

    def test_assistant_response_fixture(self):
        """Test ASSISTANT_RESPONSE fixture has expected values."""
        assert ASSISTANT_RESPONSE.role == "assistant"
        assert isinstance(ASSISTANT_RESPONSE.content, str)

    def test_user_question_fixture(self):
        """Test USER_QUESTION fixture has expected values."""
        assert USER_QUESTION.role == "user"
        assert "weather" in USER_QUESTION.content.lower()

    def test_multimodal_image_fixture(self):
        """Test MULTIMODAL_IMAGE fixture has expected structure."""
        assert isinstance(MULTIMODAL_IMAGE.content, list)
        assert len(MULTIMODAL_IMAGE.content) == 2
        assert MULTIMODAL_IMAGE.content[0]["type"] == "text"
        assert MULTIMODAL_IMAGE.content[1]["type"] == "image"

    def test_multimodal_audio_fixture(self):
        """Test MULTIMODAL_AUDIO fixture has expected structure."""
        assert isinstance(MULTIMODAL_AUDIO.content, list)
        has_audio = any(block.get("type") == "audio" for block in MULTIMODAL_AUDIO.content)
        assert has_audio


class TestChatInputEdgeCases:
    """Test edge cases and boundary conditions.
    
    CHAT-SPECIFIC: Test unusual but valid chat configurations.
    """

    def test_very_long_text_message(self):
        """Test that very long text messages are accepted."""
        long_message = "A" * 10000
        chat_input = create_chat_input(content=long_message)
        
        assert len(chat_input.content) == 10000

    def test_multimodal_many_parts(self):
        """Test multimodal content with many parts."""
        content = [
            {"type": "text", "text": f"Part {i}"}
            for i in range(20)
        ]
        chat_input = create_chat_input(content=content)
        
        assert len(chat_input.content) == 20

    def test_metadata_with_nested_structures(self):
        """Test that complex metadata is preserved."""
        metadata = {
            "tokens": 100,
            "model": "gpt-4",
            "settings": {
                "temperature": 0.7,
                "max_tokens": 500,
            },
            "tags": ["important", "work"],
        }
        chat_input = create_chat_input(metadata=metadata)
        
        assert chat_input.metadata["settings"]["temperature"] == 0.7
        assert "important" in chat_input.metadata["tags"]

    def test_unicode_content(self):
        """Test that unicode content is handled correctly."""
        chat_input = create_chat_input(content="Hello 👋 世界 🌍")
        
        assert "👋" in chat_input.content
        assert "世界" in chat_input.content

    def test_special_characters_in_conversation_id(self):
        """Test that conversation IDs can contain special characters."""
        chat_input = create_chat_input(conversation_id="user-123_chat-456")
        
        assert chat_input.conversation_id == "user-123_chat-456"

    def test_mixed_multimodal_content_types(self):
        """Test combining different media types in one message."""
        content = [
            {"type": "text", "text": "Check these:"},
            {"type": "image", "source": "url", "url": "https://example.com/1.jpg"},
            {"type": "text", "text": "and this:"},
            {"type": "audio", "source": "url", "url": "https://example.com/audio.mp3"},
            {"type": "video", "source": "url", "url": "https://example.com/video.mp4"},
        ]
        chat_input = create_chat_input(content=content)
        
        assert len(chat_input.content) == 5
        types = [block["type"] for block in chat_input.content]
        assert "text" in types
        assert "image" in types
        assert "audio" in types
        assert "video" in types
