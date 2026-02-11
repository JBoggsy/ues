"""SMS/RCS input model for text messaging operations."""

from datetime import datetime
from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from ues.models.base_input import ModalityInput


SMSOperation = Literal[
    "send_message",
    "receive_message",
    "update_delivery_status",
    "add_reaction",
    "remove_reaction",
    "edit_message",
    "delete_message",
    "create_group",
    "update_group",
    "add_participant",
    "remove_participant",
    "leave_group",
    "update_conversation",
]

MessageType = Literal["sms", "rcs"]
DeliveryStatus = Literal["sending", "sent", "delivered", "failed", "read"]


class MessageAttachmentData(BaseModel):
    """Represents media or file attachment metadata for input.

    Args:
        filename: Original filename.
        size: File size in bytes.
        mime_type: MIME type (e.g., "image/jpeg", "video/mp4").
        thumbnail_url: Optional thumbnail for images/videos.
        duration: Optional duration in seconds for audio/video.
    """

    filename: str = Field(description="Original filename")
    size: int = Field(description="File size in bytes")
    mime_type: str = Field(description="MIME type")
    thumbnail_url: Optional[str] = Field(
        default=None,
        description="Thumbnail URL for images/videos",
    )
    duration: Optional[int] = Field(
        default=None,
        description="Duration in seconds for audio/video",
    )


