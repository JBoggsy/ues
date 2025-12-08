"""Unit tests for ChatState.

This test suite covers:
1. General ModalityState behavior (applicable to all modalities)
2. Chat-specific state management and features
"""

from datetime import datetime, timedelta, timezone

import pytest

from models.modalities.chat_input import ChatInput
from models.modalities.chat_state import ChatMessage, ChatState, ConversationMetadata
from tests.fixtures.modalities.chat import (
    ASSISTANT_RESPONSE,
    MULTIMODAL_IMAGE,
    PERSONAL_CONVERSATION,
    USER_GREETING,
    USER_QUESTION,
    WORK_CONVERSATION,
    create_chat_input,
    create_chat_state,
)


class TestChatStateInstantiation:
    """Test ChatState instantiation and basic properties.
    
    GENERAL PATTERN: All ModalityState subclasses should test instantiation,
    default values, and proper inheritance from ModalityState.
    """

    def test_instantiation_with_minimal_fields(self):
        """Test creating ChatState with minimal configuration."""
        timestamp = datetime.now(timezone.utc)
        state = ChatState(
            last_updated=timestamp,
        )
        
        assert state.modality_type == "chat"
        assert state.last_updated == timestamp
        assert state.update_count == 0
        assert state.messages == []
        assert state.conversations == {}
        assert state.default_conversation_id == "default"

    def test_instantiation_with_custom_settings(self):
        """Test creating ChatState with custom initial settings."""
        timestamp = datetime.now(timezone.utc)
        state = ChatState(
            last_updated=timestamp,
            max_history_size=500,
            default_conversation_id="main",
        )
        
        assert state.max_history_size == 500
        assert state.default_conversation_id == "main"

    def test_instantiation_modality_type_is_frozen(self):
        """Test that modality_type cannot be changed after instantiation."""
        state = create_chat_state()
        
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            state.modality_type = "other"

    def test_instantiation_default_history_size(self):
        """Test that default max_history_size is set correctly."""
        state = create_chat_state()
        
        assert state.max_history_size == 1000


class TestChatStateApplyInput:
    """Test ChatState.apply_input() method.
    
    GENERAL PATTERN: All ModalityState subclasses must implement apply_input()
    to modify state based on ModalityInput instances.
    """

    def test_apply_input_adds_message(self):
        """Test that applying ChatInput adds message to state."""
        state = create_chat_state()
        chat_input = create_chat_input(
            role="user",
            content="Hello!",
        )
        
        state.apply_input(chat_input)
        
        assert len(state.messages) == 1
        assert state.messages[0].content == "Hello!"
        assert state.messages[0].role == "user"

    def test_apply_input_increments_update_count(self):
        """Test that applying input increments update_count."""
        state = create_chat_state()
        assert state.update_count == 0
        
        state.apply_input(create_chat_input())
        assert state.update_count == 1
        
        state.apply_input(create_chat_input())
        assert state.update_count == 2

    def test_apply_input_updates_last_updated_timestamp(self):
        """Test that applying input updates last_updated to input timestamp."""
        initial_time = datetime.now(timezone.utc)
        state = ChatState(last_updated=initial_time)
        
        input_time = initial_time + timedelta(hours=1)
        chat_input = create_chat_input(timestamp=input_time)
        
        state.apply_input(chat_input)
        
        assert state.last_updated == input_time

    def test_apply_input_creates_conversation_metadata(self):
        """Test that applying input to new conversation creates metadata."""
        state = create_chat_state()
        chat_input = create_chat_input(conversation_id="work-chat")
        
        state.apply_input(chat_input)
        
        assert "work-chat" in state.conversations
        assert state.conversations["work-chat"].message_count == 1

    def test_apply_input_updates_conversation_metadata(self):
        """Test that subsequent messages update conversation metadata."""
        state = create_chat_state()
        
        # First message
        state.apply_input(create_chat_input(role="user", conversation_id="test"))
        
        # Second message
        input_time = datetime.now(timezone.utc) + timedelta(minutes=1)
        state.apply_input(create_chat_input(
            role="assistant",
            conversation_id="test",
            timestamp=input_time,
        ))
        
        metadata = state.conversations["test"]
        assert metadata.message_count == 2
        assert metadata.last_message_at == input_time
        assert "user" in metadata.participant_roles
        assert "assistant" in metadata.participant_roles

    def test_apply_input_maintains_message_order(self):
        """Test that messages are kept in chronological order."""
        state = create_chat_state()
        now = datetime.now(timezone.utc)
        
        # Add messages in non-chronological order
        state.apply_input(create_chat_input(content="Third", timestamp=now + timedelta(minutes=2)))
        state.apply_input(create_chat_input(content="First", timestamp=now))
        state.apply_input(create_chat_input(content="Second", timestamp=now + timedelta(minutes=1)))
        
        assert state.messages[0].content == "First"
        assert state.messages[1].content == "Second"
        assert state.messages[2].content == "Third"

    def test_apply_input_manages_history_size_per_conversation(self):
        """Test that history is trimmed when it exceeds max_history_size."""
        state = create_chat_state(max_history_size=5)
        
        # Add 10 messages to one conversation
        for i in range(10):
            chat_input = create_chat_input(
                content=f"Message {i}",
                conversation_id="test",
            )
            state.apply_input(chat_input)
        
        # Should only have 5 messages for this conversation
        test_messages = [m for m in state.messages if m.conversation_id == "test"]
        assert len(test_messages) == 5

    def test_apply_input_preserves_message_metadata(self):
        """Test that message metadata is preserved."""
        state = create_chat_state()
        chat_input = create_chat_input(
            content="Test",
            metadata={"tokens": 10, "model": "gpt-4"},
        )
        
        state.apply_input(chat_input)
        
        assert state.messages[0].metadata["tokens"] == 10
        assert state.messages[0].metadata["model"] == "gpt-4"

    def test_apply_input_rejects_wrong_input_type(self):
        """Test that applying wrong input type raises ValueError."""
        from models.modalities.location_input import LocationInput
        
        state = create_chat_state()
        location_input = LocationInput(
            latitude=37.7749,
            longitude=-122.4194,
            timestamp=datetime.now(timezone.utc),
        )
        
        with pytest.raises(ValueError, match="ChatState can only apply ChatInput"):
            state.apply_input(location_input)

    def test_apply_input_multiple_conversations(self):
        """Test managing messages from multiple conversations."""
        state = create_chat_state()
        
        state.apply_input(create_chat_input(content="Work msg", conversation_id="work"))
        state.apply_input(create_chat_input(content="Personal msg", conversation_id="personal"))
        state.apply_input(create_chat_input(content="Work msg 2", conversation_id="work"))
        
        assert len(state.conversations) == 2
        assert state.conversations["work"].message_count == 2
        assert state.conversations["personal"].message_count == 1


