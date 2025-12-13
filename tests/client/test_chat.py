"""Unit tests for the ChatClient and AsyncChatClient.

This module tests the chat modality sub-client that provides methods for
sending messages, querying conversation history, and managing chat conversations.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from client._chat import (
    AsyncChatClient,
    ChatClient,
    ChatMessage,
    ChatQueryResponse,
    ChatStateResponse,
    ConversationMetadata,
)
from client.models import ModalityActionResponse


# =============================================================================
# Response Model Tests
# =============================================================================


class TestChatMessage:
    """Tests for the ChatMessage model."""

    def test_instantiation_with_string_content(self):
        """Test creating a ChatMessage with string content."""
        message = ChatMessage(
            message_id="msg-123",
            conversation_id="default",
            role="user",
            content="Hello, how are you?",
            timestamp=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
            metadata={"token_count": 5},
        )
        assert message.message_id == "msg-123"
        assert message.role == "user"
        assert message.content == "Hello, how are you?"
        assert message.metadata["token_count"] == 5

    def test_instantiation_with_multimodal_content(self):
        """Test creating a ChatMessage with multimodal content."""
        message = ChatMessage(
            message_id="msg-456",
            conversation_id="default",
            role="assistant",
            content=[
                {"type": "text", "text": "Here's an image:"},
                {"type": "image", "url": "https://example.com/image.png"},
            ],
            timestamp=datetime(2025, 1, 15, 10, 1, tzinfo=timezone.utc),
        )
        assert isinstance(message.content, list)
        assert len(message.content) == 2

    def test_instantiation_with_defaults(self):
        """Test creating a ChatMessage with default metadata."""
        message = ChatMessage(
            message_id="msg-123",
            conversation_id="default",
            role="user",
            content="Hello",
            timestamp=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
        )
        assert message.metadata == {}


class TestConversationMetadata:
    """Tests for the ConversationMetadata model."""

    def test_instantiation(self):
        """Test creating ConversationMetadata."""
        metadata = ConversationMetadata(
            conversation_id="conv-123",
            created_at=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
            last_message_at=datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc),
            message_count=10,
            user_message_count=5,
            assistant_message_count=5,
        )
        assert metadata.conversation_id == "conv-123"
        assert metadata.message_count == 10
        assert metadata.user_message_count == 5

    def test_instantiation_with_defaults(self):
        """Test ConversationMetadata with default counts."""
        metadata = ConversationMetadata(
            conversation_id="conv-123",
            created_at=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
            last_message_at=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
        )
        assert metadata.message_count == 0
        assert metadata.user_message_count == 0
        assert metadata.assistant_message_count == 0


class TestChatStateResponse:
    """Tests for the ChatStateResponse model."""

    def test_instantiation(self):
        """Test creating a ChatStateResponse."""
        response = ChatStateResponse(
            modality_type="chat",
            current_time=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
            conversations={
                "default": ConversationMetadata(
                    conversation_id="default",
                    created_at=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
                    last_message_at=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
                    message_count=5,
                    user_message_count=3,
                    assistant_message_count=2,
                ),
            },
            messages=[],
            total_message_count=5,
            conversation_count=1,
            max_history_size=1000,
        )
        assert response.modality_type == "chat"
        assert response.total_message_count == 5
        assert response.conversation_count == 1


class TestChatQueryResponse:
    """Tests for the ChatQueryResponse model."""

    def test_instantiation(self):
        """Test creating a ChatQueryResponse."""
        response = ChatQueryResponse(
            modality_type="chat",
            messages=[],
            total_count=10,
            returned_count=5,
            query={"role": "user", "limit": 5},
        )
        assert response.total_count == 10
        assert response.returned_count == 5


# =============================================================================
# ChatClient Tests
# =============================================================================


class TestChatClientGetState:
    """Tests for ChatClient.get_state() method."""

    def test_get_state(self):
        """Test getting chat state."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "modality_type": "chat",
            "current_time": "2025-01-15T10:00:00+00:00",
            "conversations": {
                "default": {
                    "conversation_id": "default",
                    "created_at": "2025-01-15T10:00:00+00:00",
                    "last_message_at": "2025-01-15T10:00:00+00:00",
                    "message_count": 5,
                    "user_message_count": 3,
                    "assistant_message_count": 2,
                },
            },
            "messages": [],
            "total_message_count": 5,
            "conversation_count": 1,
            "max_history_size": 1000,
        }

        client = ChatClient(mock_http)
        result = client.get_state()

        mock_http.get.assert_called_once_with("/chat/state", params=None)
        assert isinstance(result, ChatStateResponse)
        assert result.total_message_count == 5


