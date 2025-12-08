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

    def clear(self) -> None:
        """Reset chat state to empty defaults.

        Clears all messages and conversations, returning the state to
        a freshly created condition.
        """
        self.messages.clear()
        self.conversations.clear()
        self.update_count = 0

    def create_undo_data(self, input_data: ModalityInput) -> dict[str, Any]:
        """Capture minimal data needed to undo applying a ChatInput.

        For chat operations:
        - send_message: Store message_id to remove, plus conversation creation/capacity info
        - delete_message: Store the full message being deleted
        - clear_conversation: Store all messages and metadata being cleared

        Args:
            input_data: The ChatInput that will be applied.

        Returns:
            Dictionary containing minimal data needed to undo the operation.
        """
        from models.modalities.chat_input import ChatInput

        if not isinstance(input_data, ChatInput):
            raise ValueError(
                f"ChatState can only create undo data for ChatInput, got {type(input_data)}"
            )

        # Ensure input is validated (auto-generates message_id for send_message)
        input_data.validate_input()

        base_undo: dict[str, Any] = {
            "state_previous_update_count": self.update_count,
            "state_previous_last_updated": self.last_updated.isoformat(),
        }

        if input_data.operation == "send_message":
            conversation_id = input_data.conversation_id
            is_new_conversation = conversation_id not in self.conversations

            undo_data = {
                **base_undo,
                "action": "remove_message",
                "message_id": input_data.message_id,
                "conversation_id": conversation_id,
                "was_new_conversation": is_new_conversation,
            }

            if not is_new_conversation:
                # Capture current conversation metadata for restoration
                conv = self.conversations[conversation_id]
                undo_data["previous_conv_metadata"] = {
                    "last_message_at": conv.last_message_at.isoformat(),
                    "message_count": conv.message_count,
                    "participant_roles": list(conv.participant_roles),
                }

                # Check if we'll exceed capacity and lose messages
                conv_messages = [m for m in self.messages if m.conversation_id == conversation_id]
                if len(conv_messages) >= self.max_history_size:
                    # The oldest message will be removed - capture it
                    conv_messages.sort(key=lambda m: (m.timestamp, m.message_id))
                    oldest = conv_messages[0]
                    undo_data["removed_message"] = {
                        "message_id": oldest.message_id,
                        "conversation_id": oldest.conversation_id,
                        "role": oldest.role,
                        "content": oldest.content,
                        "timestamp": oldest.timestamp.isoformat(),
                        "metadata": oldest.metadata,
                    }

            return undo_data

        elif input_data.operation == "delete_message":
            # Find the message that will be deleted
            message_id = input_data.message_id
            target_message = None
            for msg in self.messages:
                if msg.message_id == message_id:
                    target_message = msg
                    break

            if target_message is None:
                # Message doesn't exist - delete is a no-op, undo is also no-op
                return {
                    **base_undo,
                    "action": "noop",
                }

            return {
                **base_undo,
                "action": "restore_message",
                "message": {
                    "message_id": target_message.message_id,
                    "conversation_id": target_message.conversation_id,
                    "role": target_message.role,
                    "content": target_message.content,
                    "timestamp": target_message.timestamp.isoformat(),
                    "metadata": target_message.metadata,
                },
                "conversation_existed": target_message.conversation_id in self.conversations,
            }

        elif input_data.operation == "clear_conversation":
            conversation_id = input_data.conversation_id

            # Capture all messages that will be cleared
            conv_messages = [m for m in self.messages if m.conversation_id == conversation_id]
            cleared_messages = [
                {
                    "message_id": m.message_id,
                    "conversation_id": m.conversation_id,
                    "role": m.role,
                    "content": m.content,
                    "timestamp": m.timestamp.isoformat(),
                    "metadata": m.metadata,
                }
                for m in conv_messages
            ]

            # Capture conversation metadata if it exists
            conv_metadata = None
            if conversation_id in self.conversations:
                conv = self.conversations[conversation_id]
                conv_metadata = {
                    "conversation_id": conv.conversation_id,
                    "created_at": conv.created_at.isoformat(),
                    "last_message_at": conv.last_message_at.isoformat(),
                    "message_count": conv.message_count,
                    "participant_roles": list(conv.participant_roles),
                }

            return {
                **base_undo,
                "action": "restore_conversation",
                "conversation_id": conversation_id,
                "cleared_messages": cleared_messages,
                "conv_metadata": conv_metadata,
            }

        else:
            raise ValueError(f"Unknown operation: {input_data.operation}")

    def apply_undo(self, undo_data: dict[str, Any]) -> None:
        """Apply undo data to reverse a previous chat input application.

        Handles:
        - remove_message: Removes a message that was added by send_message
        - restore_message: Restores a message that was deleted
        - restore_conversation: Restores a cleared conversation
        - noop: Does nothing (for operations that had no effect)

        Args:
            undo_data: Dictionary returned by create_undo_data().

        Raises:
            ValueError: If undo_data is invalid or action is unknown.
            RuntimeError: If state has been modified in a way that prevents undo.
        """
        action = undo_data.get("action")
        if not action:
            raise ValueError("Undo data missing 'action' field")

        if action == "noop":
            # Restore state-level metadata only
            self.update_count = undo_data["state_previous_update_count"]
            self.last_updated = datetime.fromisoformat(
                undo_data["state_previous_last_updated"]
            )
            return

        if action == "remove_message":
            message_id = undo_data.get("message_id")
            if not message_id:
                raise ValueError("Undo data missing 'message_id' field")

            conversation_id = undo_data.get("conversation_id")
            if not conversation_id:
                raise ValueError("Undo data missing 'conversation_id' field")

            # Remove the message that was added
            message_found = False
            for i, msg in enumerate(self.messages):
                if msg.message_id == message_id:
                    self.messages.pop(i)
                    message_found = True
                    break

            if not message_found:
                raise RuntimeError(
                    f"Cannot undo: message '{message_id}' not found in state"
                )

            # Handle conversation cleanup/restoration
            if undo_data.get("was_new_conversation"):
                # Remove the conversation that was created
                if conversation_id in self.conversations:
                    del self.conversations[conversation_id]
            else:
                # Restore previous conversation metadata
                if conversation_id in self.conversations:
                    prev_meta = undo_data.get("previous_conv_metadata", {})
                    conv = self.conversations[conversation_id]
                    conv.last_message_at = datetime.fromisoformat(
                        prev_meta["last_message_at"]
                    )
                    conv.message_count = prev_meta["message_count"]
                    conv.participant_roles = set(prev_meta["participant_roles"])

            # Restore any message that was removed due to capacity limit
            if "removed_message" in undo_data:
                removed = undo_data["removed_message"]
                restored_message = ChatMessage(
                    message_id=removed["message_id"],
                    conversation_id=removed["conversation_id"],
                    role=removed["role"],
                    content=removed["content"],
                    timestamp=datetime.fromisoformat(removed["timestamp"]),
                    metadata=removed["metadata"],
                )
                self.messages.append(restored_message)
                self.messages.sort(key=lambda m: (m.timestamp, m.message_id))

        elif action == "restore_message":
            # Restore a message that was deleted
            message_data = undo_data.get("message")
            if not message_data:
                raise ValueError("Undo data missing 'message' field")

            restored_message = ChatMessage(
                message_id=message_data["message_id"],
                conversation_id=message_data["conversation_id"],
                role=message_data["role"],
                content=message_data["content"],
                timestamp=datetime.fromisoformat(message_data["timestamp"]),
                metadata=message_data["metadata"],
            )
            self.messages.append(restored_message)
            self.messages.sort(key=lambda m: (m.timestamp, m.message_id))

            # Update conversation metadata
            conv_id = message_data["conversation_id"]
            if conv_id in self.conversations:
                conv = self.conversations[conv_id]
                conv.message_count += 1
                # Update last_message_at if this was the most recent
                msg_time = datetime.fromisoformat(message_data["timestamp"])
                if msg_time > conv.last_message_at:
                    conv.last_message_at = msg_time

        elif action == "restore_conversation":
            # Restore a cleared conversation
            conversation_id = undo_data.get("conversation_id")
            if not conversation_id:
                raise ValueError("Undo data missing 'conversation_id' field")

            # Restore all cleared messages
            cleared_messages = undo_data.get("cleared_messages", [])
            for msg_data in cleared_messages:
                restored_message = ChatMessage(
                    message_id=msg_data["message_id"],
                    conversation_id=msg_data["conversation_id"],
                    role=msg_data["role"],
                    content=msg_data["content"],
                    timestamp=datetime.fromisoformat(msg_data["timestamp"]),
                    metadata=msg_data["metadata"],
                )
                self.messages.append(restored_message)

            self.messages.sort(key=lambda m: (m.timestamp, m.message_id))

            # Restore conversation metadata
            conv_metadata = undo_data.get("conv_metadata")
            if conv_metadata:
                self.conversations[conversation_id] = ConversationMetadata(
                    conversation_id=conv_metadata["conversation_id"],
                    created_at=datetime.fromisoformat(conv_metadata["created_at"]),
                    last_message_at=datetime.fromisoformat(conv_metadata["last_message_at"]),
                    message_count=conv_metadata["message_count"],
                    participant_roles=set(conv_metadata["participant_roles"]),
                )

        else:
            raise ValueError(f"Unknown undo action: {action}")

        # Restore state-level metadata
        self.update_count = undo_data["state_previous_update_count"]
        self.last_updated = datetime.fromisoformat(
            undo_data["state_previous_last_updated"]
        )