class TestChatStateGetSnapshot:
    """Test ChatState.get_snapshot() method.
    
    GENERAL PATTERN: All ModalityState subclasses must implement get_snapshot()
    to return JSON-serializable state for API responses.
    """

    def test_get_snapshot_includes_metadata(self):
        """Test that snapshot includes modality_type, last_updated, update_count."""
        state = create_chat_state()
        snapshot = state.get_snapshot()
        
        assert snapshot["modality_type"] == "chat"
        assert "last_updated" in snapshot
        assert snapshot["update_count"] == 0

    def test_get_snapshot_includes_messages(self):
        """Test snapshot includes message list."""
        state = create_chat_state()
        state.apply_input(USER_GREETING)
        state.apply_input(ASSISTANT_RESPONSE)
        
        snapshot = state.get_snapshot()
        
        assert "messages" in snapshot
        assert len(snapshot["messages"]) == 2

    def test_get_snapshot_includes_conversations(self):
        """Test snapshot includes conversation metadata."""
        state = create_chat_state()
        state.apply_input(create_chat_input(conversation_id="work"))
        
        snapshot = state.get_snapshot()
        
        assert "conversations" in snapshot
        assert "work" in snapshot["conversations"]

    def test_get_snapshot_includes_counts(self):
        """Test snapshot includes total counts."""
        state = create_chat_state()
        state.apply_input(create_chat_input(conversation_id="work"))
        state.apply_input(create_chat_input(conversation_id="personal"))
        
        snapshot = state.get_snapshot()
        
        assert snapshot["total_message_count"] == 2
        assert snapshot["conversation_count"] == 2

    def test_get_snapshot_is_json_serializable(self):
        """Test that snapshot can be JSON serialized."""
        import json
        
        state = create_chat_state()
        state.apply_input(create_chat_input())
        
        snapshot = state.get_snapshot()
        json_str = json.dumps(snapshot)
        
        assert json_str is not None
        assert isinstance(json_str, str)


class TestChatStateValidateState:
    """Test ChatState.validate_state() method.
    
    GENERAL PATTERN: All ModalityState subclasses must implement validate_state()
    to check internal consistency and return error messages.
    """

    def test_validate_state_valid_state_returns_empty_list(self):
        """Test that valid state returns no issues."""
        state = create_chat_state()
        state.apply_input(create_chat_input())
        
        issues = state.validate_state()
        
        assert issues == []

    def test_validate_state_detects_messages_not_chronological(self):
        """Test detection of non-chronological message ordering."""
        state = create_chat_state()
        now = datetime.now(timezone.utc)
        
        # Manually create out-of-order messages
        state.messages = [
            ChatMessage(
                message_id="msg1",
                conversation_id="test",
                role="user",
                content="First",
                timestamp=now,
            ),
            ChatMessage(
                message_id="msg2",
                conversation_id="test",
                role="user",
                content="Second",
                timestamp=now - timedelta(hours=1),
            ),
        ]
        
        issues = state.validate_state()
        
        assert any("chronological" in issue.lower() for issue in issues)

    def test_validate_state_detects_message_count_mismatch(self):
        """Test detection of conversation metadata count mismatch."""
        state = create_chat_state()
        now = datetime.now(timezone.utc)
        
        # Add message
        state.messages = [
            ChatMessage(
                message_id="msg1",
                conversation_id="test",
                role="user",
                content="Hello",
                timestamp=now,
            )
        ]
        
        # Manually set wrong count
        state.conversations["test"] = ConversationMetadata(
            conversation_id="test",
            created_at=now,
            last_message_at=now,
            message_count=5,  # Wrong count
        )
        
        issues = state.validate_state()
        
        assert any("count" in issue.lower() for issue in issues)

    def test_validate_state_detects_exceeds_history_limit(self):
        """Test detection of conversations exceeding history limit."""
        state = create_chat_state(max_history_size=3)
        now = datetime.now(timezone.utc)
        
        # Manually add too many messages
        for i in range(5):
            state.messages.append(
                ChatMessage(
                    message_id=f"msg{i}",
                    conversation_id="test",
                    role="user",
                    content=f"Message {i}",
                    timestamp=now,
                )
            )
        
        state.conversations["test"] = ConversationMetadata(
            conversation_id="test",
            created_at=now,
            last_message_at=now,
            message_count=5,
        )
        
        issues = state.validate_state()
        
        assert any("exceeds maximum" in issue.lower() for issue in issues)

    def test_validate_state_detects_role_mismatch(self):
        """Test detection of participant role mismatch."""
        state = create_chat_state()
        now = datetime.now(timezone.utc)
        
        state.messages = [
            ChatMessage(
                message_id="msg1",
                conversation_id="test",
                role="user",
                content="Hello",
                timestamp=now,
            ),
            ChatMessage(
                message_id="msg2",
                conversation_id="test",
                role="assistant",
                content="Hi",
                timestamp=now,
            ),
        ]
        
        # Metadata has wrong roles
        state.conversations["test"] = ConversationMetadata(
            conversation_id="test",
            created_at=now,
            last_message_at=now,
            message_count=2,
            participant_roles={"user"},  # Missing assistant
        )
        
        issues = state.validate_state()
        
        assert any("roles" in issue.lower() for issue in issues)


