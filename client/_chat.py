"""Chat modality sub-client for the UES API.

This module provides ChatClient and AsyncChatClient for interacting with
the chat modality endpoints (/chat/*).

This is an internal module. Import from `client` instead.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field

from client._base import AsyncBaseClient, BaseClient
from client.models import ModalityActionResponse

if TYPE_CHECKING:
    from client._http import AsyncHTTPClient, HTTPClient


# Response models for chat endpoints


class ChatMessage(BaseModel):
    """Represents a chat message.
    
    Attributes:
        message_id: Unique message identifier.
        conversation_id: Conversation/thread identifier.
        role: Message sender role ("user" or "assistant").
        content: Message content (string for text, or list for multimodal).
        timestamp: When the message was sent.
        metadata: Optional additional data (token count, model info, etc.).
    """

    message_id: str
    conversation_id: str
    role: str
    content: str | list[dict[str, Any]]
    timestamp: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationMetadata(BaseModel):
    """Metadata for a conversation.
    
    Attributes:
        conversation_id: Unique conversation identifier.
        created_at: When the conversation started.
        last_message_at: When the last message was sent.
        message_count: Total number of messages.
        user_message_count: Number of user messages.
        assistant_message_count: Number of assistant messages.
    """

    conversation_id: str
    created_at: datetime
    last_message_at: datetime
    message_count: int = 0
    user_message_count: int = 0
    assistant_message_count: int = 0


class ChatStateResponse(BaseModel):
    """Response model for chat state endpoint.
    
    Attributes:
        modality_type: Always "chat".
        current_time: Current simulator time.
        conversations: Metadata for each conversation.
        messages: All messages (ordered by timestamp).
        total_message_count: Total number of messages.
        conversation_count: Total number of conversations.
        max_history_size: Maximum messages retained per conversation.
    """

    modality_type: str = "chat"
    current_time: datetime
    conversations: dict[str, ConversationMetadata]
    messages: list[ChatMessage]
    total_message_count: int
    conversation_count: int
    max_history_size: int


class ChatQueryResponse(BaseModel):
    """Response model for chat query endpoint.
    
    Attributes:
        modality_type: Always "chat".
        messages: Query results (matching messages).
        total_count: Total number of results matching query.
        returned_count: Number of results returned (after pagination).
        query: Echo of query parameters for debugging.
    """

    modality_type: str = "chat"
    messages: list[ChatMessage]
    total_count: int
    returned_count: int
    query: dict[str, Any]


# Synchronous ChatClient


class ChatClient(BaseClient):
    """Synchronous client for chat modality endpoints (/chat/*).
    
    This client provides methods for sending messages, querying conversation
    history, and managing chat conversations between user and assistant.
    
    Example:
        with UESClient() as client:
            # Send a user message
            client.chat.send(
                role="user",
                content="Hello, how are you?",
            )
            
            # Send an assistant response
            client.chat.send(
                role="assistant",
                content="I'm doing well, thank you!",
            )
            
            # Get chat state
            state = client.chat.get_state()
            print(f"Total messages: {state.total_message_count}")
            
            # Query messages from a specific role
            user_msgs = client.chat.query(role="user")
            print(f"Found {user_msgs.total_count} user messages")
    """

    _BASE_PATH = "/chat"

    def get_state(self) -> ChatStateResponse:
        """Get the current chat state.
        
        Returns a complete snapshot of all chat conversations and messages.
        
        Returns:
            Complete chat state with conversations and messages.
        
        Raises:
            APIError: If the request fails.
        """
        data = self._get(f"{self._BASE_PATH}/state")
        return ChatStateResponse(**data)

    def query(
        self,
        conversation_id: str | None = None,
        role: Literal["user", "assistant"] | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        search: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        sort_by: Literal["timestamp", "role", "conversation_id"] = "timestamp",
        sort_order: Literal["asc", "desc"] = "asc",
    ) -> ChatQueryResponse:
        """Query chat messages with filters.
        
        Allows filtering and searching through chat history with various criteria
        including conversation, role, time range, and text search.
        
        Args:
            conversation_id: Filter by conversation ID.
            role: Filter by role ("user" or "assistant").
            since: Filter messages after this time.
            until: Filter messages before this time.
            search: Search for text in message content (case-insensitive).
            limit: Maximum number of results to return.
            offset: Number of results to skip (for pagination).
            sort_by: Field to sort by ("timestamp", "role", "conversation_id").
            sort_order: Sort direction ("asc" or "desc").
        
        Returns:
            Filtered message results with counts.
        
        Raises:
            ValidationError: If query parameters are invalid.
            APIError: If the request fails.
        """
        # Build the request body, excluding None values
        request_data: dict[str, Any] = {}
        
        if conversation_id is not None:
            request_data["conversation_id"] = conversation_id
        if role is not None:
            request_data["role"] = role
        if since is not None:
            request_data["since"] = since.isoformat()
        if until is not None:
            request_data["until"] = until.isoformat()
        if search is not None:
            request_data["search"] = search
        if limit is not None:
            request_data["limit"] = limit
        if offset != 0:
            request_data["offset"] = offset
        if sort_by != "timestamp":
            request_data["sort_by"] = sort_by
        if sort_order != "asc":
            request_data["sort_order"] = sort_order
        
        data = self._post(f"{self._BASE_PATH}/query", json=request_data)
        return ChatQueryResponse(**data)

    def send(
        self,
        role: Literal["user", "assistant"],
        content: str | list[dict[str, Any]],
        conversation_id: str = "default",
        metadata: dict[str, Any] | None = None,
    ) -> ModalityActionResponse:
        """Send a chat message.
        
        Creates an immediate event to send a message from either the user or
        assistant to the conversation history.
        
        Args:
            role: Message sender role ("user" or "assistant").
            content: Message content (string for text, or list of content blocks
                for multimodal messages).
            conversation_id: Conversation/thread identifier (default: "default").
            metadata: Optional additional data (token count, model info, etc.).
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If request parameters are invalid.
            APIError: If the request fails.
        """
        request_data: dict[str, Any] = {
            "role": role,
            "content": content,
            "conversation_id": conversation_id,
        }
        
        if metadata is not None:
            request_data["metadata"] = metadata
        
        data = self._post(f"{self._BASE_PATH}/send", json=request_data)
        return ModalityActionResponse(**data)

    def delete(self, message_id: str) -> ModalityActionResponse:
        """Delete a chat message.
        
        Creates an immediate event to remove a specific message from the
        conversation history.
        
        Args:
            message_id: Message ID to delete.
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If message_id is invalid.
            APIError: If the request fails.
        """
        data = self._post(
            f"{self._BASE_PATH}/delete",
            json={"message_id": message_id},
        )
        return ModalityActionResponse(**data)

    def clear(self, conversation_id: str = "default") -> ModalityActionResponse:
        """Clear conversation history.
        
        Creates an immediate event to remove all messages from a specific
        conversation.
        
        Args:
            conversation_id: Conversation ID to clear (default: "default").
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If conversation_id is invalid.
            APIError: If the request fails.
        """
        data = self._post(
            f"{self._BASE_PATH}/clear",
            json={"conversation_id": conversation_id},
        )
        return ModalityActionResponse(**data)


# Asynchronous AsyncChatClient


class AsyncChatClient(AsyncBaseClient):
    """Asynchronous client for chat modality endpoints (/chat/*).
    
    This client provides async methods for sending messages, querying conversation
    history, and managing chat conversations between user and assistant.
    
    Example:
        async with AsyncUESClient() as client:
            # Send a user message
            await client.chat.send(
                role="user",
                content="Hello, how are you?",
            )
            
            # Send an assistant response
            await client.chat.send(
                role="assistant",
                content="I'm doing well, thank you!",
            )
            
            # Get chat state
            state = await client.chat.get_state()
            print(f"Total messages: {state.total_message_count}")
            
            # Query messages from a specific role
            user_msgs = await client.chat.query(role="user")
            print(f"Found {user_msgs.total_count} user messages")
    """

    _BASE_PATH = "/chat"

    async def get_state(self) -> ChatStateResponse:
        """Get the current chat state.
        
        Returns a complete snapshot of all chat conversations and messages.
        
        Returns:
            Complete chat state with conversations and messages.
        
        Raises:
            APIError: If the request fails.
        """
        data = await self._get(f"{self._BASE_PATH}/state")
        return ChatStateResponse(**data)

    async def query(
        self,
        conversation_id: str | None = None,
        role: Literal["user", "assistant"] | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        search: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        sort_by: Literal["timestamp", "role", "conversation_id"] = "timestamp",
        sort_order: Literal["asc", "desc"] = "asc",
    ) -> ChatQueryResponse:
        """Query chat messages with filters.
        
        Allows filtering and searching through chat history with various criteria
        including conversation, role, time range, and text search.
        
        Args:
            conversation_id: Filter by conversation ID.
            role: Filter by role ("user" or "assistant").
            since: Filter messages after this time.
            until: Filter messages before this time.
            search: Search for text in message content (case-insensitive).
            limit: Maximum number of results to return.
            offset: Number of results to skip (for pagination).
            sort_by: Field to sort by ("timestamp", "role", "conversation_id").
            sort_order: Sort direction ("asc" or "desc").
        
        Returns:
            Filtered message results with counts.
        
        Raises:
            ValidationError: If query parameters are invalid.
            APIError: If the request fails.
        """
        # Build the request body, excluding None values
        request_data: dict[str, Any] = {}
        
        if conversation_id is not None:
            request_data["conversation_id"] = conversation_id
        if role is not None:
            request_data["role"] = role
        if since is not None:
            request_data["since"] = since.isoformat()
        if until is not None:
            request_data["until"] = until.isoformat()
        if search is not None:
            request_data["search"] = search
        if limit is not None:
            request_data["limit"] = limit
        if offset != 0:
            request_data["offset"] = offset
        if sort_by != "timestamp":
            request_data["sort_by"] = sort_by
        if sort_order != "asc":
            request_data["sort_order"] = sort_order
        
        data = await self._post(f"{self._BASE_PATH}/query", json=request_data)
        return ChatQueryResponse(**data)

    async def send(
        self,
        role: Literal["user", "assistant"],
        content: str | list[dict[str, Any]],
        conversation_id: str = "default",
        metadata: dict[str, Any] | None = None,
    ) -> ModalityActionResponse:
        """Send a chat message.
        
        Creates an immediate event to send a message from either the user or
        assistant to the conversation history.
        
        Args:
            role: Message sender role ("user" or "assistant").
            content: Message content (string for text, or list of content blocks
                for multimodal messages).
            conversation_id: Conversation/thread identifier (default: "default").
            metadata: Optional additional data (token count, model info, etc.).
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If request parameters are invalid.
            APIError: If the request fails.
        """
        request_data: dict[str, Any] = {
            "role": role,
            "content": content,
            "conversation_id": conversation_id,
        }
        
        if metadata is not None:
            request_data["metadata"] = metadata
        
        data = await self._post(f"{self._BASE_PATH}/send", json=request_data)
        return ModalityActionResponse(**data)

    async def delete(self, message_id: str) -> ModalityActionResponse:
        """Delete a chat message.
        
        Creates an immediate event to remove a specific message from the
        conversation history.
        
        Args:
            message_id: Message ID to delete.
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If message_id is invalid.
            APIError: If the request fails.
        """
        data = await self._post(
            f"{self._BASE_PATH}/delete",
            json={"message_id": message_id},
        )
        return ModalityActionResponse(**data)

    async def clear(self, conversation_id: str = "default") -> ModalityActionResponse:
        """Clear conversation history.
        
        Creates an immediate event to remove all messages from a specific
        conversation.
        
        Args:
            conversation_id: Conversation ID to clear (default: "default").
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If conversation_id is invalid.
            APIError: If the request fails.
        """
        data = await self._post(
            f"{self._BASE_PATH}/clear",
            json={"conversation_id": conversation_id},
        )
        return ModalityActionResponse(**data)
