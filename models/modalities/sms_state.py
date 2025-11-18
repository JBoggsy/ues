"""SMS/RCS state model for text messaging."""

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from models.base_state import ModalityState
from models.modalities.sms_input import SMSInput


class MessageAttachment(BaseModel):
    """Represents media or file attachments in messages.

    Args:
        filename: Original filename.
        size: File size in bytes.
        mime_type: MIME type (e.g., "image/jpeg", "video/mp4").
        attachment_id: Unique identifier (auto-generated UUID).
        thumbnail_url: Optional thumbnail for images/videos.
        duration: Optional duration in seconds for audio/video.
    """

    filename: str = Field(description="Original filename")
    size: int = Field(description="File size in bytes")
    mime_type: str = Field(description="MIME type")
    attachment_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier",
    )
    thumbnail_url: Optional[str] = Field(
        default=None,
        description="Thumbnail URL for images/videos",
    )
    duration: Optional[int] = Field(
        default=None,
        description="Duration in seconds for audio/video",
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert attachment to dictionary for API responses.

        Returns:
            Dictionary representation of this attachment.
        """
        result = {
            "filename": self.filename,
            "size": self.size,
            "mime_type": self.mime_type,
            "attachment_id": self.attachment_id,
        }
        if self.thumbnail_url:
            result["thumbnail_url"] = self.thumbnail_url
        if self.duration is not None:
            result["duration"] = self.duration
        return result

    def is_image(self) -> bool:
        """Check if attachment is an image.

        Returns:
            True if this is an image attachment.
        """
        return self.mime_type.startswith("image/")

    def is_video(self) -> bool:
        """Check if attachment is a video.

        Returns:
            True if this is a video attachment.
        """
        return self.mime_type.startswith("video/")

    def is_audio(self) -> bool:
        """Check if attachment is audio.

        Returns:
            True if this is an audio attachment.
        """
        return self.mime_type.startswith("audio/")


class MessageReaction(BaseModel):
    """Represents an emoji reaction to a message.

    Args:
        reaction_id: Unique reaction identifier (UUID).
        message_id: ID of message being reacted to.
        phone_number: Phone number of person who reacted.
        emoji: Emoji character(s) used for reaction.
        timestamp: When reaction was added (simulator time).
    """

    reaction_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique reaction identifier",
    )
    message_id: str = Field(description="ID of message being reacted to")
    phone_number: str = Field(description="Phone number of person who reacted")
    emoji: str = Field(description="Emoji character(s) used for reaction")
    timestamp: datetime = Field(description="When reaction was added")

    def to_dict(self) -> dict[str, Any]:
        """Convert reaction to dictionary.

        Returns:
            Dictionary representation of this reaction.
        """
        return {
            "reaction_id": self.reaction_id,
            "message_id": self.message_id,
            "phone_number": self.phone_number,
            "emoji": self.emoji,
            "timestamp": self.timestamp.isoformat(),
        }


class GroupParticipant(BaseModel):
    """Represents a participant in a group conversation.

    Args:
        phone_number: Participant's phone number (immutable identifier).
        is_admin: Whether participant has admin privileges.
        joined_at: When participant joined group (simulator time).
        left_at: When participant left group, if applicable.
    """

    phone_number: str = Field(description="Participant's phone number")
    is_admin: bool = Field(
        default=False,
        description="Whether participant has admin privileges",
    )
    joined_at: datetime = Field(description="When participant joined group")
    left_at: Optional[datetime] = Field(
        default=None,
        description="When participant left group",
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert participant to dictionary.

        Returns:
            Dictionary representation of this participant.
        """
        result = {
            "phone_number": self.phone_number,
            "is_admin": self.is_admin,
            "joined_at": self.joined_at.isoformat(),
        }
        if self.left_at:
            result["left_at"] = self.left_at.isoformat()
        return result

    def is_active(self) -> bool:
        """Check if participant is currently in group.

        Returns:
            True if participant is currently in group (left_at is None).
        """
        return self.left_at is None


class SMSMessage(BaseModel):
    """Represents a complete SMS/RCS message with all metadata.

    Args:
        message_id: Unique message identifier (UUID).
        thread_id: Conversation/thread identifier.
        from_number: Sender phone number.
        to_numbers: Recipient phone number(s).
        body: Message text content.
        attachments: Media/file attachments.
        reactions: Emoji reactions to this message.
        message_type: "sms" or "rcs".
        direction: "incoming" or "outgoing".
        sent_at: When message was sent (simulator time).
        delivered_at: When message was delivered (outgoing messages).
        read_at: When message was read.
        is_read: Read status.
        delivery_status: Message delivery status.
        edited_at: When message was edited (RCS only).
        is_deleted: Whether message has been deleted.
        replied_to_message_id: ID of message this is replying to.
        is_spam: Whether flagged as spam.
    """

    message_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique message identifier",
    )
    thread_id: str = Field(description="Conversation/thread identifier")
    from_number: str = Field(description="Sender phone number")
    to_numbers: list[str] = Field(description="Recipient phone number(s)")
    body: str = Field(description="Message text content")
    attachments: list[MessageAttachment] = Field(
        default_factory=list,
        description="Media/file attachments",
    )
    reactions: list[MessageReaction] = Field(
        default_factory=list,
        description="Emoji reactions to this message",
    )
    message_type: str = Field(default="sms", description="Message type")
    direction: str = Field(description="Message direction")
    sent_at: datetime = Field(description="When message was sent")
    delivered_at: Optional[datetime] = Field(
        default=None,
        description="When message was delivered",
    )
    read_at: Optional[datetime] = Field(
        default=None,
        description="When message was read",
    )
    is_read: bool = Field(default=False, description="Read status")
    delivery_status: str = Field(default="sent", description="Delivery status")
    edited_at: Optional[datetime] = Field(
        default=None,
        description="When message was edited",
    )
    is_deleted: bool = Field(default=False, description="Whether message is deleted")
    replied_to_message_id: Optional[str] = Field(
        default=None,
        description="ID of message this replies to",
    )
    is_spam: bool = Field(default=False, description="Whether flagged as spam")

    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary for API responses.

        Returns:
            Dictionary representation of this message.
        """
        result = {
            "message_id": self.message_id,
            "thread_id": self.thread_id,
            "from_number": self.from_number,
            "to_numbers": self.to_numbers,
            "body": self.body,
            "attachments": [att.to_dict() for att in self.attachments],
            "reactions": [react.to_dict() for react in self.reactions],
            "message_type": self.message_type,
            "direction": self.direction,
            "sent_at": self.sent_at.isoformat(),
            "is_read": self.is_read,
            "delivery_status": self.delivery_status,
            "is_deleted": self.is_deleted,
            "is_spam": self.is_spam,
        }
        if self.delivered_at:
            result["delivered_at"] = self.delivered_at.isoformat()
        if self.read_at:
            result["read_at"] = self.read_at.isoformat()
        if self.edited_at:
            result["edited_at"] = self.edited_at.isoformat()
        if self.replied_to_message_id:
            result["replied_to_message_id"] = self.replied_to_message_id
        return result

    def mark_read(self, current_time: datetime) -> None:
        """Set message as read.

        Args:
            current_time: Current simulator time.
        """
        self.is_read = True
        self.read_at = current_time
        if self.direction == "outgoing":
            self.delivery_status = "read"

    def mark_unread(self) -> None:
        """Set message as unread."""
        self.is_read = False
        self.read_at = None

    def mark_delivered(self, current_time: datetime) -> None:
        """Update delivery status to delivered.

        Args:
            current_time: Current simulator time.
        """
        self.delivery_status = "delivered"
        self.delivered_at = current_time

    def mark_failed(self) -> None:
        """Update delivery status to failed."""
        self.delivery_status = "failed"

    def add_reaction(self, phone_number: str, emoji: str, current_time: datetime) -> None:
        """Add emoji reaction to message.

        Args:
            phone_number: Phone number of person reacting.
            emoji: Emoji character(s).
            current_time: Current simulator time.
        """
        reaction = MessageReaction(
            message_id=self.message_id,
            phone_number=phone_number,
            emoji=emoji,
            timestamp=current_time,
        )
        self.reactions.append(reaction)

    def remove_reaction(self, reaction_id: str) -> None:
        """Remove specific reaction from message.

        Args:
            reaction_id: ID of reaction to remove.
        """
        self.reactions = [r for r in self.reactions if r.reaction_id != reaction_id]

    def edit_body(self, new_body: str, current_time: datetime) -> None:
        """Edit message text (RCS only).

        Args:
            new_body: Updated message text.
            current_time: Current simulator time.

        Raises:
            ValueError: If message is not RCS type.
        """
        if self.message_type != "rcs":
            raise ValueError("Can only edit RCS messages")
        self.body = new_body
        self.edited_at = current_time

    def soft_delete(self) -> None:
        """Mark message as deleted without removing from state."""
        self.is_deleted = True


class SMSConversation(BaseModel):
    """Represents a conversation thread (one-on-one or group).

    Args:
        thread_id: Unique conversation identifier (UUID).
        conversation_type: "one_on_one" or "group".
        participants: All participants in conversation.
        group_name: User-defined group name (group conversations only).
        group_photo_url: URL to group icon/photo.
        created_at: When conversation was created (simulator time).
        created_by: Phone number of conversation creator (groups).
        last_message_at: Timestamp of most recent message.
        message_count: Total number of messages in conversation.
        unread_count: Number of unread messages.
        is_pinned: Whether conversation is pinned to top.
        is_muted: Whether notifications are disabled.
        is_archived: Whether conversation is archived.
        draft_message: Partially composed message text.
    """

    thread_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique conversation identifier",
    )
    conversation_type: str = Field(description="Conversation type")
    participants: list[GroupParticipant] = Field(
        description="All participants in conversation"
    )
    group_name: Optional[str] = Field(
        default=None,
        description="User-defined group name",
    )
    group_photo_url: Optional[str] = Field(
        default=None,
        description="URL to group icon/photo",
    )
    created_at: datetime = Field(description="When conversation was created")
    created_by: Optional[str] = Field(
        default=None,
        description="Phone number of conversation creator",
    )
    last_message_at: datetime = Field(description="Timestamp of most recent message")
    message_count: int = Field(
        default=0,
        description="Total number of messages",
    )
    unread_count: int = Field(
        default=0,
        description="Number of unread messages",
    )
    is_pinned: bool = Field(
        default=False,
        description="Whether conversation is pinned",
    )
    is_muted: bool = Field(
        default=False,
        description="Whether notifications are disabled",
    )
    is_archived: bool = Field(
        default=False,
        description="Whether conversation is archived",
    )
    draft_message: Optional[str] = Field(
        default=None,
        description="Partially composed message text",
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert conversation to dictionary for API responses.

        Returns:
            Dictionary representation of this conversation.
        """
        result = {
            "thread_id": self.thread_id,
            "conversation_type": self.conversation_type,
            "participants": [p.to_dict() for p in self.participants],
            "created_at": self.created_at.isoformat(),
            "last_message_at": self.last_message_at.isoformat(),
            "message_count": self.message_count,
            "unread_count": self.unread_count,
            "is_pinned": self.is_pinned,
            "is_muted": self.is_muted,
            "is_archived": self.is_archived,
        }
        if self.group_name:
            result["group_name"] = self.group_name
        if self.group_photo_url:
            result["group_photo_url"] = self.group_photo_url
        if self.created_by:
            result["created_by"] = self.created_by
        if self.draft_message:
            result["draft_message"] = self.draft_message
        return result

    def is_group(self) -> bool:
        """Check if conversation is group chat.

        Returns:
            True if this is a group conversation.
        """
        return self.conversation_type == "group"

    def get_participant_numbers(self) -> list[str]:
        """Get list of all participant phone numbers.

        Returns:
            List of phone numbers.
        """
        return [p.phone_number for p in self.participants]

    def get_active_participants(self) -> list[GroupParticipant]:
        """Get currently active participants.

        Returns:
            List of participants who haven't left.
        """
        return [p for p in self.participants if p.is_active()]

    def add_participant(
        self,
        phone_number: str,
        is_admin: bool,
        current_time: datetime,
    ) -> None:
        """Add new participant to conversation.

        Args:
            phone_number: Phone number to add.
            is_admin: Whether participant should be admin.
            current_time: Current simulator time.
        """
        participant = GroupParticipant(
            phone_number=phone_number,
            is_admin=is_admin,
            joined_at=current_time,
        )
        self.participants.append(participant)

    def remove_participant(self, phone_number: str, current_time: datetime) -> None:
        """Remove participant from conversation (set left_at).

        Args:
            phone_number: Phone number to remove.
            current_time: Current simulator time.
        """
        for participant in self.participants:
            if participant.phone_number == phone_number and participant.is_active():
                participant.left_at = current_time
                break

    def get_other_participant(self) -> Optional[str]:
        """For one-on-one conversations, get the other phone number.

        Returns:
            The other participant's phone number, or None if not one-on-one.
        """
        if self.conversation_type == "one_on_one":
            active = self.get_active_participants()
            if len(active) >= 2:
                return active[1].phone_number
        return None

    def update_last_message(self, timestamp: datetime) -> None:
        """Update last_message_at timestamp.

        Args:
            timestamp: Timestamp of the new message.
        """
        self.last_message_at = timestamp
        self.message_count += 1

    def increment_unread(self) -> None:
        """Increase unread count by one."""
        self.unread_count += 1

    def mark_all_read(self) -> None:
        """Reset unread_count to 0."""
        self.unread_count = 0

    def pin(self) -> None:
        """Set is_pinned to True."""
        self.is_pinned = True

    def unpin(self) -> None:
        """Set is_pinned to False."""
        self.is_pinned = False

    def mute(self) -> None:
        """Set is_muted to True."""
        self.is_muted = True

    def unmute(self) -> None:
        """Set is_muted to False."""
        self.is_muted = False

    def archive(self) -> None:
        """Set is_archived to True."""
        self.is_archived = True

    def unarchive(self) -> None:
        """Set is_archived to False."""
        self.is_archived = False

    def save_draft(self, text: str) -> None:
        """Save draft message text.

        Args:
            text: Draft message text to save.
        """
        self.draft_message = text

    def clear_draft(self) -> None:
        """Clear draft message."""
        self.draft_message = None