class TestChatClientQuery:
    """Tests for ChatClient.query() method."""

    def test_query_no_filters(self):
        """Test querying messages with no filters."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "modality_type": "chat",
            "messages": [],
            "total_count": 0,
            "returned_count": 0,
            "query": {},
        }

        client = ChatClient(mock_http)
        result = client.query()

        mock_http.post.assert_called_once_with("/chat/query", json={}, params=None)
        assert isinstance(result, ChatQueryResponse)

    def test_query_with_filters(self):
        """Test querying messages with various filters."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "modality_type": "chat",
            "messages": [],
            "total_count": 3,
            "returned_count": 3,
            "query": {"role": "user"},
        }

        client = ChatClient(mock_http)
        result = client.query(
            conversation_id="conv-123",
            role="user",
            search="hello",
            limit=10,
        )

        call_args = mock_http.post.call_args
        assert call_args[1]["json"]["conversation_id"] == "conv-123"
        assert call_args[1]["json"]["role"] == "user"
        assert call_args[1]["json"]["search"] == "hello"
        assert call_args[1]["json"]["limit"] == 10

    def test_query_with_date_filters(self):
        """Test querying messages with date filters."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "modality_type": "chat",
            "messages": [],
            "total_count": 0,
            "returned_count": 0,
            "query": {},
        }

        client = ChatClient(mock_http)
        since = datetime(2025, 1, 15, 0, 0, tzinfo=timezone.utc)
        until = datetime(2025, 1, 16, 0, 0, tzinfo=timezone.utc)
        client.query(since=since, until=until)

        call_args = mock_http.post.call_args
        assert "since" in call_args[1]["json"]
        assert "until" in call_args[1]["json"]

    def test_query_with_sort_options(self):
        """Test querying messages with sort options."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "modality_type": "chat",
            "messages": [],
            "total_count": 0,
            "returned_count": 0,
            "query": {},
        }

        client = ChatClient(mock_http)
        client.query(sort_by="role", sort_order="desc")

        call_args = mock_http.post.call_args
        assert call_args[1]["json"]["sort_by"] == "role"
        assert call_args[1]["json"]["sort_order"] == "desc"


class TestChatClientSend:
    """Tests for ChatClient.send() method."""

    def test_send_user_message(self):
        """Test sending a user message."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Message sent",
            "modality": "chat",
        }

        client = ChatClient(mock_http)
        result = client.send(
            role="user",
            content="Hello, how are you?",
        )

        mock_http.post.assert_called_once()
        call_args = mock_http.post.call_args
        assert call_args[0][0] == "/chat/send"
        assert call_args[1]["json"]["role"] == "user"
        assert call_args[1]["json"]["content"] == "Hello, how are you?"
        assert call_args[1]["json"]["conversation_id"] == "default"
        assert isinstance(result, ModalityActionResponse)

    def test_send_assistant_message(self):
        """Test sending an assistant message."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Message sent",
            "modality": "chat",
        }

        client = ChatClient(mock_http)
        result = client.send(
            role="assistant",
            content="I'm doing well, thank you!",
            conversation_id="conv-123",
            metadata={"model": "gpt-4", "token_count": 10},
        )

        call_args = mock_http.post.call_args
        assert call_args[1]["json"]["role"] == "assistant"
        assert call_args[1]["json"]["conversation_id"] == "conv-123"
        assert call_args[1]["json"]["metadata"]["model"] == "gpt-4"

    def test_send_multimodal_content(self):
        """Test sending a message with multimodal content."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Message sent",
            "modality": "chat",
        }

        client = ChatClient(mock_http)
        result = client.send(
            role="user",
            content=[
                {"type": "text", "text": "What's in this image?"},
                {"type": "image_url", "url": "https://example.com/image.png"},
            ],
        )

        call_args = mock_http.post.call_args
        assert isinstance(call_args[1]["json"]["content"], list)
        assert len(call_args[1]["json"]["content"]) == 2


class TestChatClientDelete:
    """Tests for ChatClient.delete() method."""

    def test_delete(self):
        """Test deleting a chat message."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Message deleted",
            "modality": "chat",
        }

        client = ChatClient(mock_http)
        result = client.delete(message_id="msg-123")

        mock_http.post.assert_called_once_with(
            "/chat/delete",
            json={"message_id": "msg-123"},
            params=None,
        )
        assert isinstance(result, ModalityActionResponse)