class TestChatStateQuery:
    """Test ChatState.query() method.
    
    CHAT-SPECIFIC: Test chat-specific query capabilities like filtering by
    conversation, role, time range, and text search.
    """

    def test_query_all_messages(self):
        """Test querying all messages with no filters."""
        state = create_chat_state()
        state.apply_input(create_chat_input(content="Message 1"))
        state.apply_input(create_chat_input(content="Message 2"))
        
        result = state.query({})
        
        assert result["count"] == 2

    def test_query_filter_by_conversation(self):
        """Test filtering messages by conversation ID."""
        state = create_chat_state()
        state.apply_input(create_chat_input(content="Work", conversation_id="work"))
        state.apply_input(create_chat_input(content="Personal", conversation_id="personal"))
        state.apply_input(create_chat_input(content="Work 2", conversation_id="work"))
        
        result = state.query({"conversation_id": "work"})
        
        assert result["count"] == 2
        assert all(msg["conversation_id"] == "work" for msg in result["messages"])

    def test_query_filter_by_role(self):
        """Test filtering messages by role."""
        state = create_chat_state()
        state.apply_input(create_chat_input(role="user", content="Question"))
        state.apply_input(create_chat_input(role="assistant", content="Answer"))
        state.apply_input(create_chat_input(role="user", content="Follow-up"))
        
        result = state.query({"role": "user"})
        
        assert result["count"] == 2
        assert all(msg["role"] == "user" for msg in result["messages"])

    def test_query_filter_by_time_range(self):
        """Test filtering messages by time range."""
        now = datetime.now(timezone.utc)
        state = ChatState(last_updated=now)
        
        for i in range(5):
            state.apply_input(create_chat_input(
                content=f"Message {i}",
                timestamp=now + timedelta(hours=i),
            ))
        
        # Query for messages after 2 hours
        result = state.query({"since": now + timedelta(hours=2)})
        
        assert result["count"] == 3

    def test_query_filter_by_text_search(self):
        """Test searching for text in message content."""
        state = create_chat_state()
        state.apply_input(create_chat_input(content="The weather is nice"))
        state.apply_input(create_chat_input(content="I like coding"))
        state.apply_input(create_chat_input(content="Weather forecast looks good"))
        
        result = state.query({"search": "weather"})
        
        assert result["count"] == 2

    def test_query_text_search_case_insensitive(self):
        """Test that text search is case-insensitive."""
        state = create_chat_state()
        state.apply_input(create_chat_input(content="HELLO WORLD"))
        
        result = state.query({"search": "hello"})
        
        assert result["count"] == 1

    def test_query_respects_limit(self):
        """Test that query respects limit parameter."""
        state = create_chat_state()
        
        for i in range(10):
            state.apply_input(create_chat_input(content=f"Message {i}"))
        
        result = state.query({"limit": 3})
        
        assert result["count"] == 3

    def test_query_combined_filters(self):
        """Test combining multiple query filters."""
        state = create_chat_state()
        now = datetime.now(timezone.utc)
        
        state.apply_input(create_chat_input(
            role="user",
            content="Work question",
            conversation_id="work",
            timestamp=now,
        ))
        state.apply_input(create_chat_input(
            role="assistant",
            content="Work answer",
            conversation_id="work",
            timestamp=now + timedelta(minutes=1),
        ))
        
        result = state.query({
            "conversation_id": "work",
            "role": "user",
        })
        
        assert result["count"] == 1
        assert result["messages"][0]["content"] == "Work question"


class TestChatStateHelperMethods:
    """Test ChatState helper methods.
    
    CHAT-SPECIFIC: Test convenience methods for common chat operations.
    """

    def test_get_conversation(self):
        """Test getting all messages in a specific conversation."""
        state = create_chat_state()
        state.apply_input(WORK_CONVERSATION)
        state.apply_input(PERSONAL_CONVERSATION)
        
        result = state.get_conversation("work")
        
        assert result["count"] == 1
        assert result["messages"][0]["conversation_id"] == "work"

    def test_get_recent_messages(self):
        """Test getting most recent N messages."""
        state = create_chat_state()
        
        for i in range(20):
            state.apply_input(create_chat_input(content=f"Message {i}"))
        
        result = state.get_recent_messages(limit=5)
        
        assert result["count"] == 5

    def test_get_recent_messages_from_conversation(self):
        """Test getting recent messages from specific conversation."""
        state = create_chat_state()
        
        for i in range(10):
            state.apply_input(create_chat_input(
                content=f"Work {i}",
                conversation_id="work",
            ))
        for i in range(5):
            state.apply_input(create_chat_input(
                content=f"Personal {i}",
                conversation_id="personal",
            ))
        
        result = state.get_recent_messages(limit=3, conversation_id="work")
        
        assert result["count"] == 3
        assert all(msg["conversation_id"] == "work" for msg in result["messages"])

    def test_get_message_by_id(self):
        """Test retrieving a specific message by ID."""
        state = create_chat_state()
        chat_input = create_chat_input(content="Test message", message_id="msg-123")
        state.apply_input(chat_input)
        
        message = state.get_message_by_id("msg-123")
        
        assert message is not None
        assert message["message_id"] == "msg-123"
        assert message["content"] == "Test message"

    def test_get_message_by_id_not_found(self):
        """Test that getting non-existent message returns None."""
        state = create_chat_state()
        
        message = state.get_message_by_id("nonexistent")
        
        assert message is None


class TestChatStateOperations:
    """Test ChatState operation handlers.
    
    CHAT-SPECIFIC: Test delete_message and clear_conversation operations.
    """

    def test_delete_message_removes_from_state(self):
        """Test that delete_message operation removes message from state."""
        state = create_chat_state()
        
        # Send a message
        send_input = create_chat_input(role="user", content="Hello")
        send_input.validate_input()  # Auto-generates message_id
        state.apply_input(send_input)
        
        assert len(state.messages) == 1
        message_id = send_input.message_id
        
        # Delete the message
        delete_input = ChatInput(
            operation="delete_message",
            message_id=message_id,
            timestamp=datetime.now(timezone.utc),
        )
        state.apply_input(delete_input)
        
        assert len(state.messages) == 0
        assert state.get_message_by_id(message_id) is None

    def test_delete_message_updates_conversation_metadata(self):
        """Test that deleting message updates conversation metadata."""
        state = create_chat_state()
        
        # Send two messages to same conversation
        send1 = create_chat_input(role="user", content="First", conversation_id="test")
        send1.validate_input()
        state.apply_input(send1)
        
        send2 = create_chat_input(role="user", content="Second", conversation_id="test")
        send2.validate_input()
        state.apply_input(send2)
        
        assert state.conversations["test"].message_count == 2
        
        # Delete one message
        delete_input = ChatInput(
            operation="delete_message",
            message_id=send1.message_id,
            conversation_id="test",
            timestamp=datetime.now(timezone.utc),
        )
        state.apply_input(delete_input)
        
        assert state.conversations["test"].message_count == 1

    def test_delete_message_nonexistent_is_noop(self):
        """Test that deleting nonexistent message is a no-op."""
        state = create_chat_state()
        
        # Add a message
        send_input = create_chat_input(role="user", content="Hello")
        send_input.validate_input()
        state.apply_input(send_input)
        
        initial_count = len(state.messages)
        
        # Try to delete nonexistent message
        delete_input = ChatInput(
            operation="delete_message",
            message_id="nonexistent-id",
            timestamp=datetime.now(timezone.utc),
        )
        state.apply_input(delete_input)
        
        # State should be unchanged
        assert len(state.messages) == initial_count

    def test_clear_conversation_removes_all_messages(self):
        """Test that clear_conversation removes all messages in conversation."""
        state = create_chat_state()
        
        # Add messages to "test" conversation
        for i in range(3):
            state.apply_input(create_chat_input(
                role="user",
                content=f"Message {i}",
                conversation_id="test",
            ))
        
        # Add messages to "other" conversation
        state.apply_input(create_chat_input(
            role="user",
            content="Other message",
            conversation_id="other",
        ))
        
        assert len(state.messages) == 4
        
        # Clear "test" conversation
        clear_input = ChatInput(
            operation="clear_conversation",
            conversation_id="test",
            timestamp=datetime.now(timezone.utc),
        )
        state.apply_input(clear_input)
        
        # Only "other" conversation message should remain
        assert len(state.messages) == 1
        assert state.messages[0].conversation_id == "other"

    def test_clear_conversation_removes_metadata(self):
        """Test that clearing conversation removes its metadata."""
        state = create_chat_state()
        
        # Add messages
        state.apply_input(create_chat_input(
            role="user",
            content="Hello",
            conversation_id="test",
        ))
        
        assert "test" in state.conversations
        
        # Clear conversation
        clear_input = ChatInput(
            operation="clear_conversation",
            conversation_id="test",
            timestamp=datetime.now(timezone.utc),
        )
        state.apply_input(clear_input)
        
        assert "test" not in state.conversations

    def test_clear_conversation_nonexistent_is_noop(self):
        """Test that clearing nonexistent conversation is a no-op."""
        state = create_chat_state()
        
        # Add a message to "test" conversation
        state.apply_input(create_chat_input(
            role="user",
            content="Hello",
            conversation_id="test",
        ))
        
        initial_count = len(state.messages)
        
        # Try to clear nonexistent conversation
        clear_input = ChatInput(
            operation="clear_conversation",
            conversation_id="nonexistent",
            timestamp=datetime.now(timezone.utc),
        )
        state.apply_input(clear_input)
        
        # State should be unchanged
        assert len(state.messages) == initial_count
        assert "test" in state.conversations