class SMSInput(ModalityInput):
    """Event payload for SMS/RCS operations.

    This input type handles all SMS-related operations through an operation discriminator.
    Different operations require different subsets of the typed fields below.

    Args:
        modality_type: Always "sms".
        timestamp: When this input event occurs (simulator time).
        input_id: Unique identifier for this input (auto-generated UUID).
        operation: Type of SMS operation being performed.
        from_number: Sender phone number (send_message, receive_message).
        to_numbers: Recipient phone numbers (send_message, receive_message).
        body: Message text content (send_message, receive_message).
        message_type: "sms" or "rcs" (send_message, receive_message).
        attachments: Media/file attachments (send_message, receive_message).
        thread_id: Conversation identifier (various operations).
        replied_to_message_id: Message being replied to (send_message, receive_message).
        message_id: Target message identifier (various operations).
        new_status: Delivery status to set (update_delivery_status).
        delivered_at: Delivery timestamp (update_delivery_status).
        read_at: Read timestamp (update_delivery_status).
        phone_number: Phone number for participant/reaction (various operations).
        emoji: Reaction emoji (add_reaction).
        reaction_id: Reaction to remove (remove_reaction).
        new_body: Edited message content (edit_message).
        delete_for_everyone: Delete for all participants (delete_message).
        group_name: Group conversation name (create_group, update_group).
        creator_number: Group creator phone (create_group).
        participant_numbers: Group participants (create_group).
        group_photo_url: Group photo URL (create_group, update_group).
        added_by: Who added a participant (add_participant).
        removed_by: Who removed a participant (remove_participant).
        is_admin: Participant admin status (add_participant).
        pin: Pin conversation (update_conversation).
        mute: Mute conversation (update_conversation).
        archive: Archive conversation (update_conversation).
        mark_all_read: Mark all messages read (update_conversation).
        draft_message: Draft message content (update_conversation).
        mute_until: Mute until timestamp (update_conversation).
    """

    modality_type: Literal["sms"] = Field(
        default="sms",
        description="Always 'sms'",
    )
    operation: SMSOperation = Field(description="Type of SMS operation being performed")

    # Message fields (send_message, receive_message)
    from_number: Optional[str] = Field(
        default=None,
        description="Sender phone number",
    )
    to_numbers: Optional[list[str]] = Field(
        default=None,
        description="Recipient phone numbers",
    )
    body: Optional[str] = Field(
        default=None,
        description="Message text content",
    )
    message_type: MessageType = Field(
        default="sms",
        description="Message type: 'sms' or 'rcs'",
    )
    attachments: Optional[list[MessageAttachmentData]] = Field(
        default=None,
        description="Media/file attachments",
    )
    thread_id: Optional[str] = Field(
        default=None,
        description="Conversation/thread identifier",
    )
    replied_to_message_id: Optional[str] = Field(
        default=None,
        description="Message ID being replied to",
    )

    # Message identifier (for operations on existing messages)
    message_id: Optional[str] = Field(
        default=None,
        description="Target message identifier",
    )

    # Delivery status fields (update_delivery_status)
    new_status: Optional[DeliveryStatus] = Field(
        default=None,
        description="New delivery status",
    )
    delivered_at: Optional[datetime] = Field(
        default=None,
        description="Delivery timestamp",
    )
    read_at: Optional[datetime] = Field(
        default=None,
        description="Read timestamp",
    )

    # Reaction fields (add_reaction, remove_reaction)
    phone_number: Optional[str] = Field(
        default=None,
        description="Phone number for participant or reaction author",
    )
    emoji: Optional[str] = Field(
        default=None,
        description="Reaction emoji",
    )
    reaction_id: Optional[str] = Field(
        default=None,
        description="Reaction identifier (for removal)",
    )

    # Edit fields (edit_message)
    new_body: Optional[str] = Field(
        default=None,
        description="Edited message content",
    )

    # Delete fields (delete_message)
    delete_for_everyone: bool = Field(
        default=False,
        description="Delete for all participants",
    )

    # Group fields (create_group, update_group)
    group_name: Optional[str] = Field(
        default=None,
        description="Group conversation name",
    )
    creator_number: Optional[str] = Field(
        default=None,
        description="Group creator phone number",
    )
    participant_numbers: Optional[list[str]] = Field(
        default=None,
        description="Group participant phone numbers",
    )
    group_photo_url: Optional[str] = Field(
        default=None,
        description="Group photo URL",
    )

    # Participant fields (add_participant, remove_participant)
    added_by: Optional[str] = Field(
        default=None,
        description="Phone number of user who added participant",
    )
    removed_by: Optional[str] = Field(
        default=None,
        description="Phone number of user who removed participant",
    )
    is_admin: bool = Field(
        default=False,
        description="Participant admin status",
    )

    # Conversation update fields (update_conversation)
    pin: Optional[bool] = Field(
        default=None,
        description="Pin/unpin conversation",
    )
    mute: Optional[bool] = Field(
        default=None,
        description="Mute/unmute conversation",
    )
    archive: Optional[bool] = Field(
        default=None,
        description="Archive/unarchive conversation",
    )
    mark_all_read: Optional[bool] = Field(
        default=None,
        description="Mark all messages as read",
    )
    draft_message: Optional[str] = Field(
        default=None,
        description="Draft message content",
    )
    mute_until: Optional[datetime] = Field(
        default=None,
        description="Mute until timestamp",
    )

    def validate_input(self) -> None:
        """Validate that required data for the operation is present and well-formed.

        Raises:
            ValueError: If required data is missing or malformed for the operation.
        """
        if self.operation in ["send_message", "receive_message"]:
            self._validate_message_fields()
        elif self.operation == "update_delivery_status":
            self._validate_delivery_update_fields()
        elif self.operation in ["add_reaction", "remove_reaction"]:
            self._validate_reaction_fields()
        elif self.operation == "edit_message":
            self._validate_edit_fields()
        elif self.operation == "delete_message":
            self._validate_delete_fields()
        elif self.operation in ["create_group", "update_group"]:
            self._validate_group_fields()
        elif self.operation in ["add_participant", "remove_participant", "leave_group"]:
            self._validate_participant_fields()
        elif self.operation == "update_conversation":
            self._validate_conversation_update_fields()

    def _validate_message_fields(self) -> None:
        """Validate fields for send/receive operations."""
        if self.from_number is None:
            raise ValueError(
                f"from_number is required for operation '{self.operation}'"
            )
        if self.to_numbers is None:
            raise ValueError(
                f"to_numbers is required for operation '{self.operation}'"
            )
        if self.body is None:
            raise ValueError(
                f"body is required for operation '{self.operation}'"
            )

        if not self.to_numbers:
            raise ValueError("to_numbers cannot be empty")

    def _validate_delivery_update_fields(self) -> None:
        """Validate fields for status updates."""
        if self.message_id is None:
            raise ValueError(
                "message_id is required for operation 'update_delivery_status'"
            )
        if self.new_status is None:
            raise ValueError(
                "new_status is required for operation 'update_delivery_status'"
            )

        valid_statuses = ["delivered", "read", "failed"]
        if self.new_status not in valid_statuses:
            raise ValueError(
                f"new_status must be one of {valid_statuses}, got '{self.new_status}'"
            )

    def _validate_reaction_fields(self) -> None:
        """Validate fields for add/remove reaction operations."""
        if self.message_id is None:
            raise ValueError("message_id is required for reaction operations")
        if self.phone_number is None:
            raise ValueError("phone_number is required for reaction operations")

        if self.operation == "add_reaction" and self.emoji is None:
            raise ValueError(
                "emoji is required for operation 'add_reaction'"
            )

        if self.operation == "remove_reaction" and self.reaction_id is None:
            raise ValueError(
                "reaction_id is required for operation 'remove_reaction'"
            )

    def _validate_edit_fields(self) -> None:
        """Validate fields for message editing."""
        if self.message_id is None:
            raise ValueError("message_id is required for operation 'edit_message'")
        if self.new_body is None:
            raise ValueError("new_body is required for operation 'edit_message'")

    def _validate_delete_fields(self) -> None:
        """Validate fields for message deletion."""
        if self.message_id is None:
            raise ValueError("message_id is required for operation 'delete_message'")

    def _validate_group_fields(self) -> None:
        """Validate fields for group creation/update."""
        if self.operation == "create_group":
            if self.creator_number is None:
                raise ValueError("creator_number is required for create_group")
            if self.participant_numbers is None:
                raise ValueError("participant_numbers is required for create_group")

            if len(self.participant_numbers) < 2:
                raise ValueError(
                    "participant_numbers must have at least 2 participants"
                )

        elif self.operation == "update_group":
            if self.thread_id is None:
                raise ValueError("thread_id is required for update_group")

    def _validate_participant_fields(self) -> None:
        """Validate fields for participant operations."""
        if self.thread_id is None:
            raise ValueError(
                f"thread_id is required for operation '{self.operation}'"
            )

        if self.operation in ["add_participant", "remove_participant"]:
            if self.phone_number is None:
                raise ValueError(
                    f"phone_number is required for operation '{self.operation}'"
                )

    def _validate_conversation_update_fields(self) -> None:
        """Validate fields for conversation updates."""
        if self.thread_id is None:
            raise ValueError("thread_id is required for operation 'update_conversation'")

        has_update = any([
            self.pin is not None,
            self.mute is not None,
            self.archive is not None,
            self.mark_all_read is not None,
            self.draft_message is not None,
        ])
        if not has_update:
            raise ValueError(
                "update_conversation must specify at least one update "
                "(pin, mute, archive, mark_all_read, or draft_message)"
            )

    def get_affected_entities(self) -> list[str]:
        """Return thread_id(s) or message_id(s) affected by this input.

        Returns:
            List of entity identifiers affected by this input.
        """
        if self.operation in ["send_message", "receive_message"]:
            if self.thread_id:
                return [self.thread_id]
            return ["new_conversation"]

        elif self.operation == "update_delivery_status":
            if self.message_id:
                return [self.message_id]

        elif self.operation in ["add_reaction", "remove_reaction"]:
            if self.message_id:
                return [self.message_id]

        elif self.operation in ["edit_message", "delete_message"]:
            if self.message_id:
                return [self.message_id]

        elif self.operation in ["create_group", "update_group"]:
            if self.thread_id:
                return [self.thread_id]
            return ["new_group"]

        elif self.operation in [
            "add_participant",
            "remove_participant",
            "leave_group",
            "update_conversation",
        ]:
            if self.thread_id:
                return [self.thread_id]

        return []

    def get_summary(self) -> str:
        """Return human-readable summary of this SMS input.

        Returns:
            Brief, human-readable description for logging/UI display.
        """
        if self.operation == "send_message":
            from_num = self.from_number or "unknown"
            to_nums = self.to_numbers or []
            body = self.body or ""
            body_preview = body[:50] + "..." if len(body) > 50 else body
            to_display = to_nums[0] if len(to_nums) == 1 else f"{len(to_nums)} recipients"
            return f"Send SMS from {from_num} to {to_display}: '{body_preview}'"

        elif self.operation == "receive_message":
            from_num = self.from_number or "unknown"
            body = self.body or ""
            body_preview = body[:50] + "..." if len(body) > 50 else body
            return f"Receive SMS from {from_num}: '{body_preview}'"

        elif self.operation == "update_delivery_status":
            status = self.new_status or "unknown"
            return f"Update message delivery status to '{status}'"

        elif self.operation == "add_reaction":
            emoji = self.emoji or "?"
            return f"Add reaction '{emoji}' to message"

        elif self.operation == "remove_reaction":
            return "Remove reaction from message"

        elif self.operation == "edit_message":
            new_body = self.new_body or ""
            preview = new_body[:50] + "..." if len(new_body) > 50 else new_body
            return f"Edit message to: '{preview}'"

        elif self.operation == "delete_message":
            return "Delete message"

        elif self.operation == "create_group":
            name = self.group_name or "Unnamed Group"
            participants = self.participant_numbers or []
            return f"Create group '{name}' with {len(participants)} participants"

        elif self.operation == "update_group":
            return "Update group settings"

        elif self.operation == "add_participant":
            return "Add participant to group"

        elif self.operation == "remove_participant":
            return "Remove participant from group"

        elif self.operation == "leave_group":
            return "Leave group conversation"

        elif self.operation == "update_conversation":
            return "Update conversation settings"

        return f"SMS operation: {self.operation}"

    def should_merge_with(self, other: "ModalityInput") -> bool:
        """Determine if this input should be merged with another.

        SMS events are discrete and should not be merged.

        Args:
            other: Another input of the same type.

        Returns:
            Always False for SMS inputs.
        """
        return False
