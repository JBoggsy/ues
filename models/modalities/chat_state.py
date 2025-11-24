"""Chat state model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional, Union

from pydantic import BaseModel, Field

from models.base_input import ModalityInput
from models.base_state import ModalityState

if TYPE_CHECKING:
    from models.modalities.chat_input import ChatInput


class ChatMessage(BaseModel):
    """A single message in the chat conversation.

    Simple wrapper for storing message data in state.

    Args:
        message_id: Unique message identifier.
        conversation_id: Which conversation this belongs to.
        role: "user" or "assistant".
        content: Message content (string or multimodal structure).
        timestamp: When message was sent (simulator time).
        metadata: Optional additional data.
    """

    message_id: str = Field(description="Unique message identifier")
    conversation_id: str = Field(description="Which conversation this belongs to")
    role: str = Field(description="Message role (user or assistant)")
    content: Union[str, list[dict]] = Field(description="Message content")
    timestamp: datetime = Field(description="When message was sent")
    metadata: dict = Field(default_factory=dict, description="Optional additional data")

    def to_dict(self) -> dict[str, Any]:
        """Convert this message to a dictionary.

        Returns:
            Dictionary representation of this message.
        """
        result = {
            "message_id": self.message_id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.metadata:
            result["metadata"] = self.metadata
        return result


class ConversationMetadata(BaseModel):
    """Metadata for a conversation.

    Tracks summary information about a conversation without storing all messages.

    Args:
        conversation_id: Conversation identifier.
        created_at: When conversation started.
        last_message_at: When last message was sent.
        message_count: Number of messages in this conversation.
        participant_roles: Set of roles that have participated.
    """

    conversation_id: str = Field(description="Conversation identifier")
    created_at: datetime = Field(description="When conversation started")
    last_message_at: datetime = Field(description="When last message was sent")
    message_count: int = Field(default=0, description="Number of messages")
    participant_roles: set[str] = Field(default_factory=set, description="Roles that have participated")

    def to_dict(self) -> dict[str, Any]:
        """Convert this metadata to a dictionary.

        Returns:
            Dictionary representation of this metadata.
        """
        return {
            "conversation_id": self.conversation_id,
            "created_at": self.created_at.isoformat(),
            "last_message_at": self.last_message_at.isoformat(),
            "message_count": self.message_count,
            "participant_roles": list(self.participant_roles),
        }


class ChatState(ModalityState):
    """Current chat conversation state.

    Tracks complete conversation history and current state of chat interactions.
    Supports multiple concurrent conversations.

    Args:
        modality_type: Always "chat" for this state type.
        last_updated: When state was last modified.
        update_count: Number of messages added.
        messages: List of ChatMessage objects (ordered by timestamp).
        conversations: Dict mapping conversation_id to ConversationMetadata.
        max_history_size: Maximum messages to retain per conversation.
        default_conversation_id: ID for default conversation.
    """

    modality_type: str = Field(default="chat", frozen=True)
    messages: list[ChatMessage] = Field(
        default_factory=list, description="List of all messages (ordered by timestamp)"
    )
    conversations: dict[str, ConversationMetadata] = Field(
        default_factory=dict, description="Metadata for each conversation"
    )
    max_history_size: int = Field(
        default=1000, description="Maximum messages to retain per conversation"
    )
    default_conversation_id: str = Field(
        default="default", description="ID for default conversation"
    )

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True

    def apply_input(self, input_data: ModalityInput) -> None:
        """Apply a ChatInput to modify this state.

        Dispatches to operation-specific handlers based on operation type.

        Args:
            input_data: The ChatInput to apply to this state.

        Raises:
            ValueError: If input_data is not a ChatInput.
        """
        from models.modalities.chat_input import ChatInput

        if not isinstance(input_data, ChatInput):
            raise ValueError(
                f"ChatState can only apply ChatInput, got {type(input_data)}"
            )

        input_data.validate_input()

        operation_handlers = {
            "send_message": self._handle_send_message,
            "delete_message": self._handle_delete_message,
            "clear_conversation": self._handle_clear_conversation,
        }

        handler = operation_handlers.get(input_data.operation)
        if handler:
            handler(input_data)
            self.last_updated = input_data.timestamp
            self.update_count += 1
        else:
            raise ValueError(f"Unknown operation: {input_data.operation}")

    def _handle_send_message(self, input_data: "ChatInput") -> None:
        """Handle sending a new message.

        Args:
            input_data: Chat input data.
        """
        conversation_id = input_data.conversation_id

        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = ConversationMetadata(
                conversation_id=conversation_id,
                created_at=input_data.timestamp,
                last_message_at=input_data.timestamp,
                message_count=0,
                participant_roles=set(),
            )

        message = ChatMessage(
            message_id=input_data.message_id,
            conversation_id=conversation_id,
            role=input_data.role,
            content=input_data.content,
            timestamp=input_data.timestamp,
            metadata=input_data.metadata,
        )

        self.messages.append(message)
        self.messages.sort(key=lambda m: (m.timestamp, m.message_id))

        conv_metadata = self.conversations[conversation_id]
        conv_metadata.last_message_at = input_data.timestamp
        conv_metadata.message_count += 1
        conv_metadata.participant_roles.add(input_data.role)

        conv_messages = [m for m in self.messages if m.conversation_id == conversation_id]
        if len(conv_messages) > self.max_history_size:
            messages_to_remove = len(conv_messages) - self.max_history_size
            removed_count = 0
            self.messages = [
                m
                for m in self.messages
                if not (m.conversation_id == conversation_id and removed_count < messages_to_remove and (removed_count := removed_count + 1))
            ]

    def _handle_delete_message(self, input_data: "ChatInput") -> None:
        """Handle deleting a message.

        Args:
            input_data: Chat input data.
            
        Note:
            If message is not found, this is a no-op (similar to email/SMS patterns).
        """
        message_id = input_data.message_id
        
        for i, msg in enumerate(self.messages):
            if msg.message_id == message_id:
                conv_id = msg.conversation_id
                self.messages.pop(i)
                
                # Update conversation metadata
                if conv_id in self.conversations:
                    conv = self.conversations[conv_id]
                    conv.message_count -= 1
                    
                    # Update last_message_at if we deleted the last message
                    remaining_msgs = [m for m in self.messages if m.conversation_id == conv_id]
                    if remaining_msgs:
                        conv.last_message_at = max(m.timestamp for m in remaining_msgs)
                return
        
        # Message not found - no-op (consistent with email/SMS modalities)

    def _handle_clear_conversation(self, input_data: "ChatInput") -> None:
        """Handle clearing a conversation.

        Args:
            input_data: Chat input data.
        """
        conversation_id = input_data.conversation_id
        
        # Remove all messages from this conversation
        self.messages = [
            m for m in self.messages if m.conversation_id != conversation_id
        ]
        
        # Remove conversation metadata
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]

    def get_snapshot(self) -> dict[str, Any]:
        """Return a complete snapshot of current state for API responses.

        Returns:
            Dictionary representation of all conversations and messages.
        """
        return {
            "modality_type": self.modality_type,
            "last_updated": self.last_updated.isoformat(),
            "update_count": self.update_count,
            "conversations": {
                conv_id: metadata.to_dict()
                for conv_id, metadata in self.conversations.items()
            },
            "messages": [msg.to_dict() for msg in self.messages],
            "total_message_count": len(self.messages),
            "conversation_count": len(self.conversations),
        }

    def validate_state(self) -> list[str]:
        """Validate internal state consistency and return any issues.

        Checks for:
        - Message ordering (chronological within conversations)
        - Conversation metadata consistency
        - History limits

        Returns:
            List of validation error messages (empty list if valid).
        """
        issues = []

        for i in range(1, len(self.messages)):
            if self.messages[i].timestamp < self.messages[i - 1].timestamp:
                issues.append(f"Messages not in chronological order at index {i}")

        for conv_id, metadata in self.conversations.items():
            conv_messages = [m for m in self.messages if m.conversation_id == conv_id]

            if len(conv_messages) != metadata.message_count:
                issues.append(
                    f"Conversation {conv_id} metadata count {metadata.message_count} "
                    f"doesn't match actual count {len(conv_messages)}"
                )

            if len(conv_messages) > self.max_history_size:
                issues.append(
                    f"Conversation {conv_id} has {len(conv_messages)} messages, "
                    f"exceeds maximum {self.max_history_size}"
                )

            if conv_messages:
                actual_roles = {m.role for m in conv_messages}
                if actual_roles != metadata.participant_roles:
                    issues.append(
                        f"Conversation {conv_id} metadata roles {metadata.participant_roles} "
                        f"don't match actual roles {actual_roles}"
                    )

                last_msg = max(conv_messages, key=lambda m: m.timestamp)
                if last_msg.timestamp != metadata.last_message_at:
                    issues.append(
                        f"Conversation {conv_id} metadata last_message_at doesn't match "
                        f"actual last message timestamp"
                    )

        return issues

    def query(self, query_params: dict[str, Any]) -> dict[str, Any]:
        """Execute a query against this state.

        Supports filtering messages by conversation, role, time range, and text search.

        Supported query parameters:
            - conversation_id: str - Filter by conversation
            - role: str - Filter by role ("user" or "assistant")
            - since: datetime - Return messages after this time
            - until: datetime - Return messages before this time
            - limit: int - Maximum number of results
            - offset: int - Number of results to skip (for pagination)
            - search: str - Search for text in message content
            - sort_by: str - Field to sort by ("timestamp", "role", "conversation_id")
            - sort_order: str - Sort order ("asc" or "desc")

        Args:
            query_params: Dictionary of query parameters.

        Returns:
            Dictionary containing matching messages:
                - messages: List of message objects matching the query.
                - count: Number of messages returned (after pagination).
                - total_count: Total number of messages matching query (before pagination).
        """
        conversation_id = query_params.get("conversation_id")
        role = query_params.get("role")
        since = query_params.get("since")
        until = query_params.get("until")
        limit = query_params.get("limit")
        search = query_params.get("search")

        filtered_messages = self.messages

        if conversation_id:
            filtered_messages = [
                m for m in filtered_messages if m.conversation_id == conversation_id
            ]

        if role:
            filtered_messages = [m for m in filtered_messages if m.role == role]

        if since:
            since_dt = since if isinstance(since, datetime) else datetime.fromisoformat(since)
            filtered_messages = [m for m in filtered_messages if m.timestamp >= since_dt]

        if until:
            until_dt = until if isinstance(until, datetime) else datetime.fromisoformat(until)
            filtered_messages = [m for m in filtered_messages if m.timestamp <= until_dt]

        if search:
            search_lower = search.lower()
            filtered_messages = [
                m
                for m in filtered_messages
                if self._message_contains_text(m, search_lower)
            ]

        # Sort messages
        sort_by = query_params.get("sort_by", "timestamp")
        sort_order = query_params.get("sort_order", "asc")
        if sort_by in ["timestamp", "role", "conversation_id"]:
            filtered_messages.sort(
                key=lambda m: getattr(m, sort_by),
                reverse=(sort_order == "desc")
            )

        # Store total count before pagination
        total_count = len(filtered_messages)

        # Apply pagination
        offset = query_params.get("offset", 0)
        if offset:
            filtered_messages = filtered_messages[offset:]
        if limit:
            filtered_messages = filtered_messages[:limit]

        return {
            "messages": [msg.to_dict() for msg in filtered_messages],
            "count": len(filtered_messages),
            "total_count": total_count,
        }

    def _message_contains_text(self, message: ChatMessage, search_text: str) -> bool:
        """Check if a message contains the search text.

        Args:
            message: Message to search.
            search_text: Text to search for (lowercase).

        Returns:
            True if message contains the text.
        """
        if isinstance(message.content, str):
            return search_text in message.content.lower()
        else:
            for block in message.content:
                if block.get("type") == "text" and search_text in block.get("text", "").lower():
                    return True
        return False

    def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        """Get all messages in a specific conversation.

        Args:
            conversation_id: Conversation identifier.

        Returns:
            Dictionary with conversation metadata and messages.
        """
        return self.query({"conversation_id": conversation_id})

    def get_recent_messages(
        self, limit: int = 10, conversation_id: Optional[str] = None
    ) -> dict[str, Any]:
        """Get most recent N messages.

        Args:
            limit: Maximum number of messages to return.
            conversation_id: Optional conversation filter.

        Returns:
            Dictionary with recent messages.
        """
        query_params = {"limit": limit}
        if conversation_id:
            query_params["conversation_id"] = conversation_id
        return self.query(query_params)

    def get_message_by_id(self, message_id: str) -> Optional[dict[str, Any]]:
        """Retrieve a specific message by ID.

        Args:
            message_id: Message identifier to find.

        Returns:
            Message dictionary if found, None otherwise.
        """
        for message in self.messages:
            if message.message_id == message_id:
                return message.to_dict()
        return None