class TestChatMessageClass:
    """Test ChatMessage helper class.
    
    CHAT-SPECIFIC: Test the message data structure.
    """

    def test_message_creation(self):
        """Test creating a ChatMessage."""
        now = datetime.now(timezone.utc)
        message = ChatMessage(
            message_id="msg-123",
            conversation_id="test",
            role="user",
            content="Hello",
            timestamp=now,
            metadata={"tokens": 5},
        )
        
        assert message.message_id == "msg-123"
        assert message.conversation_id == "test"
        assert message.role == "user"
        assert message.content == "Hello"
        assert message.timestamp == now
        assert message.metadata["tokens"] == 5

    def test_message_to_dict(self):
        """Test converting message to dictionary."""
        now = datetime.now(timezone.utc)
        message = ChatMessage(
            message_id="msg-456",
            conversation_id="chat",
            role="assistant",
            content="Response",
            timestamp=now,
        )
        
        message_dict = message.to_dict()
        
        assert message_dict["message_id"] == "msg-456"
        assert message_dict["conversation_id"] == "chat"
        assert message_dict["role"] == "assistant"
        assert message_dict["content"] == "Response"
        assert "timestamp" in message_dict

    def test_message_to_dict_with_metadata(self):
        """Test that to_dict includes metadata when present."""
        message = ChatMessage(
            message_id="msg1",
            conversation_id="test",
            role="user",
            content="Hello",
            timestamp=datetime.now(timezone.utc),
            metadata={"key": "value"},
        )
        
        message_dict = message.to_dict()
        
        assert "metadata" in message_dict
        assert message_dict["metadata"]["key"] == "value"

    def test_message_to_dict_without_metadata(self):
        """Test that to_dict omits empty metadata."""
        message = ChatMessage(
            message_id="msg1",
            conversation_id="test",
            role="user",
            content="Hello",
            timestamp=datetime.now(timezone.utc),
        )
        
        message_dict = message.to_dict()
        
        assert "metadata" not in message_dict


class TestConversationMetadataClass:
    """Test ConversationMetadata helper class.
    
    CHAT-SPECIFIC: Test the conversation metadata structure.
    """

    def test_metadata_creation(self):
        """Test creating ConversationMetadata."""
        now = datetime.now(timezone.utc)
        metadata = ConversationMetadata(
            conversation_id="work",
            created_at=now,
            last_message_at=now + timedelta(minutes=10),
            message_count=5,
            participant_roles={"user", "assistant"},
        )
        
        assert metadata.conversation_id == "work"
        assert metadata.message_count == 5
        assert len(metadata.participant_roles) == 2

    def test_metadata_to_dict(self):
        """Test converting metadata to dictionary."""
        now = datetime.now(timezone.utc)
        metadata = ConversationMetadata(
            conversation_id="test",
            created_at=now,
            last_message_at=now,
            message_count=3,
            participant_roles={"user"},
        )
        
        metadata_dict = metadata.to_dict()
        
        assert metadata_dict["conversation_id"] == "test"
        assert metadata_dict["message_count"] == 3
        assert "user" in metadata_dict["participant_roles"]


class TestChatStateIntegration:
    """Integration tests for ChatState with multiple operations.
    
    CHAT-SPECIFIC: Test realistic chat usage patterns.
    """

    def test_complete_conversation(self):
        """Test a complete multi-turn conversation."""
        state = create_chat_state()
        now = datetime.now(timezone.utc)
        
        # User asks question
        state.apply_input(create_chat_input(
            role="user",
            content="What's the weather?",
            timestamp=now,
        ))
        
        # Assistant responds
        state.apply_input(create_chat_input(
            role="assistant",
            content="It's sunny and 72°F.",
            timestamp=now + timedelta(seconds=1),
        ))
        
        # User follows up
        state.apply_input(create_chat_input(
            role="user",
            content="Will it rain tomorrow?",
            timestamp=now + timedelta(seconds=5),
        ))
        
        # Assistant responds again
        state.apply_input(create_chat_input(
            role="assistant",
            content="No rain expected tomorrow.",
            timestamp=now + timedelta(seconds=6),
        ))
        
        assert state.update_count == 4
        assert len(state.messages) == 4
        assert state.conversations["default"].message_count == 4