class TestChatClientClear:
    """Tests for ChatClient.clear() method."""

    def test_clear_default_conversation(self):
        """Test clearing the default conversation."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Conversation cleared",
            "modality": "chat",
        }

        client = ChatClient(mock_http)
        result = client.clear()

        mock_http.post.assert_called_once_with(
            "/chat/clear",
            json={"conversation_id": "default"},
            params=None,
        )
        assert isinstance(result, ModalityActionResponse)

    def test_clear_specific_conversation(self):
        """Test clearing a specific conversation."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Conversation cleared",
            "modality": "chat",
        }

        client = ChatClient(mock_http)
        result = client.clear(conversation_id="conv-123")

        mock_http.post.assert_called_once_with(
            "/chat/clear",
            json={"conversation_id": "conv-123"},
            params=None,
        )


# =============================================================================
# AsyncChatClient Tests
# =============================================================================


class TestAsyncChatClientGetState:
    """Tests for AsyncChatClient.get_state() method."""

    async def test_get_state(self):
        """Test getting chat state asynchronously."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {
            "modality_type": "chat",
            "current_time": "2025-01-15T10:00:00+00:00",
            "conversations": {},
            "messages": [],
            "total_message_count": 0,
            "conversation_count": 0,
            "max_history_size": 1000,
        }

        client = AsyncChatClient(mock_http)
        result = await client.get_state()

        mock_http.get.assert_called_once_with("/chat/state", params=None)
        assert isinstance(result, ChatStateResponse)


class TestAsyncChatClientQuery:
    """Tests for AsyncChatClient.query() method."""

    async def test_query(self):
        """Test querying messages asynchronously."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "modality_type": "chat",
            "messages": [],
            "total_count": 0,
            "returned_count": 0,
            "query": {"role": "user"},
        }

        client = AsyncChatClient(mock_http)
        result = await client.query(role="user")

        mock_http.post.assert_called_once()
        assert isinstance(result, ChatQueryResponse)


class TestAsyncChatClientSend:
    """Tests for AsyncChatClient.send() method."""

    async def test_send(self):
        """Test sending a message asynchronously."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Message sent",
            "modality": "chat",
        }

        client = AsyncChatClient(mock_http)
        result = await client.send(
            role="user",
            content="Hello!",
        )

        assert isinstance(result, ModalityActionResponse)


class TestAsyncChatClientDelete:
    """Tests for AsyncChatClient.delete() method."""

    async def test_delete(self):
        """Test deleting a message asynchronously."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Message deleted",
            "modality": "chat",
        }

        client = AsyncChatClient(mock_http)
        result = await client.delete(message_id="msg-123")

        mock_http.post.assert_called_once()
        assert isinstance(result, ModalityActionResponse)


class TestAsyncChatClientClear:
    """Tests for AsyncChatClient.clear() method."""

    async def test_clear(self):
        """Test clearing a conversation asynchronously."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Conversation cleared",
            "modality": "chat",
        }

        client = AsyncChatClient(mock_http)
        result = await client.clear(conversation_id="conv-123")

        mock_http.post.assert_called_once()
        assert isinstance(result, ModalityActionResponse)
