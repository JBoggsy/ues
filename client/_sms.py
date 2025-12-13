"""SMS/RCS modality sub-client for the UES API.

This module provides SMSClient and AsyncSMSClient for interacting with
the SMS/RCS modality endpoints (/sms/*).

This is an internal module. Import from `client` instead.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field

from client._base import AsyncBaseClient, BaseClient
from client.models import ModalityActionResponse

if TYPE_CHECKING:
    from client._http import AsyncHTTPClient, HTTPClient


# Response models for SMS endpoints


class MessageAttachment(BaseModel):
    """Represents a message attachment.
    
    Attributes:
        filename: Original filename.
        size: File size in bytes.
        mime_type: MIME type of the attachment.
        thumbnail_url: Optional thumbnail URL for images/videos.
        duration: Optional duration in seconds for audio/video.
    """

    filename: str
    size: int
    mime_type: str
    thumbnail_url: str | None = None
    duration: int | None = None


class MessageReaction(BaseModel):
    """Represents a reaction to a message.
    
    Attributes:
        emoji: The emoji character(s) used for the reaction.
        phone_number: Phone number of the person who reacted.
        timestamp: When the reaction was added.
    """

    emoji: str
    phone_number: str
    timestamp: datetime


class SMSMessage(BaseModel):
    """Represents an SMS/RCS message.
    
    Attributes:
        message_id: Unique message identifier.
        thread_id: Conversation/thread identifier.
        from_number: Sender phone number.
        to_numbers: Recipient phone number(s).
        body: Message text content.
        message_type: "sms" or "rcs".
        direction: "incoming" or "outgoing".
        sent_at: When the message was sent.
        received_at: When the message was received (for incoming).
        is_read: Whether the message has been read.
        read_at: When the message was read.
        delivery_status: Delivery status (sending, sent, delivered, failed, read).
        attachments: Media/file attachments.
        reactions: Reactions to the message (RCS only).
        replied_to_message_id: ID of message being replied to.
        is_deleted: Whether the message is deleted.
        deleted_at: When the message was deleted.
        is_spam: Whether the message is marked as spam.
    """

    message_id: str
    thread_id: str
    from_number: str
    to_numbers: list[str]
    body: str
    message_type: str = "sms"
    direction: str = "outgoing"
    sent_at: datetime
    received_at: datetime | None = None
    is_read: bool = False
    read_at: datetime | None = None
    delivery_status: str = "sent"
    attachments: list[MessageAttachment] = Field(default_factory=list)
    reactions: list[MessageReaction] = Field(default_factory=list)
    replied_to_message_id: str | None = None
    is_deleted: bool = False
    deleted_at: datetime | None = None
    is_spam: bool = False


class GroupParticipant(BaseModel):
    """Represents a participant in a group conversation.
    
    Attributes:
        phone_number: Participant's phone number.
        display_name: Optional display name.
        joined_at: When the participant joined.
        is_admin: Whether the participant is a group admin.
    """

    phone_number: str
    display_name: str | None = None
    joined_at: datetime
    is_admin: bool = False


class SMSConversation(BaseModel):
    """Represents a conversation/thread.
    
    Attributes:
        thread_id: Unique thread identifier.
        conversation_type: Type of conversation ("one_on_one" or "group").
        participants: All participants in conversation (as GroupParticipant objects).
        is_group: Whether this is a group conversation.
        group_name: Name of the group (if group conversation).
        group_photo_url: URL to group icon/photo.
        message_ids: List of message IDs in this conversation.
        created_at: When the conversation started.
        created_by: Phone number of conversation creator (for groups).
        last_message_at: When the last message was sent/received.
        message_count: Total number of messages.
        unread_count: Number of unread messages.
        is_pinned: Whether conversation is pinned to top.
        is_muted: Whether notifications are muted.
        is_archived: Whether the conversation is archived.
        draft_message: Partially composed message text.
    """

    thread_id: str
    conversation_type: str = "one_on_one"
    participants: list[GroupParticipant] = Field(default_factory=list)
    is_group: bool = False
    group_name: str | None = None
    group_photo_url: str | None = None
    message_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    created_by: str | None = None
    last_message_at: datetime
    message_count: int = 0
    unread_count: int = 0
    is_pinned: bool = False
    is_muted: bool = False
    is_archived: bool = False
    draft_message: str | None = None


class SMSStateResponse(BaseModel):
    """Response model for SMS state endpoint.
    
    Attributes:
        modality_type: Always "sms".
        current_time: Current simulator time.
        user_phone_number: The simulated user's phone number.
        messages: All messages indexed by message_id.
        conversations: All conversations indexed by thread_id.
        total_message_count: Total number of messages.
        unread_count: Total number of unread messages.
        total_conversation_count: Total number of conversations.
    """

    modality_type: str = "sms"
    current_time: datetime
    user_phone_number: str
    messages: dict[str, SMSMessage]
    conversations: dict[str, SMSConversation]
    total_message_count: int
    unread_count: int
    total_conversation_count: int


class SMSQueryResponse(BaseModel):
    """Response model for SMS query endpoint.
    
    Attributes:
        modality_type: Always "sms".
        messages: Query results (matching messages).
        total_count: Total number of results matching query.
        returned_count: Number of results returned (after pagination).
        query: Echo of query parameters for debugging.
    """

    modality_type: str = "sms"
    messages: list[SMSMessage]
    total_count: int
    returned_count: int
    query: dict[str, Any]


# Synchronous SMSClient


class SMSClient(BaseClient):
    """Synchronous client for SMS/RCS modality endpoints (/sms/*).
    
    This client provides methods for sending, receiving, and managing
    SMS and RCS messages. Supports text messages, attachments, reactions,
    and group conversations.
    
    Example:
        with UESClient() as client:
            # Send an SMS
            client.sms.send(
                from_number="+15551234567",
                to_numbers=["+15559876543"],
                body="Hello from UES!",
            )
            
            # Get SMS state
            state = client.sms.get_state()
            print(f"Total messages: {state.total_message_count}")
            
            # Query unread messages
            unread = client.sms.query(is_read=False)
            print(f"Found {unread.total_count} unread messages")
    """

    _BASE_PATH = "/sms"

    def get_state(self) -> SMSStateResponse:
        """Get the current SMS state.
        
        Returns a complete snapshot of the SMS system including all messages
        and conversations.
        
        Returns:
            Complete SMS state with all messages and conversations.
        
        Raises:
            APIError: If the request fails.
        """
        data = self._get(f"{self._BASE_PATH}/state")
        return SMSStateResponse(**data)

    def query(
        self,
        thread_id: str | None = None,
        from_number: str | None = None,
        to_number: str | None = None,
        body_contains: str | None = None,
        message_type: Literal["sms", "rcs"] | None = None,
        direction: Literal["incoming", "outgoing"] | None = None,
        is_read: bool | None = None,
        has_attachments: bool | None = None,
        delivery_status: Literal["sending", "sent", "delivered", "failed", "read"] | None = None,
        is_deleted: bool | None = None,
        is_spam: bool | None = None,
        sent_after: datetime | None = None,
        sent_before: datetime | None = None,
        limit: int | None = None,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> SMSQueryResponse:
        """Query SMS messages with filters.
        
        Allows filtering and searching through message data with various criteria
        including thread, sender, recipient, text content, date ranges, etc.
        
        Args:
            thread_id: Filter by conversation/thread ID.
            from_number: Filter by sender phone number.
            to_number: Filter by recipient phone number.
            body_contains: Filter by message text (case-insensitive).
            message_type: Filter by message type ("sms" or "rcs").
            direction: Filter by direction ("incoming" or "outgoing").
            is_read: Filter by read status.
            has_attachments: Filter by attachment presence.
            delivery_status: Filter by delivery status.
            is_deleted: Filter by deleted status.
            is_spam: Filter by spam status.
            sent_after: Filter by sent date (inclusive).
            sent_before: Filter by sent date (inclusive).
            limit: Maximum number of results to return.
            offset: Number of results to skip (for pagination).
            sort_by: Field to sort by (e.g., 'sent_at', 'from_number').
            sort_order: Sort direction ("asc" or "desc").
        
        Returns:
            Filtered message results with counts.
        
        Raises:
            ValidationError: If query parameters are invalid.
            APIError: If the request fails.
        """
        # Build the request body, excluding None values
        request_data: dict[str, Any] = {}
        
        if thread_id is not None:
            request_data["thread_id"] = thread_id
        if from_number is not None:
            request_data["from_number"] = from_number
        if to_number is not None:
            request_data["to_number"] = to_number
        if body_contains is not None:
            request_data["body_contains"] = body_contains
        if message_type is not None:
            request_data["message_type"] = message_type
        if direction is not None:
            request_data["direction"] = direction
        if is_read is not None:
            request_data["is_read"] = is_read
        if has_attachments is not None:
            request_data["has_attachments"] = has_attachments
        if delivery_status is not None:
            request_data["delivery_status"] = delivery_status
        if is_deleted is not None:
            request_data["is_deleted"] = is_deleted
        if is_spam is not None:
            request_data["is_spam"] = is_spam
        if sent_after is not None:
            request_data["sent_after"] = sent_after.isoformat()
        if sent_before is not None:
            request_data["sent_before"] = sent_before.isoformat()
        if limit is not None:
            request_data["limit"] = limit
        if offset != 0:
            request_data["offset"] = offset
        if sort_by is not None:
            request_data["sort_by"] = sort_by
        if sort_order != "desc":
            request_data["sort_order"] = sort_order
        
        data = self._post(f"{self._BASE_PATH}/query", json=request_data)
        return SMSQueryResponse(**data)

    def send(
        self,
        from_number: str,
        to_numbers: list[str],
        body: str,
        message_type: Literal["sms", "rcs"] = "sms",
        attachments: list[dict[str, Any]] | None = None,
        replied_to_message_id: str | None = None,
    ) -> ModalityActionResponse:
        """Send a new SMS/RCS message.
        
        Creates an immediate event to send a message from the user to specified
        recipient(s) with text content and optional attachments.
        
        Args:
            from_number: Sender phone number.
            to_numbers: Recipient phone number(s).
            body: Message text content.
            message_type: "sms" or "rcs" (default: "sms").
            attachments: Media/file attachments. Each attachment should be a dict
                with 'filename', 'size', 'mime_type', and optional 'thumbnail_url'
                and 'duration' keys.
            replied_to_message_id: Optional ID of message being replied to.
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If request parameters are invalid.
            APIError: If the request fails.
        """
        request_data: dict[str, Any] = {
            "from_number": from_number,
            "to_numbers": to_numbers,
            "body": body,
            "message_type": message_type,
        }
        
        if attachments is not None:
            request_data["attachments"] = attachments
        if replied_to_message_id is not None:
            request_data["replied_to_message_id"] = replied_to_message_id
        
        data = self._post(f"{self._BASE_PATH}/send", json=request_data)
        return ModalityActionResponse(**data)

    def receive(
        self,
        from_number: str,
        to_numbers: list[str],
        body: str,
        message_type: Literal["sms", "rcs"] = "sms",
        attachments: list[dict[str, Any]] | None = None,
        replied_to_message_id: str | None = None,
        sent_at: datetime | None = None,
    ) -> ModalityActionResponse:
        """Simulate receiving an SMS/RCS message.
        
        Creates an immediate event to receive a message from an external sender
        into the user's message inbox.
        
        Args:
            from_number: Sender phone number.
            to_numbers: Recipient phone number(s).
            body: Message text content.
            message_type: "sms" or "rcs" (default: "sms").
            attachments: Media/file attachments. Each attachment should be a dict
                with 'filename', 'size', 'mime_type', and optional 'thumbnail_url'
                and 'duration' keys.
            replied_to_message_id: Optional ID of message being replied to.
            sent_at: When message was originally sent (defaults to current time).
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If request parameters are invalid.
            APIError: If the request fails.
        """
        request_data: dict[str, Any] = {
            "from_number": from_number,
            "to_numbers": to_numbers,
            "body": body,
            "message_type": message_type,
        }
        
        if attachments is not None:
            request_data["attachments"] = attachments
        if replied_to_message_id is not None:
            request_data["replied_to_message_id"] = replied_to_message_id
        if sent_at is not None:
            request_data["sent_at"] = sent_at.isoformat()
        
        data = self._post(f"{self._BASE_PATH}/receive", json=request_data)
        return ModalityActionResponse(**data)

    def read(self, message_ids: list[str]) -> ModalityActionResponse:
        """Mark messages as read.
        
        Creates an immediate event to mark one or more messages as read.
        
        Args:
            message_ids: Message IDs to mark as read.
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If message_ids is empty.
            APIError: If the request fails.
        """
        data = self._post(
            f"{self._BASE_PATH}/read",
            json={"message_ids": message_ids},
        )
        return ModalityActionResponse(**data)

    def unread(self, message_ids: list[str]) -> ModalityActionResponse:
        """Mark messages as unread.
        
        Creates an immediate event to mark one or more messages as unread.
        
        Args:
            message_ids: Message IDs to mark as unread.
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If message_ids is empty.
            APIError: If the request fails.
        """
        data = self._post(
            f"{self._BASE_PATH}/unread",
            json={"message_ids": message_ids},
        )
        return ModalityActionResponse(**data)

    def delete(self, message_ids: list[str]) -> ModalityActionResponse:
        """Delete messages.
        
        Creates an immediate event to delete one or more messages.
        
        Args:
            message_ids: Message IDs to delete.
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If message_ids is empty.
            APIError: If the request fails.
        """
        data = self._post(
            f"{self._BASE_PATH}/delete",
            json={"message_ids": message_ids},
        )
        return ModalityActionResponse(**data)

    def react(
        self,
        message_id: str,
        phone_number: str,
        emoji: str,
    ) -> ModalityActionResponse:
        """Add a reaction to a message.
        
        Creates an immediate event to add an emoji reaction to a message.
        Note: Reactions are only supported for RCS messages.
        
        Args:
            message_id: Message ID to react to.
            phone_number: Phone number of person reacting.
            emoji: Emoji character(s) for the reaction.
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If parameters are invalid.
            APIError: If the request fails.
        """
        data = self._post(
            f"{self._BASE_PATH}/react",
            json={
                "message_id": message_id,
                "phone_number": phone_number,
                "emoji": emoji,
            },
        )
        return ModalityActionResponse(**data)


# Asynchronous AsyncSMSClient


class AsyncSMSClient(AsyncBaseClient):
    """Asynchronous client for SMS/RCS modality endpoints (/sms/*).
    
    This client provides async methods for sending, receiving, and managing
    SMS and RCS messages. Supports text messages, attachments, reactions,
    and group conversations.
    
    Example:
        async with AsyncUESClient() as client:
            # Send an SMS
            await client.sms.send(
                from_number="+15551234567",
                to_numbers=["+15559876543"],
                body="Hello from UES!",
            )
            
            # Get SMS state
            state = await client.sms.get_state()
            print(f"Total messages: {state.total_message_count}")
            
            # Query unread messages
            unread = await client.sms.query(is_read=False)
            print(f"Found {unread.total_count} unread messages")
    """

    _BASE_PATH = "/sms"

    async def get_state(self) -> SMSStateResponse:
        """Get the current SMS state.
        
        Returns a complete snapshot of the SMS system including all messages
        and conversations.
        
        Returns:
            Complete SMS state with all messages and conversations.
        
        Raises:
            APIError: If the request fails.
        """
        data = await self._get(f"{self._BASE_PATH}/state")
        return SMSStateResponse(**data)

    async def query(
        self,
        thread_id: str | None = None,
        from_number: str | None = None,
        to_number: str | None = None,
        body_contains: str | None = None,
        message_type: Literal["sms", "rcs"] | None = None,
        direction: Literal["incoming", "outgoing"] | None = None,
        is_read: bool | None = None,
        has_attachments: bool | None = None,
        delivery_status: Literal["sending", "sent", "delivered", "failed", "read"] | None = None,
        is_deleted: bool | None = None,
        is_spam: bool | None = None,
        sent_after: datetime | None = None,
        sent_before: datetime | None = None,
        limit: int | None = None,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> SMSQueryResponse:
        """Query SMS messages with filters.
        
        Allows filtering and searching through message data with various criteria
        including thread, sender, recipient, text content, date ranges, etc.
        
        Args:
            thread_id: Filter by conversation/thread ID.
            from_number: Filter by sender phone number.
            to_number: Filter by recipient phone number.
            body_contains: Filter by message text (case-insensitive).
            message_type: Filter by message type ("sms" or "rcs").
            direction: Filter by direction ("incoming" or "outgoing").
            is_read: Filter by read status.
            has_attachments: Filter by attachment presence.
            delivery_status: Filter by delivery status.
            is_deleted: Filter by deleted status.
            is_spam: Filter by spam status.
            sent_after: Filter by sent date (inclusive).
            sent_before: Filter by sent date (inclusive).
            limit: Maximum number of results to return.
            offset: Number of results to skip (for pagination).
            sort_by: Field to sort by (e.g., 'sent_at', 'from_number').
            sort_order: Sort direction ("asc" or "desc").
        
        Returns:
            Filtered message results with counts.
        
        Raises:
            ValidationError: If query parameters are invalid.
            APIError: If the request fails.
        """
        # Build the request body, excluding None values
        request_data: dict[str, Any] = {}
        
        if thread_id is not None:
            request_data["thread_id"] = thread_id
        if from_number is not None:
            request_data["from_number"] = from_number
        if to_number is not None:
            request_data["to_number"] = to_number
        if body_contains is not None:
            request_data["body_contains"] = body_contains
        if message_type is not None:
            request_data["message_type"] = message_type
        if direction is not None:
            request_data["direction"] = direction
        if is_read is not None:
            request_data["is_read"] = is_read
        if has_attachments is not None:
            request_data["has_attachments"] = has_attachments
        if delivery_status is not None:
            request_data["delivery_status"] = delivery_status
        if is_deleted is not None:
            request_data["is_deleted"] = is_deleted
        if is_spam is not None:
            request_data["is_spam"] = is_spam
        if sent_after is not None:
            request_data["sent_after"] = sent_after.isoformat()
        if sent_before is not None:
            request_data["sent_before"] = sent_before.isoformat()
        if limit is not None:
            request_data["limit"] = limit
        if offset != 0:
            request_data["offset"] = offset
        if sort_by is not None:
            request_data["sort_by"] = sort_by
        if sort_order != "desc":
            request_data["sort_order"] = sort_order
        
        data = await self._post(f"{self._BASE_PATH}/query", json=request_data)
        return SMSQueryResponse(**data)

    async def send(
        self,
        from_number: str,
        to_numbers: list[str],
        body: str,
        message_type: Literal["sms", "rcs"] = "sms",
        attachments: list[dict[str, Any]] | None = None,
        replied_to_message_id: str | None = None,
    ) -> ModalityActionResponse:
        """Send a new SMS/RCS message.
        
        Creates an immediate event to send a message from the user to specified
        recipient(s) with text content and optional attachments.
        
        Args:
            from_number: Sender phone number.
            to_numbers: Recipient phone number(s).
            body: Message text content.
            message_type: "sms" or "rcs" (default: "sms").
            attachments: Media/file attachments. Each attachment should be a dict
                with 'filename', 'size', 'mime_type', and optional 'thumbnail_url'
                and 'duration' keys.
            replied_to_message_id: Optional ID of message being replied to.
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If request parameters are invalid.
            APIError: If the request fails.
        """
        request_data: dict[str, Any] = {
            "from_number": from_number,
            "to_numbers": to_numbers,
            "body": body,
            "message_type": message_type,
        }
        
        if attachments is not None:
            request_data["attachments"] = attachments
        if replied_to_message_id is not None:
            request_data["replied_to_message_id"] = replied_to_message_id
        
        data = await self._post(f"{self._BASE_PATH}/send", json=request_data)
        return ModalityActionResponse(**data)

    async def receive(
        self,
        from_number: str,
        to_numbers: list[str],
        body: str,
        message_type: Literal["sms", "rcs"] = "sms",
        attachments: list[dict[str, Any]] | None = None,
        replied_to_message_id: str | None = None,
        sent_at: datetime | None = None,
    ) -> ModalityActionResponse:
        """Simulate receiving an SMS/RCS message.
        
        Creates an immediate event to receive a message from an external sender
        into the user's message inbox.
        
        Args:
            from_number: Sender phone number.
            to_numbers: Recipient phone number(s).
            body: Message text content.
            message_type: "sms" or "rcs" (default: "sms").
            attachments: Media/file attachments. Each attachment should be a dict
                with 'filename', 'size', 'mime_type', and optional 'thumbnail_url'
                and 'duration' keys.
            replied_to_message_id: Optional ID of message being replied to.
            sent_at: When message was originally sent (defaults to current time).
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If request parameters are invalid.
            APIError: If the request fails.
        """
        request_data: dict[str, Any] = {
            "from_number": from_number,
            "to_numbers": to_numbers,
            "body": body,
            "message_type": message_type,
        }
        
        if attachments is not None:
            request_data["attachments"] = attachments
        if replied_to_message_id is not None:
            request_data["replied_to_message_id"] = replied_to_message_id
        if sent_at is not None:
            request_data["sent_at"] = sent_at.isoformat()
        
        data = await self._post(f"{self._BASE_PATH}/receive", json=request_data)
        return ModalityActionResponse(**data)

    async def read(self, message_ids: list[str]) -> ModalityActionResponse:
        """Mark messages as read.
        
        Creates an immediate event to mark one or more messages as read.
        
        Args:
            message_ids: Message IDs to mark as read.
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If message_ids is empty.
            APIError: If the request fails.
        """
        data = await self._post(
            f"{self._BASE_PATH}/read",
            json={"message_ids": message_ids},
        )
        return ModalityActionResponse(**data)

    async def unread(self, message_ids: list[str]) -> ModalityActionResponse:
        """Mark messages as unread.
        
        Creates an immediate event to mark one or more messages as unread.
        
        Args:
            message_ids: Message IDs to mark as unread.
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If message_ids is empty.
            APIError: If the request fails.
        """
        data = await self._post(
            f"{self._BASE_PATH}/unread",
            json={"message_ids": message_ids},
        )
        return ModalityActionResponse(**data)

    async def delete(self, message_ids: list[str]) -> ModalityActionResponse:
        """Delete messages.
        
        Creates an immediate event to delete one or more messages.
        
        Args:
            message_ids: Message IDs to delete.
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If message_ids is empty.
            APIError: If the request fails.
        """
        data = await self._post(
            f"{self._BASE_PATH}/delete",
            json={"message_ids": message_ids},
        )
        return ModalityActionResponse(**data)

    async def react(
        self,
        message_id: str,
        phone_number: str,
        emoji: str,
    ) -> ModalityActionResponse:
        """Add a reaction to a message.
        
        Creates an immediate event to add an emoji reaction to a message.
        Note: Reactions are only supported for RCS messages.
        
        Args:
            message_id: Message ID to react to.
            phone_number: Phone number of person reacting.
            emoji: Emoji character(s) for the reaction.
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If parameters are invalid.
            APIError: If the request fails.
        """
        data = await self._post(
            f"{self._BASE_PATH}/react",
            json={
                "message_id": message_id,
                "phone_number": phone_number,
                "emoji": emoji,
            },
        )
        return ModalityActionResponse(**data)