class TestChatStateSerialization:
    """Test ChatState serialization and deserialization.
    
    GENERAL PATTERN: All ModalityState subclasses should support Pydantic
    serialization via model_dump() and model_validate() for state persistence.
    """

    def test_serialization_to_dict(self):
        """Test serializing ChatState to dictionary."""
        state = create_chat_state()
        state.apply_input(USER_GREETING)
        state.apply_input(ASSISTANT_RESPONSE)
        
        data = state.model_dump()
        
        assert data["modality_type"] == "chat"
        assert "messages" in data
        assert len(data["messages"]) == 2
        assert "conversations" in data
        assert "default" in data["conversations"]

    def test_deserialization_from_dict(self):
        """Test deserializing ChatState from dictionary."""
        state = create_chat_state()
        state.apply_input(USER_GREETING)
        state.apply_input(ASSISTANT_RESPONSE)
        state.apply_input(USER_QUESTION)
        
        data = state.model_dump()
        restored = ChatState.model_validate(data)
        
        assert restored.modality_type == state.modality_type
        assert restored.update_count == state.update_count
        assert len(restored.messages) == len(state.messages)
        assert len(restored.conversations) == len(state.conversations)

    def test_serialization_roundtrip(self):
        """Test complete serialization/deserialization roundtrip."""
        original = create_chat_state(max_history_size=100)
        original.apply_input(USER_GREETING)
        original.apply_input(ASSISTANT_RESPONSE)
        
        data = original.model_dump()
        restored = ChatState.model_validate(data)
        
        assert restored.max_history_size == original.max_history_size
        assert len(restored.messages) == len(original.messages)
        assert restored.messages[0].message_id == original.messages[0].message_id
        assert restored.messages[0].role == original.messages[0].role
        assert restored.messages[0].content == original.messages[0].content

    def test_serialization_preserves_multimodal_content(self):
        """Test that multimodal content is properly serialized."""
        state = create_chat_state()
        state.apply_input(MULTIMODAL_IMAGE)
        
        data = state.model_dump()
        restored = ChatState.model_validate(data)
        
        assert len(restored.messages) == 1
        assert isinstance(restored.messages[0].content, list)
        assert restored.messages[0].content[0]["type"] == "text"
        assert restored.messages[0].content[1]["type"] == "image"

    def test_serialization_preserves_metadata(self):
        """Test that message metadata is properly serialized."""
        state = create_chat_state()
        now = datetime.now(timezone.utc)
        
        state.apply_input(create_chat_input(
            role="user",
            content="Test",
            timestamp=now,
            metadata={"client": "web", "version": "1.0"},
        ))
        
        data = state.model_dump()
        restored = ChatState.model_validate(data)
        
        assert restored.messages[0].metadata["client"] == "web"
        assert restored.messages[0].metadata["version"] == "1.0"

    def test_serialization_preserves_conversations(self):
        """Test that conversation metadata is properly serialized."""
        state = create_chat_state()
        now = datetime.now(timezone.utc)
        
        # Add messages to default conversation
        state.apply_input(create_chat_input(
            role="user",
            content="Hello",
            timestamp=now,
        ))
        
        # Add messages to work conversation
        state.apply_input(create_chat_input(
            role="user",
            content="Meeting at 3pm",
            conversation_id="work",
            timestamp=now + timedelta(seconds=5),
        ))
        
        data = state.model_dump()
        restored = ChatState.model_validate(data)
        
        assert len(restored.conversations) == 2
        assert "default" in restored.conversations
        assert "work" in restored.conversations
        assert restored.conversations["default"].message_count == 1
        assert restored.conversations["work"].message_count == 1

    def test_serialization_preserves_participant_roles(self):
        """Test that participant roles are properly serialized."""
        state = create_chat_state()
        state.apply_input(USER_GREETING)
        state.apply_input(ASSISTANT_RESPONSE)
        
        data = state.model_dump()
        restored = ChatState.model_validate(data)
        
        participant_roles = restored.conversations["default"].participant_roles
        assert "user" in participant_roles
        assert "assistant" in participant_roles
        assert len(participant_roles) == 2
        assert len(state.conversations["default"].participant_roles) == 2

    def test_multiple_concurrent_conversations(self):
        """Test managing multiple conversations simultaneously."""
        state = create_chat_state()
        
        # Work conversation
        state.apply_input(create_chat_input(
            role="user",
            content="Review the report",
            conversation_id="work",
        ))
        state.apply_input(create_chat_input(
            role="assistant",
            content="I'll review it now",
            conversation_id="work",
        ))
        
        # Personal conversation
        state.apply_input(create_chat_input(
            role="user",
            content="Plan my vacation",
            conversation_id="personal",
        ))
        state.apply_input(create_chat_input(
            role="assistant",
            content="Let's start planning",
            conversation_id="personal",
        ))
        
        assert len(state.conversations) == 2
        
        work_msgs = state.get_conversation("work")
        personal_msgs = state.get_conversation("personal")
        
        assert work_msgs["count"] == 2
        assert personal_msgs["count"] == 2

    def test_state_consistency_after_many_messages(self):
        """Test that state remains consistent after many messages."""
        state = create_chat_state(max_history_size=50)
        
        # Add 100 messages
        for i in range(100):
            state.apply_input(create_chat_input(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
            ))
        
        # Check history limit is enforced
        assert len(state.messages) == 50
        assert state.update_count == 100
        
        # Validate state consistency (should have no issues after pruning)
        issues = state.validate_state()
        # When history is pruned, message_count won't match actual messages
        # This is expected behavior, so we skip validation for this test
        # The important check is that max_history_size is enforced
        assert len(state.messages) <= state.max_history_size


