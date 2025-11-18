"""SMS/RCS input model for text messaging operations."""

from datetime import datetime
from typing import Any, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from models.base_input import ModalityInput


SMSAction = Literal[
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

    This input type handles all SMS-related actions through an action discriminator.
    Different actions require different data payloads specified in optional fields.

    Args:
        modality_type: Always "sms".
        timestamp: When this input event occurs (simulator time).
        input_id: Unique identifier for this input (auto-generated UUID).
        action: Type of SMS action being performed.
        message_data: Data for send_message, receive_message actions.
        delivery_update_data: Data for update_delivery_status action.
        reaction_data: Data for add_reaction, remove_reaction actions.
        edit_data: Data for edit_message action.
        delete_data: Data for delete_message action.
        group_data: Data for create_group, update_group actions.
        participant_data: Data for add_participant, remove_participant actions.
        conversation_update_data: Data for update_conversation action.
    """

    modality_type: Literal["sms"] = Field(
        default="sms",
        description="Always 'sms'",
    )
    action: SMSAction = Field(description="Type of SMS action being performed")

    message_data: Optional[dict[str, Any]] = Field(
        default=None,
        description="Data for message send/receive actions",
    )
    delivery_update_data: Optional[dict[str, Any]] = Field(
        default=None,
        description="Data for delivery status updates",
    )
    reaction_data: Optional[dict[str, Any]] = Field(
        default=None,
        description="Data for reaction actions",
    )
    edit_data: Optional[dict[str, Any]] = Field(
        default=None,
        description="Data for message editing",
    )
    delete_data: Optional[dict[str, Any]] = Field(
        default=None,
        description="Data for message deletion",
    )
    group_data: Optional[dict[str, Any]] = Field(
        default=None,
        description="Data for group operations",
    )
    participant_data: Optional[dict[str, Any]] = Field(
        default=None,
        description="Data for participant operations",
    )
    conversation_update_data: Optional[dict[str, Any]] = Field(
        default=None,
        description="Data for conversation state changes",
    )

    def validate_input(self) -> None:
        """Validate that required data for the action is present and well-formed.

        Raises:
            ValueError: If required data is missing or malformed for the action.
        """
        if self.action in ["send_message", "receive_message"]:
            self._validate_message_data()
        elif self.action == "update_delivery_status":
            self._validate_delivery_update_data()
        elif self.action in ["add_reaction", "remove_reaction"]:
            self._validate_reaction_data()
        elif self.action == "edit_message":
            self._validate_edit_data()
        elif self.action == "delete_message":
            self._validate_delete_data()
        elif self.action in ["create_group", "update_group"]:
            self._validate_group_data()
        elif self.action in ["add_participant", "remove_participant", "leave_group"]:
            self._validate_participant_data()
        elif self.action == "update_conversation":
            self._validate_conversation_update_data()

    def _validate_message_data(self) -> None:
        """Validate message_data for send/receive actions."""
        if not self.message_data:
            raise ValueError(
                f"message_data is required for action '{self.action}'"
            )

        required_fields = ["from_number", "to_numbers", "body"]
        for field in required_fields:
            if field not in self.message_data:
                raise ValueError(
                    f"message_data.{field} is required for action '{self.action}'"
                )

        if not isinstance(self.message_data["to_numbers"], list):
            raise ValueError("message_data.to_numbers must be a list")

        if not self.message_data["to_numbers"]:
            raise ValueError("message_data.to_numbers cannot be empty")

        message_type = self.message_data.get("message_type", "sms")
        if message_type not in ["sms", "rcs"]:
            raise ValueError(
                f"message_data.message_type must be 'sms' or 'rcs', got '{message_type}'"
            )

    def _validate_delivery_update_data(self) -> None:
        """Validate delivery_update_data for status updates."""
        if not self.delivery_update_data:
            raise ValueError(
                "delivery_update_data is required for action 'update_delivery_status'"
            )

        required_fields = ["message_id", "new_status"]
        for field in required_fields:
            if field not in self.delivery_update_data:
                raise ValueError(
                    f"delivery_update_data.{field} is required"
                )

        valid_statuses = ["delivered", "read", "failed"]
        new_status = self.delivery_update_data["new_status"]
        if new_status not in valid_statuses:
            raise ValueError(
                f"delivery_update_data.new_status must be one of {valid_statuses}, got '{new_status}'"
            )

    def _validate_reaction_data(self) -> None:
        """Validate reaction_data for add/remove reaction actions."""
        if not self.reaction_data:
            raise ValueError(
                f"reaction_data is required for action '{self.action}'"
            )

        required_fields = ["message_id", "phone_number"]
        for field in required_fields:
            if field not in self.reaction_data:
                raise ValueError(
                    f"reaction_data.{field} is required"
                )

        if self.action == "add_reaction" and "emoji" not in self.reaction_data:
            raise ValueError(
                "reaction_data.emoji is required for action 'add_reaction'"
            )

        if self.action == "remove_reaction" and "reaction_id" not in self.reaction_data:
            raise ValueError(
                "reaction_data.reaction_id is required for action 'remove_reaction'"
            )

    def _validate_edit_data(self) -> None:
        """Validate edit_data for message editing."""
        if not self.edit_data:
            raise ValueError(
                "edit_data is required for action 'edit_message'"
            )

        required_fields = ["message_id", "new_body"]
        for field in required_fields:
            if field not in self.edit_data:
                raise ValueError(f"edit_data.{field} is required")

    def _validate_delete_data(self) -> None:
        """Validate delete_data for message deletion."""
        if not self.delete_data:
            raise ValueError(
                "delete_data is required for action 'delete_message'"
            )

        if "message_id" not in self.delete_data:
            raise ValueError("delete_data.message_id is required")

    def _validate_group_data(self) -> None:
        """Validate group_data for group creation/update."""
        if not self.group_data:
            raise ValueError(
                f"group_data is required for action '{self.action}'"
            )

        if self.action == "create_group":
            required_fields = ["creator_number", "participant_numbers"]
            for field in required_fields:
                if field not in self.group_data:
                    raise ValueError(f"group_data.{field} is required for create_group")

            if not isinstance(self.group_data["participant_numbers"], list):
                raise ValueError("group_data.participant_numbers must be a list")

            if len(self.group_data["participant_numbers"]) < 2:
                raise ValueError(
                    "group_data.participant_numbers must have at least 2 participants"
                )

        elif self.action == "update_group":
            if "thread_id" not in self.group_data:
                raise ValueError("group_data.thread_id is required for update_group")

    def _validate_participant_data(self) -> None:
        """Validate participant_data for participant operations."""
        if not self.participant_data:
            raise ValueError(
                f"participant_data is required for action '{self.action}'"
            )

        required_fields = ["thread_id"]
        if self.action in ["add_participant", "remove_participant"]:
            required_fields.append("phone_number")

        for field in required_fields:
            if field not in self.participant_data:
                raise ValueError(
                    f"participant_data.{field} is required for action '{self.action}'"
                )

    def _validate_conversation_update_data(self) -> None:
        """Validate conversation_update_data for conversation updates."""
        if not self.conversation_update_data:
            raise ValueError(
                "conversation_update_data is required for action 'update_conversation'"
            )

        if "thread_id" not in self.conversation_update_data:
            raise ValueError("conversation_update_data.thread_id is required")

        has_update = any(
            key in self.conversation_update_data
            for key in ["pin", "mute", "archive", "mark_all_read", "draft_message"]
        )
        if not has_update:
            raise ValueError(
                "conversation_update_data must specify at least one update "
                "(pin, mute, archive, mark_all_read, or draft_message)"
            )

    def get_affected_entities(self) -> list[str]:
        """Return thread_id(s) or message_id(s) affected by this input.

        Returns:
            List of entity identifiers affected by this input.
        """
        if self.action in ["send_message", "receive_message"]:
            if self.message_data and "thread_id" in self.message_data:
                return [self.message_data["thread_id"]]
            return ["new_conversation"]

        elif self.action == "update_delivery_status":
            if self.delivery_update_data:
                return [self.delivery_update_data["message_id"]]

        elif self.action in ["add_reaction", "remove_reaction"]:
            if self.reaction_data:
                return [self.reaction_data["message_id"]]

        elif self.action in ["edit_message", "delete_message"]:
            data = self.edit_data if self.action == "edit_message" else self.delete_data
            if data:
                return [data["message_id"]]

        elif self.action in ["create_group", "update_group"]:
            if self.group_data and "thread_id" in self.group_data:
                return [self.group_data["thread_id"]]
            return ["new_group"]

        elif self.action in ["add_participant", "remove_participant", "leave_group", "update_conversation"]:
            data = self.participant_data if self.action in ["add_participant", "remove_participant", "leave_group"] else self.conversation_update_data
            if data and "thread_id" in data:
                return [data["thread_id"]]

        return []

    def get_summary(self) -> str:
        """Return human-readable summary of this SMS input.

        Returns:
            Brief, human-readable description for logging/UI display.
        """
        if self.action == "send_message" and self.message_data:
            from_num = self.message_data.get("from_number", "unknown")
            to_nums = self.message_data.get("to_numbers", [])
            body = self.message_data.get("body", "")
            body_preview = body[:50] + "..." if len(body) > 50 else body
            to_display = to_nums[0] if len(to_nums) == 1 else f"{len(to_nums)} recipients"
            return f"Send SMS from {from_num} to {to_display}: '{body_preview}'"

        elif self.action == "receive_message" and self.message_data:
            from_num = self.message_data.get("from_number", "unknown")
            body = self.message_data.get("body", "")
            body_preview = body[:50] + "..." if len(body) > 50 else body
            return f"Receive SMS from {from_num}: '{body_preview}'"

        elif self.action == "update_delivery_status" and self.delivery_update_data:
            status = self.delivery_update_data.get("new_status", "unknown")
            return f"Update message delivery status to '{status}'"

        elif self.action == "add_reaction" and self.reaction_data:
            emoji = self.reaction_data.get("emoji", "?")
            return f"Add reaction '{emoji}' to message"

        elif self.action == "remove_reaction":
            return "Remove reaction from message"

        elif self.action == "edit_message" and self.edit_data:
            new_body = self.edit_data.get("new_body", "")
            preview = new_body[:50] + "..." if len(new_body) > 50 else new_body
            return f"Edit message to: '{preview}'"

        elif self.action == "delete_message":
            return "Delete message"

        elif self.action == "create_group" and self.group_data:
            group_name = self.group_data.get("group_name", "Unnamed Group")
            participants = self.group_data.get("participant_numbers", [])
            return f"Create group '{group_name}' with {len(participants)} participants"

        elif self.action == "update_group":
            return "Update group settings"

        elif self.action == "add_participant":
            return "Add participant to group"

        elif self.action == "remove_participant":
            return "Remove participant from group"

        elif self.action == "leave_group":
            return "Leave group conversation"

        elif self.action == "update_conversation":
            return "Update conversation settings"

        return f"SMS action: {self.action}"

    def should_merge_with(self, other: "ModalityInput") -> bool:
        """Determine if this input should be merged with another.

        SMS events are discrete and should not be merged.

        Args:
            other: Another input of the same type.

        Returns:
            Always False for SMS inputs.
        """
        return False