class SMSState(ModalityState):
    """Tracks all SMS/RCS conversations, messages, and related state.

    Args:
        modality_type: Always "sms".
        last_updated: When state was last modified.
        update_count: Number of inputs applied.
        messages: All messages keyed by message_id.
        conversations: All conversations keyed by thread_id.
        max_messages_per_conversation: Message history limit per conversation.
        user_phone_number: The simulated user's phone number.
    """

    modality_type: str = Field(default="sms", description="Always 'sms'")
    messages: dict[str, SMSMessage] = Field(
        default_factory=dict,
        description="All messages keyed by message_id",
    )
    conversations: dict[str, SMSConversation] = Field(
        default_factory=dict,
        description="All conversations keyed by thread_id",
    )
    max_messages_per_conversation: int = Field(
        default=10000,
        description="Message history limit per conversation",
    )
    user_phone_number: str = Field(
        description="The simulated user's phone number"
    )

    def apply_input(self, input_data: SMSInput) -> None:
        """Process SMS action and update state accordingly.

        Args:
            input_data: The SMS input to apply.

        Raises:
            ValueError: If input is invalid or references non-existent entities.
        """
        if not isinstance(input_data, SMSInput):
            raise ValueError(f"Expected SMSInput, got {type(input_data)}")

        input_data.validate_input()

        if input_data.action in ["send_message", "receive_message"]:
            self._handle_message(input_data)
        elif input_data.action == "update_delivery_status":
            self._handle_delivery_update(input_data)
        elif input_data.action == "add_reaction":
            self._handle_add_reaction(input_data)
        elif input_data.action == "remove_reaction":
            self._handle_remove_reaction(input_data)
        elif input_data.action == "edit_message":
            self._handle_edit_message(input_data)
        elif input_data.action == "delete_message":
            self._handle_delete_message(input_data)
        elif input_data.action == "create_group":
            self._handle_create_group(input_data)
        elif input_data.action == "update_group":
            self._handle_update_group(input_data)
        elif input_data.action == "add_participant":
            self._handle_add_participant(input_data)
        elif input_data.action in ["remove_participant", "leave_group"]:
            self._handle_remove_participant(input_data)
        elif input_data.action == "update_conversation":
            self._handle_update_conversation(input_data)

        self.last_updated = input_data.timestamp
        self.update_count += 1

    def _handle_message(self, input_data: SMSInput) -> None:
        """Handle send_message and receive_message actions.

        Args:
            input_data: The SMS input with message_data.
        """
        msg_data = input_data.message_data
        if not msg_data:
            return

        from_number = msg_data["from_number"]
        to_numbers = msg_data["to_numbers"]
        body = msg_data["body"]
        message_type = msg_data.get("message_type", "sms")

        direction = "outgoing" if from_number == self.user_phone_number else "incoming"

        thread_id = msg_data.get("thread_id")
        if not thread_id:
            all_participants = sorted(set([from_number] + to_numbers))
            thread_id = self.find_or_create_conversation(
                all_participants,
                msg_data.get("group_name"),
                input_data.timestamp,
            )

        if thread_id not in self.conversations:
            raise ValueError(f"Conversation {thread_id} not found")

        attachments = []
        for att_data in msg_data.get("attachments", []):
            attachment = MessageAttachment(**att_data)
            attachments.append(attachment)

        message = SMSMessage(
            thread_id=thread_id,
            from_number=from_number,
            to_numbers=to_numbers,
            body=body,
            attachments=attachments,
            message_type=message_type,
            direction=direction,
            sent_at=input_data.timestamp,
            is_read=(direction == "outgoing"),
            replied_to_message_id=msg_data.get("replied_to_message_id"),
        )

        self.messages[message.message_id] = message

        conversation = self.conversations[thread_id]
        conversation.update_last_message(input_data.timestamp)
        if direction == "incoming":
            conversation.increment_unread()

        self._enforce_message_limit(thread_id)

    def _handle_delivery_update(self, input_data: SMSInput) -> None:
        """Handle update_delivery_status action.

        Args:
            input_data: The SMS input with delivery_update_data.
        """
        update_data = input_data.delivery_update_data
        if not update_data:
            return

        message_id = update_data["message_id"]
        new_status = update_data["new_status"]

        if message_id not in self.messages:
            raise ValueError(f"Message {message_id} not found")

        message = self.messages[message_id]

        if new_status == "delivered":
            message.mark_delivered(input_data.timestamp)
        elif new_status == "read":
            message.mark_read(input_data.timestamp)
        elif new_status == "failed":
            message.mark_failed()

    def _handle_add_reaction(self, input_data: SMSInput) -> None:
        """Handle add_reaction action.

        Args:
            input_data: The SMS input with reaction_data.
        """
        reaction_data = input_data.reaction_data
        if not reaction_data:
            return

        message_id = reaction_data["message_id"]
        phone_number = reaction_data["phone_number"]
        emoji = reaction_data["emoji"]

        if message_id not in self.messages:
            raise ValueError(f"Message {message_id} not found")

        message = self.messages[message_id]
        message.add_reaction(phone_number, emoji, input_data.timestamp)

    def _handle_remove_reaction(self, input_data: SMSInput) -> None:
        """Handle remove_reaction action.

        Args:
            input_data: The SMS input with reaction_data.
        """
        reaction_data = input_data.reaction_data
        if not reaction_data:
            return

        message_id = reaction_data["message_id"]
        reaction_id = reaction_data["reaction_id"]

        if message_id not in self.messages:
            raise ValueError(f"Message {message_id} not found")

        message = self.messages[message_id]
        message.remove_reaction(reaction_id)

    def _handle_edit_message(self, input_data: SMSInput) -> None:
        """Handle edit_message action.

        Args:
            input_data: The SMS input with edit_data.
        """
        edit_data = input_data.edit_data
        if not edit_data:
            return

        message_id = edit_data["message_id"]
        new_body = edit_data["new_body"]

        if message_id not in self.messages:
            raise ValueError(f"Message {message_id} not found")

        message = self.messages[message_id]
        message.edit_body(new_body, input_data.timestamp)

    def _handle_delete_message(self, input_data: SMSInput) -> None:
        """Handle delete_message action.

        Args:
            input_data: The SMS input with delete_data.
        """
        delete_data = input_data.delete_data
        if not delete_data:
            return

        message_id = delete_data["message_id"]

        if message_id not in self.messages:
            raise ValueError(f"Message {message_id} not found")

        message = self.messages[message_id]
        message.soft_delete()

    def _handle_create_group(self, input_data: SMSInput) -> None:
        """Handle create_group action.

        Args:
            input_data: The SMS input with group_data.
        """
        group_data = input_data.group_data
        if not group_data:
            return

        creator_number = group_data["creator_number"]
        participant_numbers = group_data["participant_numbers"]
        group_name = group_data.get("group_name")

        participants = []
        for number in participant_numbers:
            is_admin = number == creator_number
            participant = GroupParticipant(
                phone_number=number,
                is_admin=is_admin,
                joined_at=input_data.timestamp,
            )
            participants.append(participant)

        conversation = SMSConversation(
            conversation_type="group",
            participants=participants,
            group_name=group_name,
            created_at=input_data.timestamp,
            created_by=creator_number,
            last_message_at=input_data.timestamp,
        )

        self.conversations[conversation.thread_id] = conversation

    def _handle_update_group(self, input_data: SMSInput) -> None:
        """Handle update_group action.

        Args:
            input_data: The SMS input with group_data.
        """
        group_data = input_data.group_data
        if not group_data:
            return

        thread_id = group_data["thread_id"]

        if thread_id not in self.conversations:
            raise ValueError(f"Conversation {thread_id} not found")

        conversation = self.conversations[thread_id]

        if "group_name" in group_data:
            conversation.group_name = group_data["group_name"]
        if "group_photo_url" in group_data:
            conversation.group_photo_url = group_data["group_photo_url"]

    def _handle_add_participant(self, input_data: SMSInput) -> None:
        """Handle add_participant action.

        Args:
            input_data: The SMS input with participant_data.
        """
        participant_data = input_data.participant_data
        if not participant_data:
            return

        thread_id = participant_data["thread_id"]
        phone_number = participant_data["phone_number"]
        is_admin = participant_data.get("is_admin", False)

        if thread_id not in self.conversations:
            raise ValueError(f"Conversation {thread_id} not found")

        conversation = self.conversations[thread_id]
        conversation.add_participant(phone_number, is_admin, input_data.timestamp)

    def _handle_remove_participant(self, input_data: SMSInput) -> None:
        """Handle remove_participant and leave_group actions.

        Args:
            input_data: The SMS input with participant_data.
        """
        participant_data = input_data.participant_data
        if not participant_data:
            return

        thread_id = participant_data["thread_id"]
        phone_number = participant_data.get("phone_number", self.user_phone_number)

        if thread_id not in self.conversations:
            raise ValueError(f"Conversation {thread_id} not found")

        conversation = self.conversations[thread_id]
        conversation.remove_participant(phone_number, input_data.timestamp)

    def _handle_update_conversation(self, input_data: SMSInput) -> None:
        """Handle update_conversation action.

        Args:
            input_data: The SMS input with conversation_update_data.
        """
        update_data = input_data.conversation_update_data
        if not update_data:
            return

        thread_id = update_data["thread_id"]

        if thread_id not in self.conversations:
            raise ValueError(f"Conversation {thread_id} not found")

        conversation = self.conversations[thread_id]

        if "pin" in update_data:
            if update_data["pin"]:
                conversation.pin()
            else:
                conversation.unpin()

        if "mute" in update_data:
            if update_data["mute"]:
                conversation.mute()
            else:
                conversation.unmute()

        if "archive" in update_data:
            if update_data["archive"]:
                conversation.archive()
            else:
                conversation.unarchive()

        if update_data.get("mark_all_read"):
            conversation.mark_all_read()
            for message in self.get_conversation_messages(thread_id):
                if not message.is_read:
                    message.mark_read(input_data.timestamp)

        if "draft_message" in update_data:
            draft = update_data["draft_message"]
            if draft:
                conversation.save_draft(draft)
            else:
                conversation.clear_draft()

    def _enforce_message_limit(self, thread_id: str) -> None:
        """Enforce message history limit for a conversation.

        Args:
            thread_id: Conversation to enforce limit for.
        """
        messages_in_thread = [
            msg for msg in self.messages.values() if msg.thread_id == thread_id
        ]

        if len(messages_in_thread) > self.max_messages_per_conversation:
            messages_in_thread.sort(key=lambda m: m.sent_at)
            excess = len(messages_in_thread) - self.max_messages_per_conversation

            for message in messages_in_thread[:excess]:
                del self.messages[message.message_id]

    def find_or_create_conversation(
        self,
        participants: list[str],
        group_name: Optional[str],
        current_time: datetime,
    ) -> str:
        """Find existing or create new conversation.

        Args:
            participants: List of phone numbers.
            group_name: Optional group name for group conversations.
            current_time: Current simulator time.

        Returns:
            Thread ID of the conversation.
        """
        participants_sorted = sorted(participants)

        for conversation in self.conversations.values():
            conv_numbers = sorted(conversation.get_participant_numbers())
            if conv_numbers == participants_sorted:
                return conversation.thread_id

        conversation_type = "group" if len(participants) > 2 else "one_on_one"

        participant_objects = []
        for number in participants:
            participant = GroupParticipant(
                phone_number=number,
                is_admin=False,
                joined_at=current_time,
            )
            participant_objects.append(participant)

        conversation = SMSConversation(
            conversation_type=conversation_type,
            participants=participant_objects,
            group_name=group_name,
            created_at=current_time,
            last_message_at=current_time,
        )

        self.conversations[conversation.thread_id] = conversation
        return conversation.thread_id

    def get_snapshot(self) -> dict[str, Any]:
        """Return complete state for API responses.

        Returns:
            Dictionary representation of current SMS state.
        """
        return {
            "modality_type": self.modality_type,
            "last_updated": self.last_updated.isoformat(),
            "update_count": self.update_count,
            "user_phone_number": self.user_phone_number,
            "conversations": {
                thread_id: conv.to_dict()
                for thread_id, conv in self.conversations.items()
            },
            "messages": {
                msg_id: msg.to_dict() for msg_id, msg in self.messages.items()
            },
            "total_conversations": len(self.conversations),
            "total_messages": len(self.messages),
            "unread_total": sum(
                conv.unread_count for conv in self.conversations.values()
            ),
        }

    def validate_state(self) -> list[str]:
        """Validate internal state consistency.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors = []

        for message_id, message in self.messages.items():
            if message.thread_id not in self.conversations:
                errors.append(
                    f"Message {message_id} references non-existent conversation {message.thread_id}"
                )

        for thread_id, conversation in self.conversations.items():
            messages_in_conv = [
                msg for msg in self.messages.values() if msg.thread_id == thread_id
            ]

            if conversation.message_count != len(messages_in_conv):
                errors.append(
                    f"Conversation {thread_id} message_count ({conversation.message_count}) "
                    f"doesn't match actual count ({len(messages_in_conv)})"
                )

            if not conversation.participants:
                errors.append(
                    f"Conversation {thread_id} has no participants"
                )

        return errors

    def query(self, query_params: dict[str, Any]) -> list[SMSMessage]:
        """Search messages based on query parameters.

        Args:
            query_params: Query filters (thread_id, phone_number, direction, etc.).

        Returns:
            List of matching messages.
        """
        results = list(self.messages.values())

        if "thread_id" in query_params:
            thread_id = query_params["thread_id"]
            results = [msg for msg in results if msg.thread_id == thread_id]

        if "phone_number" in query_params:
            number = query_params["phone_number"]
            results = [
                msg
                for msg in results
                if msg.from_number == number or number in msg.to_numbers
            ]

        if "direction" in query_params:
            direction = query_params["direction"]
            results = [msg for msg in results if msg.direction == direction]

        if "message_type" in query_params:
            msg_type = query_params["message_type"]
            results = [msg for msg in results if msg.message_type == msg_type]

        if "is_read" in query_params:
            is_read = query_params["is_read"]
            results = [msg for msg in results if msg.is_read == is_read]

        if "has_attachments" in query_params and query_params["has_attachments"]:
            results = [msg for msg in results if msg.attachments]

        if "search_text" in query_params:
            search = query_params["search_text"].lower()
            results = [msg for msg in results if search in msg.body.lower()]

        if "since" in query_params:
            since = query_params["since"]
            results = [msg for msg in results if msg.sent_at >= since]

        if "until" in query_params:
            until = query_params["until"]
            results = [msg for msg in results if msg.sent_at <= until]

        results.sort(key=lambda m: m.sent_at)

        if "limit" in query_params:
            limit = query_params["limit"]
            results = results[:limit]

        return results

    def get_conversation(self, thread_id: str) -> Optional[SMSConversation]:
        """Retrieve specific conversation.

        Args:
            thread_id: Conversation identifier.

        Returns:
            The conversation, or None if not found.
        """
        return self.conversations.get(thread_id)

    def get_conversation_messages(
        self,
        thread_id: str,
        limit: Optional[int] = None,
    ) -> list[SMSMessage]:
        """Get messages in conversation, ordered by timestamp.

        Args:
            thread_id: Conversation identifier.
            limit: Optional limit on number of messages.

        Returns:
            List of messages in the conversation.
        """
        messages = [
            msg for msg in self.messages.values() if msg.thread_id == thread_id
        ]
        messages.sort(key=lambda m: m.sent_at)

        if limit:
            messages = messages[-limit:]

        return messages

    def get_message(self, message_id: str) -> Optional[SMSMessage]:
        """Retrieve specific message.

        Args:
            message_id: Message identifier.

        Returns:
            The message, or None if not found.
        """
        return self.messages.get(message_id)

    def get_recent_conversations(
        self,
        limit: int,
        include_archived: bool = False,
    ) -> list[SMSConversation]:
        """Get most recent conversations, sorted by last_message_at.

        Args:
            limit: Maximum number of conversations to return.
            include_archived: Whether to include archived conversations.

        Returns:
            List of recent conversations.
        """
        conversations = list(self.conversations.values())

        if not include_archived:
            conversations = [c for c in conversations if not c.is_archived]

        conversations.sort(key=lambda c: c.last_message_at, reverse=True)

        return conversations[:limit]

    def get_unread_count(self, thread_id: Optional[str] = None) -> int:
        """Get unread message count.

        Args:
            thread_id: Optional conversation ID for per-conversation count.

        Returns:
            Unread message count.
        """
        if thread_id:
            conversation = self.conversations.get(thread_id)
            return conversation.unread_count if conversation else 0

        return sum(conv.unread_count for conv in self.conversations.values())

    def mark_message_spam(self, message_id: str) -> None:
        """Flag individual message as spam.

        Args:
            message_id: Message to flag.

        Raises:
            ValueError: If message not found.
        """
        if message_id not in self.messages:
            raise ValueError(f"Message {message_id} not found")

        self.messages[message_id].is_spam = True

    def unmark_message_spam(self, message_id: str) -> None:
        """Remove spam flag from message.

        Args:
            message_id: Message to unflag.

        Raises:
            ValueError: If message not found.
        """
        if message_id not in self.messages:
            raise ValueError(f"Message {message_id} not found")

        self.messages[message_id].is_spam = False