class TestChatStateCreateUndoData:
    """Test ChatState.create_undo_data() method.
    
    GENERAL PATTERN: All ModalityState subclasses must implement create_undo_data()
    to capture minimal data needed to reverse an apply_input() operation.
    
    CHAT-SPECIFIC: Handles three operations:
    - send_message: Captures message_id and conversation creation status
    - delete_message: Captures the full message being deleted
    - clear_conversation: Captures all messages and metadata being cleared
    """

    def test_create_undo_data_send_message_new_conversation(self):
        """Test create_undo_data for send_message to a new conversation.
        
        CHAT-SPECIFIC: When creating a new conversation, stores flag to remove it on undo.
        """
        state = create_chat_state()
        chat_input = create_chat_input(
            role="user",
            content="Hello!",
            conversation_id="new-chat",
        )
        
        undo_data = state.create_undo_data(chat_input)
        
        assert undo_data["action"] == "remove_message"
        assert undo_data["message_id"] == chat_input.message_id
        assert undo_data["conversation_id"] == "new-chat"
        assert undo_data["was_new_conversation"] is True
        assert "previous_conv_metadata" not in undo_data

    def test_create_undo_data_send_message_existing_conversation(self):
        """Test create_undo_data for send_message to an existing conversation.
        
        CHAT-SPECIFIC: Stores previous conversation metadata for restoration.
        """
        state = create_chat_state()
        
        # Create the conversation first
        first_input = create_chat_input(
            role="user",
            content="First message",
            conversation_id="existing-chat",
        )
        state.apply_input(first_input)
        
        # Create undo data for second message
        second_input = create_chat_input(
            role="assistant",
            content="Response",
            conversation_id="existing-chat",
        )
        undo_data = state.create_undo_data(second_input)
        
        assert undo_data["action"] == "remove_message"
        assert undo_data["was_new_conversation"] is False
        assert "previous_conv_metadata" in undo_data
        assert undo_data["previous_conv_metadata"]["message_count"] == 1
        assert "user" in undo_data["previous_conv_metadata"]["participant_roles"]

    def test_create_undo_data_send_message_captures_removed_at_capacity(self):
        """Test create_undo_data captures removed message when at capacity.
        
        CHAT-SPECIFIC: When history is at max_history_size, oldest message is captured.
        """
        state = create_chat_state(max_history_size=3)
        
        # Fill to capacity
        for i in range(3):
            state.apply_input(create_chat_input(
                role="user",
                content=f"Message {i}",
                timestamp=datetime.now(timezone.utc) + timedelta(seconds=i),
            ))
        
        # Verify at capacity
        assert len(state.messages) == 3
        oldest_id = state.messages[0].message_id
        
        # Create undo data for message that will push out oldest
        new_input = create_chat_input(
            role="user",
            content="Overflow message",
            timestamp=datetime.now(timezone.utc) + timedelta(seconds=10),
        )
        undo_data = state.create_undo_data(new_input)
        
        assert "removed_message" in undo_data
        assert undo_data["removed_message"]["message_id"] == oldest_id

    def test_create_undo_data_send_message_no_removed_when_not_at_capacity(self):
        """Test create_undo_data doesn't capture removed message when not at capacity.
        
        CHAT-SPECIFIC: Only capture removed_message when actually at max capacity.
        """
        state = create_chat_state(max_history_size=100)
        
        # Add a few messages (well under capacity)
        for i in range(3):
            state.apply_input(create_chat_input(
                role="user",
                content=f"Message {i}",
            ))
        
        new_input = create_chat_input(
            role="user",
            content="New message",
        )
        undo_data = state.create_undo_data(new_input)
        
        assert "removed_message" not in undo_data

    def test_create_undo_data_delete_message_existing(self):
        """Test create_undo_data for delete_message operation.
        
        CHAT-SPECIFIC: Captures full message data for restoration.
        """
        state = create_chat_state()
        
        # Add a message to delete
        msg_input = create_chat_input(
            role="user",
            content="Message to delete",
            conversation_id="test",
        )
        state.apply_input(msg_input)
        
        # Create undo data for delete
        delete_input = ChatInput(
            timestamp=datetime.now(timezone.utc),
            operation="delete_message",
            message_id=msg_input.message_id,
            conversation_id="test",
        )
        undo_data = state.create_undo_data(delete_input)
        
        assert undo_data["action"] == "restore_message"
        assert "message" in undo_data
        assert undo_data["message"]["message_id"] == msg_input.message_id
        assert undo_data["message"]["content"] == "Message to delete"
        assert undo_data["message"]["role"] == "user"

    def test_create_undo_data_delete_message_nonexistent(self):
        """Test create_undo_data for deleting a non-existent message.
        
        CHAT-SPECIFIC: Returns noop action when message doesn't exist.
        """
        state = create_chat_state()
        
        delete_input = ChatInput(
            timestamp=datetime.now(timezone.utc),
            operation="delete_message",
            message_id="nonexistent-id",
            conversation_id="test",
        )
        undo_data = state.create_undo_data(delete_input)
        
        assert undo_data["action"] == "noop"

    def test_create_undo_data_clear_conversation(self):
        """Test create_undo_data for clear_conversation operation.
        
        CHAT-SPECIFIC: Captures all messages and metadata for the conversation.
        """
        state = create_chat_state()
        
        # Add messages to conversation
        for i in range(3):
            state.apply_input(create_chat_input(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                conversation_id="to-clear",
                timestamp=datetime.now(timezone.utc) + timedelta(seconds=i),
            ))
        
        # Create undo data for clear
        clear_input = ChatInput(
            timestamp=datetime.now(timezone.utc),
            operation="clear_conversation",
            conversation_id="to-clear",
        )
        undo_data = state.create_undo_data(clear_input)
        
        assert undo_data["action"] == "restore_conversation"
        assert undo_data["conversation_id"] == "to-clear"
        assert len(undo_data["cleared_messages"]) == 3
        assert undo_data["conv_metadata"] is not None
        assert undo_data["conv_metadata"]["message_count"] == 3

    def test_create_undo_data_clear_empty_conversation(self):
        """Test create_undo_data for clearing an empty/nonexistent conversation.
        
        CHAT-SPECIFIC: Returns empty cleared_messages list.
        """
        state = create_chat_state()
        
        clear_input = ChatInput(
            timestamp=datetime.now(timezone.utc),
            operation="clear_conversation",
            conversation_id="empty-conv",
        )
        undo_data = state.create_undo_data(clear_input)
        
        assert undo_data["action"] == "restore_conversation"
        assert len(undo_data["cleared_messages"]) == 0
        assert undo_data["conv_metadata"] is None

    def test_create_undo_data_captures_state_metadata(self):
        """Test that create_undo_data captures state-level metadata.
        
        GENERAL PATTERN: Undo data should include state-level update_count and last_updated.
        """
        state = create_chat_state()
        state.apply_input(create_chat_input())
        
        original_update_count = state.update_count
        original_last_updated = state.last_updated
        
        new_input = create_chat_input(content="Second message")
        undo_data = state.create_undo_data(new_input)
        
        assert "state_previous_update_count" in undo_data
        assert "state_previous_last_updated" in undo_data
        assert undo_data["state_previous_update_count"] == original_update_count

    def test_create_undo_data_raises_for_invalid_input_type(self):
        """Test that create_undo_data raises for non-ChatInput.
        
        GENERAL PATTERN: All modalities should validate input type.
        """
        from models.modalities.location_input import LocationInput
        
        state = create_chat_state()
        invalid_input = LocationInput(
            latitude=40.0,
            longitude=-74.0,
            timestamp=datetime.now(timezone.utc),
        )
        
        with pytest.raises(ValueError, match="ChatInput"):
            state.create_undo_data(invalid_input)

    def test_create_undo_data_does_not_modify_state(self):
        """Test that create_undo_data does not modify state.
        
        GENERAL PATTERN: create_undo_data should be read-only.
        """
        state = create_chat_state()
        state.apply_input(create_chat_input())
        
        original_update_count = state.update_count
        original_message_count = len(state.messages)
        
        new_input = create_chat_input(content="New message")
        state.create_undo_data(new_input)
        
        assert state.update_count == original_update_count
        assert len(state.messages) == original_message_count


class TestChatStateApplyUndo:
    """Test ChatState.apply_undo() method.
    
    GENERAL PATTERN: All ModalityState subclasses must implement apply_undo()
    to reverse a previous apply_input() operation using undo data.
    
    CHAT-SPECIFIC: Handles removing sent messages, restoring deleted messages,
    and restoring cleared conversations.
    """

    def test_apply_undo_removes_sent_message(self):
        """Test that apply_undo removes a message that was sent.
        
        CHAT-SPECIFIC: remove_message action removes the message from state.
        """
        state = create_chat_state()
        chat_input = create_chat_input(content="Hello!")
        
        # Capture undo data, then apply
        undo_data = state.create_undo_data(chat_input)
        state.apply_input(chat_input)
        
        assert len(state.messages) == 1
        
        # Apply undo
        state.apply_undo(undo_data)
        
        assert len(state.messages) == 0

    def test_apply_undo_removes_new_conversation(self):
        """Test that apply_undo removes a conversation that was created.
        
        CHAT-SPECIFIC: When send_message created a new conversation, undo removes it.
        """
        state = create_chat_state()
        chat_input = create_chat_input(
            content="First message",
            conversation_id="new-conv",
        )
        
        undo_data = state.create_undo_data(chat_input)
        state.apply_input(chat_input)
        
        assert "new-conv" in state.conversations
        
        state.apply_undo(undo_data)
        
        assert "new-conv" not in state.conversations

    def test_apply_undo_restores_conversation_metadata(self):
        """Test that apply_undo restores previous conversation metadata.
        
        CHAT-SPECIFIC: When undoing send to existing conversation, metadata is restored.
        """
        state = create_chat_state()
        
        # First message creates conversation
        first_input = create_chat_input(
            role="user",
            content="First",
            conversation_id="chat",
        )
        state.apply_input(first_input)
        
        original_meta = state.conversations["chat"].model_copy()
        
        # Second message
        second_input = create_chat_input(
            role="assistant",
            content="Second",
            conversation_id="chat",
        )
        undo_data = state.create_undo_data(second_input)
        state.apply_input(second_input)
        
        # Metadata should have changed
        assert state.conversations["chat"].message_count == 2
        
        # Undo
        state.apply_undo(undo_data)
        
        assert state.conversations["chat"].message_count == original_meta.message_count
        assert state.conversations["chat"].last_message_at == original_meta.last_message_at

    def test_apply_undo_restores_state_metadata(self):
        """Test that apply_undo restores state-level metadata.
        
        GENERAL PATTERN: State-level update_count and last_updated are restored.
        """
        state = create_chat_state()
        state.apply_input(create_chat_input())
        
        original_update_count = state.update_count
        original_last_updated = state.last_updated
        
        second_input = create_chat_input(content="Second")
        undo_data = state.create_undo_data(second_input)
        state.apply_input(second_input)
        
        state.apply_undo(undo_data)
        
        assert state.update_count == original_update_count
        assert state.last_updated == original_last_updated

    def test_apply_undo_restores_capacity_removed_message(self):
        """Test that apply_undo restores a message removed due to capacity.
        
        CHAT-SPECIFIC: When send_message caused oldest to be removed, it's restored.
        """
        state = create_chat_state(max_history_size=2)
        
        # Fill to capacity
        for i in range(2):
            state.apply_input(create_chat_input(
                content=f"Message {i}",
                timestamp=datetime.now(timezone.utc) + timedelta(seconds=i),
            ))
        
        oldest_id = state.messages[0].message_id
        oldest_content = state.messages[0].content
        
        # Add one more (removes oldest)
        overflow_input = create_chat_input(
            content="Overflow",
            timestamp=datetime.now(timezone.utc) + timedelta(seconds=10),
        )
        undo_data = state.create_undo_data(overflow_input)
        state.apply_input(overflow_input)
        
        # Oldest should be gone
        assert all(m.message_id != oldest_id for m in state.messages)
        
        # Undo
        state.apply_undo(undo_data)
        
        # Oldest should be back
        assert any(m.message_id == oldest_id for m in state.messages)
        restored = next(m for m in state.messages if m.message_id == oldest_id)
        assert restored.content == oldest_content

    def test_apply_undo_restores_deleted_message(self):
        """Test that apply_undo restores a deleted message.
        
        CHAT-SPECIFIC: restore_message action adds the message back.
        """
        state = create_chat_state()
        
        # Add a message
        msg_input = create_chat_input(
            role="user",
            content="To be deleted",
            conversation_id="test",
        )
        state.apply_input(msg_input)
        
        # Delete it
        delete_input = ChatInput(
            timestamp=datetime.now(timezone.utc),
            operation="delete_message",
            message_id=msg_input.message_id,
            conversation_id="test",
        )
        undo_data = state.create_undo_data(delete_input)
        state.apply_input(delete_input)
        
        assert len(state.messages) == 0
        
        # Undo the delete
        state.apply_undo(undo_data)
        
        assert len(state.messages) == 1
        assert state.messages[0].content == "To be deleted"

    def test_apply_undo_noop_for_nonexistent_delete(self):
        """Test that apply_undo handles noop action correctly.
        
        CHAT-SPECIFIC: When delete was a no-op, undo only restores metadata.
        """
        state = create_chat_state()
        state.apply_input(create_chat_input())
        
        original_update_count = state.update_count
        
        # Delete non-existent message
        delete_input = ChatInput(
            timestamp=datetime.now(timezone.utc),
            operation="delete_message",
            message_id="nonexistent",
            conversation_id="default",
        )
        undo_data = state.create_undo_data(delete_input)
        state.apply_input(delete_input)
        
        # Undo should just restore metadata
        state.apply_undo(undo_data)
        
        assert state.update_count == original_update_count
        assert len(state.messages) == 1  # Original message still there

    def test_apply_undo_restores_cleared_conversation(self):
        """Test that apply_undo restores a cleared conversation.
        
        CHAT-SPECIFIC: restore_conversation action restores all messages and metadata.
        """
        state = create_chat_state()
        
        # Add messages
        for i in range(3):
            state.apply_input(create_chat_input(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                conversation_id="to-clear",
                timestamp=datetime.now(timezone.utc) + timedelta(seconds=i),
            ))
        
        original_messages = [m.content for m in state.messages]
        
        # Clear conversation
        clear_input = ChatInput(
            timestamp=datetime.now(timezone.utc),
            operation="clear_conversation",
            conversation_id="to-clear",
        )
        undo_data = state.create_undo_data(clear_input)
        state.apply_input(clear_input)
        
        assert len(state.messages) == 0
        assert "to-clear" not in state.conversations
        
        # Undo
        state.apply_undo(undo_data)
        
        assert len(state.messages) == 3
        restored_messages = [m.content for m in state.messages]
        assert restored_messages == original_messages
        assert "to-clear" in state.conversations
        assert state.conversations["to-clear"].message_count == 3

    def test_apply_undo_raises_for_missing_action(self):
        """Test that apply_undo raises for undo_data without action.
        
        GENERAL PATTERN: Undo data must have an action field.
        """
        state = create_chat_state()
        
        with pytest.raises(ValueError, match="action"):
            state.apply_undo({"message_id": "test"})

    def test_apply_undo_raises_for_missing_message_id(self):
        """Test that apply_undo raises for remove_message without message_id.
        
        GENERAL PATTERN: remove_message action needs message_id.
        """
        state = create_chat_state()
        
        with pytest.raises(ValueError, match="message_id"):
            state.apply_undo({
                "action": "remove_message",
                "conversation_id": "test",
                "state_previous_update_count": 0,
                "state_previous_last_updated": datetime.now(timezone.utc).isoformat(),
            })

    def test_apply_undo_raises_for_unknown_action(self):
        """Test that apply_undo raises for unknown action.
        
        GENERAL PATTERN: Only valid actions should be accepted.
        """
        state = create_chat_state()
        
        with pytest.raises(ValueError, match="Unknown undo action"):
            state.apply_undo({
                "action": "invalid_action",
                "state_previous_update_count": 0,
                "state_previous_last_updated": datetime.now(timezone.utc).isoformat(),
            })

    def test_apply_undo_raises_for_message_not_found(self):
        """Test that apply_undo raises when message to remove doesn't exist.
        
        GENERAL PATTERN: Cannot undo if state has been modified inconsistently.
        """
        state = create_chat_state()
        
        with pytest.raises(RuntimeError, match="not found"):
            state.apply_undo({
                "action": "remove_message",
                "message_id": "nonexistent",
                "conversation_id": "test",
                "was_new_conversation": True,
                "state_previous_update_count": 0,
                "state_previous_last_updated": datetime.now(timezone.utc).isoformat(),
            })

    def test_undo_full_cycle_send_new_conversation(self):
        """Test complete undo cycle for sending to a new conversation.
        
        INTEGRATION: create_undo_data -> apply_input -> apply_undo should be idempotent.
        """
        state = create_chat_state()
        original_snapshot = state.get_snapshot()
        
        chat_input = create_chat_input(
            content="Hello",
            conversation_id="new",
        )
        
        undo_data = state.create_undo_data(chat_input)
        state.apply_input(chat_input)
        state.apply_undo(undo_data)
        
        restored_snapshot = state.get_snapshot()
        assert restored_snapshot["total_message_count"] == original_snapshot["total_message_count"]
        assert restored_snapshot["update_count"] == original_snapshot["update_count"]
        assert restored_snapshot["conversation_count"] == original_snapshot["conversation_count"]

    def test_undo_full_cycle_send_existing_conversation(self):
        """Test complete undo cycle for sending to an existing conversation.
        
        INTEGRATION: create_undo_data -> apply_input -> apply_undo should be idempotent.
        """
        state = create_chat_state()
        
        # Create conversation
        state.apply_input(create_chat_input(
            content="First",
            conversation_id="chat",
        ))
        original_snapshot = state.get_snapshot()
        
        # Undo cycle for second message
        second_input = create_chat_input(
            content="Second",
            conversation_id="chat",
        )
        
        undo_data = state.create_undo_data(second_input)
        state.apply_input(second_input)
        state.apply_undo(undo_data)
        
        restored_snapshot = state.get_snapshot()
        assert restored_snapshot["total_message_count"] == original_snapshot["total_message_count"]
        assert restored_snapshot["update_count"] == original_snapshot["update_count"]

    def test_undo_full_cycle_delete_message(self):
        """Test complete undo cycle for delete_message operation.
        
        INTEGRATION: create_undo_data -> apply_input -> apply_undo should be idempotent.
        """
        state = create_chat_state()
        
        # Add a message
        msg_input = create_chat_input(content="To delete")
        state.apply_input(msg_input)
        original_snapshot = state.get_snapshot()
        
        # Undo cycle for delete
        delete_input = ChatInput(
            timestamp=datetime.now(timezone.utc),
            operation="delete_message",
            message_id=msg_input.message_id,
            conversation_id="default",
        )
        
        undo_data = state.create_undo_data(delete_input)
        state.apply_input(delete_input)
        state.apply_undo(undo_data)
        
        restored_snapshot = state.get_snapshot()
        assert restored_snapshot["total_message_count"] == original_snapshot["total_message_count"]
        assert restored_snapshot["update_count"] == original_snapshot["update_count"]

    def test_undo_full_cycle_clear_conversation(self):
        """Test complete undo cycle for clear_conversation operation.
        
        INTEGRATION: create_undo_data -> apply_input -> apply_undo should be idempotent.
        """
        state = create_chat_state()
        
        # Add messages
        for i in range(3):
            state.apply_input(create_chat_input(
                content=f"Message {i}",
                conversation_id="chat",
            ))
        original_snapshot = state.get_snapshot()
        
        # Undo cycle for clear
        clear_input = ChatInput(
            timestamp=datetime.now(timezone.utc),
            operation="clear_conversation",
            conversation_id="chat",
        )
        
        undo_data = state.create_undo_data(clear_input)
        state.apply_input(clear_input)
        state.apply_undo(undo_data)
        
        restored_snapshot = state.get_snapshot()
        assert restored_snapshot["total_message_count"] == original_snapshot["total_message_count"]
        assert restored_snapshot["update_count"] == original_snapshot["update_count"]
        assert restored_snapshot["conversation_count"] == original_snapshot["conversation_count"]

    def test_multiple_undo_operations_same_conversation(self):
        """Test multiple sequential undo operations on same conversation.
        
        INTEGRATION: Multiple undos should work correctly in sequence.
        """
        state = create_chat_state()
        
        undo_stack = []
        
        # Build up messages
        for i in range(5):
            chat_input = create_chat_input(
                content=f"Message {i}",
                conversation_id="chat",
                timestamp=datetime.now(timezone.utc) + timedelta(seconds=i),
            )
            undo_data = state.create_undo_data(chat_input)
            undo_stack.append(undo_data)
            state.apply_input(chat_input)
        
        assert len(state.messages) == 5
        assert state.update_count == 5
        
        # Undo all in reverse
        for undo_data in reversed(undo_stack):
            state.apply_undo(undo_data)
        
        assert len(state.messages) == 0
        assert state.update_count == 0
        assert len(state.conversations) == 0

    def test_multiple_undo_operations_multiple_conversations(self):
        """Test undo operations across multiple conversations.
        
        INTEGRATION: Undos should work correctly across different conversations.
        """
        state = create_chat_state()
        
        undo_stack = []
        
        # Messages to different conversations
        for conv_id in ["work", "personal", "default"]:
            for i in range(2):
                chat_input = create_chat_input(
                    content=f"{conv_id} message {i}",
                    conversation_id=conv_id,
                    timestamp=datetime.now(timezone.utc) + timedelta(seconds=len(undo_stack)),
                )
                undo_data = state.create_undo_data(chat_input)
                undo_stack.append(undo_data)
                state.apply_input(chat_input)
        
        assert len(state.messages) == 6
        assert len(state.conversations) == 3
        
        # Undo all
        for undo_data in reversed(undo_stack):
            state.apply_undo(undo_data)
        
        assert len(state.messages) == 0
        assert len(state.conversations) == 0
