"""Unit tests for SMS state modality.

This module tests both general ModalityState behavior and SMS-specific features.
"""

from datetime import datetime, timezone

import pytest

from models.modalities.sms_input import MessageAttachmentData, SMSInput
from models.modalities.sms_state import (
    GroupParticipant,
    MessageAttachment,
    MessageReaction,
    SMSConversation,
    SMSMessage,
    SMSState,
)
from tests.fixtures.modalities.sms import create_sms_state


class TestSMSStateInstantiation:
    """Test instantiation patterns for SMSState.

    GENERAL PATTERN: All ModalityState subclasses should instantiate with
    user_phone_number.
    """

    def test_minimal_instantiation(self):
        """GENERAL PATTERN: Verify SMSState instantiates with minimal fields."""
        state = SMSState(
            user_phone_number="+15559876543",
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        assert state.modality_type == "sms"
        assert state.user_phone_number == "+15559876543"
        assert state.conversations == {}
        assert state.messages == {}
        assert state.last_updated is not None

    def test_initialization_creates_empty_collections(self):
        """GENERAL PATTERN: Verify empty collections on init."""
        state = SMSState(
            user_phone_number="+15559876543",
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        assert isinstance(state.conversations, dict)
        assert isinstance(state.messages, dict)
        assert len(state.conversations) == 0
        assert len(state.messages) == 0


class TestMessageAttachment:
    """Test MessageAttachment helper class.

    MODALITY-SPECIFIC: Attachment tracking in state.
    """

    def test_image_attachment(self):
        """MODALITY-SPECIFIC: Verify image attachment storage."""
        attachment = MessageAttachment(
            filename="photo.jpg",
            size=2048000,
            mime_type="image/jpeg",
            thumbnail_url="https://example.com/thumb.jpg",
        )

        assert attachment.filename == "photo.jpg"
        assert attachment.mime_type == "image/jpeg"

    def test_attachment_serialization(self):
        """Verify attachment serializes correctly."""
        attachment = MessageAttachment(
            filename="video.mp4",
            size=10240000,
            mime_type="video/mp4",
            duration=45,
        )

        dumped = attachment.model_dump()
        restored = MessageAttachment.model_validate(dumped)

        assert restored.filename == attachment.filename
        assert restored.duration == attachment.duration


class TestMessageReaction:
    """Test MessageReaction helper class.

    MODALITY-SPECIFIC: Reaction tracking for RCS messages.
    """

    def test_reaction_creation(self):
        """MODALITY-SPECIFIC: Verify reaction storage."""
        reaction = MessageReaction(
            reaction_id="react-123",
            message_id="msg-123",
            phone_number="+15551234567",
            emoji="👍",
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        assert reaction.emoji == "👍"
        assert reaction.phone_number == "+15551234567"

    def test_reaction_serialization(self):
        """Verify reaction serializes correctly."""
        reaction = MessageReaction(
            reaction_id="react-123",
            message_id="msg-123",
            phone_number="+15551234567",
            emoji="❤️",
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        dumped = reaction.model_dump()
        restored = MessageReaction.model_validate(dumped)

        assert restored.emoji == reaction.emoji


class TestGroupParticipant:
    """Test GroupParticipant helper class.

    MODALITY-SPECIFIC: Participant tracking in group conversations.
    """

    def test_participant_creation(self):
        """MODALITY-SPECIFIC: Verify participant storage."""
        participant = GroupParticipant(
            phone_number="+15551234567",
            joined_at=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            is_admin=False,
        )

        assert participant.phone_number == "+15551234567"
        assert participant.is_admin is False

    def test_participant_left_at(self):
        """MODALITY-SPECIFIC: Verify participant can have left_at."""
        participant = GroupParticipant(
            phone_number="+15551234567",
            joined_at=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            left_at=datetime(2025, 1, 2, 12, 0, tzinfo=timezone.utc),
        )

        assert participant.left_at is not None


class TestSMSMessage:
    """Test SMSMessage helper class.

    MODALITY-SPECIFIC: Message storage and tracking.
    """

    def test_simple_message(self):
        """MODALITY-SPECIFIC: Verify simple message storage."""
        message = SMSMessage(
            message_id="msg-123",
            thread_id="thread-456",
            from_number="+15559876543",
            to_numbers=["+15551234567"],
            body="Hello!",
            direction="outgoing",
            sent_at=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        assert message.message_id == "msg-123"
        assert message.body == "Hello!"
        assert message.from_number == "+15559876543"

    def test_message_with_attachments(self):
        """MODALITY-SPECIFIC: Verify message with attachments."""
        message = SMSMessage(
            message_id="msg-123",
            thread_id="thread-456",
            from_number="+15559876543",
            to_numbers=["+15551234567"],
            body="Check this out!",
            direction="outgoing",
            sent_at=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            attachments=[
                MessageAttachment(
                    filename="photo.jpg",
                    size=2048000,
                    mime_type="image/jpeg",
                )
            ],
        )

        assert len(message.attachments) == 1
        assert message.attachments[0].filename == "photo.jpg"

    def test_message_with_reactions(self):
        """MODALITY-SPECIFIC: Verify message with reactions."""
        message = SMSMessage(
            message_id="msg-123",
            thread_id="thread-456",
            from_number="+15559876543",
            to_numbers=["+15551234567"],
            body="Great news!",
            direction="outgoing",
            sent_at=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            reactions=[
                MessageReaction(
                    reaction_id="react-1",
                    message_id="msg-123",
                    phone_number="+15551234567",
                    emoji="🎉",
                    timestamp=datetime(2025, 1, 1, 12, 5, tzinfo=timezone.utc),
                )
            ],
        )

        assert len(message.reactions) == 1
        assert message.reactions[0].emoji == "🎉"

    def test_message_delivery_status(self):
        """MODALITY-SPECIFIC: Verify delivery status tracking."""
        message = SMSMessage(
            message_id="msg-123",
            thread_id="thread-456",
            from_number="+15559876543",
            to_numbers=["+15551234567"],
            body="Test",
            direction="outgoing",
            sent_at=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            delivery_status="delivered",
        )

        assert message.delivery_status == "delivered"


class TestSMSConversation:
    """Test SMSConversation helper class.

    MODALITY-SPECIFIC: Conversation/thread tracking.
    """

    def test_one_on_one_conversation(self):
        """MODALITY-SPECIFIC: Verify 1-on-1 conversation."""
        conversation = SMSConversation(
            thread_id="thread-123",
            conversation_type="one_on_one",
            participants=[
                GroupParticipant(
                    phone_number="+15551234567",
                    joined_at=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
                )
            ],
            created_at=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            last_message_at=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        assert conversation.conversation_type == "one_on_one"
        assert len(conversation.participants) == 1

    def test_group_conversation(self):
        """MODALITY-SPECIFIC: Verify group conversation."""
        conversation = SMSConversation(
            thread_id="thread-123",
            conversation_type="group",
            participants=[
                GroupParticipant(
                    phone_number="+15551234567",
                    joined_at=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
                ),
                GroupParticipant(
                    phone_number="+15555555555",
                    joined_at=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
                ),
            ],
            group_name="Family Chat",
            created_at=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            last_message_at=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        assert conversation.conversation_type == "group"
        assert conversation.group_name == "Family Chat"
        assert len(conversation.participants) == 2

    def test_conversation_message_counts(self):
        """MODALITY-SPECIFIC: Verify message count tracking."""
        conversation = SMSConversation(
            thread_id="thread-123",
            conversation_type="one_on_one",
            participants=[],
            message_count=10,
            unread_count=3,
            created_at=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            last_message_at=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        assert conversation.message_count == 10
        assert conversation.unread_count == 3

    def test_conversation_pin_mute_archive(self):
        """MODALITY-SPECIFIC: Verify conversation state flags."""
        conversation = SMSConversation(
            thread_id="thread-123",
            conversation_type="one_on_one",
            participants=[],
            is_pinned=True,
            is_muted=True,
            is_archived=False,
            created_at=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            last_message_at=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        assert conversation.is_pinned is True
        assert conversation.is_muted is True
        assert conversation.is_archived is False

    def test_conversation_draft_message(self):
        """MODALITY-SPECIFIC: Verify draft message storage."""
        conversation = SMSConversation(
            thread_id="thread-123",
            conversation_type="one_on_one",
            participants=[],
            draft_message="I need to finish typing this...",
            created_at=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            last_message_at=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        assert conversation.draft_message is not None


class TestSMSStateApplyInput:
    """Test SMSState.apply_input() method.

    GENERAL PATTERN: Test state updates from inputs.
    """

    def test_apply_send_message_creates_message(self):
        """GENERAL PATTERN: Verify apply_input creates message."""

        state = create_sms_state()

        input_event = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Hello!",
            },
        )

        state.apply_input(input_event)

        assert len(state.messages) == 1
        message = list(state.messages.values())[0]
        assert message.body == "Hello!"
        assert message.direction == "outgoing"

    def test_apply_receive_message_creates_message(self):
        """GENERAL PATTERN: Verify apply_input for received message."""

        state = create_sms_state()

        input_event = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="receive_message",
            message_data={
                "from_number": "+15551234567",
                "to_numbers": ["+15559876543"],
                "body": "Got it!",
            },
        )

        state.apply_input(input_event)

        assert len(state.messages) == 1
        message = list(state.messages.values())[0]
        assert message.direction == "incoming"
        assert message.is_read is False

    def test_apply_message_creates_conversation(self):
        """MODALITY-SPECIFIC: Verify conversation auto-created."""
        state = create_sms_state()

        input_event = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Hello!",
            },
        )

        state.apply_input(input_event)

        assert len(state.conversations) == 1
        conversation = list(state.conversations.values())[0]
        assert conversation.conversation_type == "one_on_one"

    def test_apply_group_message_creates_group_conversation(self):
        """MODALITY-SPECIFIC: Verify group conversation created."""
        state = create_sms_state()

        input_event = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567", "+15555555555"],
                "body": "Hello everyone!",
            },
        )

        state.apply_input(input_event)

        assert len(state.conversations) == 1
        conversation = list(state.conversations.values())[0]
        assert conversation.conversation_type == "group"

    def test_apply_delivery_status_update(self):
        """MODALITY-SPECIFIC: Verify delivery status update."""
        state = create_sms_state()

        # Send a message first
        send_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Test",
            },
        )
        state.apply_input(send_input)
        message_id = list(state.messages.keys())[0]

        # Update delivery status
        status_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 1, tzinfo=timezone.utc),
            action="update_delivery_status",
            delivery_update_data={
                "message_id": message_id,
                "new_status": "delivered",
            },
        )
        state.apply_input(status_input)

        message = state.messages[message_id]
        assert message.delivery_status == "delivered"

    def test_apply_add_reaction(self):
        """MODALITY-SPECIFIC: Verify add reaction."""
        state = create_sms_state()

        # Send a message first
        send_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Great news!",
            },
        )
        state.apply_input(send_input)
        message_id = list(state.messages.keys())[0]

        # Add reaction
        reaction_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 5, tzinfo=timezone.utc),
            action="add_reaction",
            reaction_data={
                "message_id": message_id,
                "phone_number": "+15551234567",
                "emoji": "🎉",
            },
        )
        state.apply_input(reaction_input)

        message = state.messages[message_id]
        assert len(message.reactions) == 1
        assert message.reactions[0].emoji == "🎉"

    def test_apply_remove_reaction(self):
        """MODALITY-SPECIFIC: Verify remove reaction."""
        state = create_sms_state()

        # Setup message with reaction
        send_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Test",
            },
        )
        state.apply_input(send_input)
        message_id = list(state.messages.keys())[0]

        add_reaction = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 1, tzinfo=timezone.utc),
            action="add_reaction",
            reaction_data={
                "message_id": message_id,
                "phone_number": "+15551234567",
                "emoji": "👍",
            },
        )
        state.apply_input(add_reaction)
        reaction_id = state.messages[message_id].reactions[0].reaction_id

        # Remove reaction
        remove_reaction = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 2, tzinfo=timezone.utc),
            action="remove_reaction",
            reaction_data={
                "message_id": message_id,
                "phone_number": "+15551234567",
                "reaction_id": reaction_id,
            },
        )
        state.apply_input(remove_reaction)

        message = state.messages[message_id]
        assert len(message.reactions) == 0

    def test_apply_edit_message(self):
        """MODALITY-SPECIFIC: Verify edit message (RCS)."""
        state = create_sms_state()

        # Send message
        send_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Original text",
                "message_type": "rcs",
            },
        )
        state.apply_input(send_input)
        message_id = list(state.messages.keys())[0]

        # Edit message
        edit_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 5, tzinfo=timezone.utc),
            action="edit_message",
            edit_data={
                "message_id": message_id,
                "new_body": "Edited text",
            },
        )
        state.apply_input(edit_input)

        message = state.messages[message_id]
        assert message.body == "Edited text"
        assert message.edited_at is not None

    def test_apply_delete_message(self):
        """MODALITY-SPECIFIC: Verify delete message."""
        state = create_sms_state()

        # Send message
        send_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Delete me",
            },
        )
        state.apply_input(send_input)
        message_id = list(state.messages.keys())[0]

        # Delete message
        delete_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 5, tzinfo=timezone.utc),
            action="delete_message",
            delete_data={
                "message_id": message_id,
            },
        )
        state.apply_input(delete_input)

        message = state.messages[message_id]
        assert message.is_deleted is True

    def test_apply_create_group(self):
        """MODALITY-SPECIFIC: Verify create group conversation."""
        state = create_sms_state()

        create_group = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="create_group",
            group_data={
                "creator_number": "+15559876543",
                "participant_numbers": ["+15551234567", "+15555555555"],
                "group_name": "Family Chat",
            },
        )
        state.apply_input(create_group)

        assert len(state.conversations) == 1
        conversation = list(state.conversations.values())[0]
        assert conversation.conversation_type == "group"
        assert conversation.group_name == "Family Chat"
        # Only the specified participants, not the creator
        assert len(conversation.participants) == 2

    def test_apply_update_group(self):
        """MODALITY-SPECIFIC: Verify update group metadata."""
        state = create_sms_state()

        # Create group
        create_group = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="create_group",
            group_data={
                "creator_number": "+15559876543",
                "participant_numbers": ["+15551234567", "+15555555555"],
                "group_name": "Old Name",
            },
        )
        state.apply_input(create_group)
        thread_id = list(state.conversations.keys())[0]

        # Update group name
        update_group = SMSInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            action="update_group",
            group_data={
                "thread_id": thread_id,
                "group_name": "New Name",
            },
        )
        state.apply_input(update_group)

        conversation = state.conversations[thread_id]
        assert conversation.group_name == "New Name"

    def test_apply_add_participant(self):
        """MODALITY-SPECIFIC: Verify add participant to group."""
        state = create_sms_state()

        # Create group
        create_group = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="create_group",
            group_data={
                "creator_number": "+15559876543",
                "participant_numbers": ["+15551234567", "+15552222222"],
            },
        )
        state.apply_input(create_group)
        thread_id = list(state.conversations.keys())[0]

        # Add participant
        add_participant = SMSInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            action="add_participant",
            participant_data={
                "thread_id": thread_id,
                "phone_number": "+15555555555",
            },
        )
        state.apply_input(add_participant)

        conversation = state.conversations[thread_id]
        active_participants = conversation.get_active_participants()
        # 2 initial + 1 added = 3 total
        assert len(active_participants) == 3

    def test_apply_remove_participant(self):
        """MODALITY-SPECIFIC: Verify remove participant from group."""
        state = create_sms_state()

        # Create group
        create_group = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="create_group",
            group_data={
                "creator_number": "+15559876543",
                "participant_numbers": ["+15551234567", "+15555555555"],
            },
        )
        state.apply_input(create_group)
        thread_id = list(state.conversations.keys())[0]

        # Remove participant
        remove_participant = SMSInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            action="remove_participant",
            participant_data={
                "thread_id": thread_id,
                "phone_number": "+15555555555",
            },
        )
        state.apply_input(remove_participant)

        conversation = state.conversations[thread_id]
        active_participants = conversation.get_active_participants()
        # 2 initial - 1 removed = 1 remaining
        assert len(active_participants) == 1

    def test_apply_update_conversation(self):
        """MODALITY-SPECIFIC: Verify update conversation flags."""
        state = create_sms_state()

        # Send message to create conversation
        send_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Test",
            },
        )
        state.apply_input(send_input)
        thread_id = list(state.conversations.keys())[0]

        # Update conversation
        update_conv = SMSInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            action="update_conversation",
            conversation_update_data={
                "thread_id": thread_id,
                "pin": True,
                "mute": True,
            },
        )
        state.apply_input(update_conv)

        conversation = state.conversations[thread_id]
        assert conversation.is_pinned is True
        assert conversation.is_muted is True


class TestSMSStateGetSnapshot:
    """Test SMSState.get_snapshot() method.

    GENERAL PATTERN: Test snapshot generation.
    """

    def test_empty_snapshot(self):
        """GENERAL PATTERN: Verify snapshot of empty state."""
        state = create_sms_state()
        snapshot = state.get_snapshot()

        assert snapshot["modality_type"] == "sms"
        assert snapshot["user_phone_number"] == "+15559876543"
        assert snapshot["conversations"] == {}
        assert snapshot["messages"] == {}
        assert snapshot["total_conversations"] == 0
        assert snapshot["total_messages"] == 0

    def test_snapshot_with_messages(self):
        """GENERAL PATTERN: Verify snapshot includes messages."""
        state = create_sms_state()

        send_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Hello!",
            },
        )
        state.apply_input(send_input)

        snapshot = state.get_snapshot()
        assert snapshot["total_messages"] == 1
        assert len(snapshot["messages"]) == 1

    def test_snapshot_with_conversations(self):
        """MODALITY-SPECIFIC: Verify snapshot includes conversations."""
        state = create_sms_state()

        send_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Test",
            },
        )
        state.apply_input(send_input)

        snapshot = state.get_snapshot()
        assert snapshot["total_conversations"] == 1
        assert len(snapshot["conversations"]) == 1

    def test_snapshot_unread_total(self):
        """MODALITY-SPECIFIC: Verify snapshot calculates unread total."""
        state = create_sms_state()

        # Receive 3 messages (unread)
        for i in range(3):
            receive_input = SMSInput(
                timestamp=datetime(2025, 1, 1, 12, i, tzinfo=timezone.utc),
                action="receive_message",
                message_data={
                    "from_number": "+15551234567",
                    "to_numbers": ["+15559876543"],
                    "body": f"Message {i}",
                },
            )
            state.apply_input(receive_input)

        snapshot = state.get_snapshot()
        assert snapshot["unread_total"] == 3


class TestSMSStateValidateState:
    """Test SMSState.validate_state() method.

    GENERAL PATTERN: Test state validation.
    MODALITY-SPECIFIC: SMS returns list[str] instead of None.
    """

    def test_validate_empty_state(self):
        """GENERAL PATTERN: Verify empty state is valid."""
        state = create_sms_state()
        errors = state.validate_state()

        assert isinstance(errors, list)
        assert len(errors) == 0

    def test_validate_state_with_messages(self):
        """GENERAL PATTERN: Verify state with messages is valid."""
        state = create_sms_state()

        send_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Test",
            },
        )
        state.apply_input(send_input)

        errors = state.validate_state()
        assert len(errors) == 0

    def test_validate_detects_orphaned_message(self):
        """MODALITY-SPECIFIC: Verify validation catches orphaned messages."""
        state = create_sms_state()

        # Manually create invalid state
        message = SMSMessage(
            message_id="msg-123",
            thread_id="nonexistent-thread",
            from_number="+15559876543",
            to_numbers=["+15551234567"],
            body="Orphaned",
            direction="outgoing",
            sent_at=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        state.messages["msg-123"] = message

        errors = state.validate_state()
        assert len(errors) > 0
        assert any("nonexistent-thread" in error for error in errors)


class TestSMSStateQuery:
    """Test SMSState.query() method.

    MODALITY-SPECIFIC: SMS-specific query filters.
    """

    def test_query_all_messages(self):
        """GENERAL PATTERN: Verify querying all messages."""
        state = create_sms_state()

        # Send 3 messages
        for i in range(3):
            send_input = SMSInput(
                timestamp=datetime(2025, 1, 1, 12, i, tzinfo=timezone.utc),
                action="send_message",
                message_data={
                    "from_number": "+15559876543",
                    "to_numbers": ["+15551234567"],
                    "body": f"Message {i}",
                },
            )
            state.apply_input(send_input)

        result = state.query({})
        assert result["count"] == 3
        assert len(result["messages"]) == 3

    def test_query_by_thread_id(self):
        """MODALITY-SPECIFIC: Verify query filtering by thread_id."""
        state = create_sms_state()

        # Send to two different conversations (let auto-creation happen)
        send1 = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Thread A",
            },
        )
        state.apply_input(send1)
        thread_a = list(state.messages.values())[0].thread_id

        send2 = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 1, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15555555555"],
                "body": "Thread B",
            },
        )
        state.apply_input(send2)

        result = state.query({"thread_id": thread_a})
        assert result["count"] == 1
        assert len(result["messages"]) == 1
        assert result["messages"][0]["body"] == "Thread A"

    def test_query_by_phone_number(self):
        """MODALITY-SPECIFIC: Verify query filtering by phone number."""
        state = create_sms_state()

        # Messages from different numbers
        receive1 = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="receive_message",
            message_data={
                "from_number": "+15551234567",
                "to_numbers": ["+15559876543"],
                "body": "From Alice",
            },
        )
        state.apply_input(receive1)

        receive2 = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 1, tzinfo=timezone.utc),
            action="receive_message",
            message_data={
                "from_number": "+15555555555",
                "to_numbers": ["+15559876543"],
                "body": "From Bob",
            },
        )
        state.apply_input(receive2)

        result = state.query({"phone_number": "+15551234567"})
        assert result["count"] == 1
        assert len(result["messages"]) == 1
        assert result["messages"][0]["body"] == "From Alice"

    def test_query_by_direction(self):
        """MODALITY-SPECIFIC: Verify query filtering by direction."""
        state = create_sms_state()

        # Send and receive
        send = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Outgoing",
            },
        )
        state.apply_input(send)

        receive = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 1, tzinfo=timezone.utc),
            action="receive_message",
            message_data={
                "from_number": "+15551234567",
                "to_numbers": ["+15559876543"],
                "body": "Incoming",
            },
        )
        state.apply_input(receive)

        outgoing = state.query({"direction": "outgoing"})
        assert outgoing["count"] == 1
        assert len(outgoing["messages"]) == 1
        assert outgoing["messages"][0]["body"] == "Outgoing"

        incoming = state.query({"direction": "incoming"})
        assert incoming["count"] == 1
        assert len(incoming["messages"]) == 1
        assert incoming["messages"][0]["body"] == "Incoming"

    def test_query_by_is_read(self):
        """MODALITY-SPECIFIC: Verify query filtering by read status."""
        state = create_sms_state()

        # Receive unread message
        receive = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="receive_message",
            message_data={
                "from_number": "+15551234567",
                "to_numbers": ["+15559876543"],
                "body": "Unread",
            },
        )
        state.apply_input(receive)

        result = state.query({"is_read": False})
        assert result["count"] == 1
        assert len(result["messages"]) == 1

    def test_query_by_has_attachments(self):
        """MODALITY-SPECIFIC: Verify query filtering by attachments."""
        state = create_sms_state()

        # Text only
        text = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Text only",
            },
        )
        state.apply_input(text)

        # With attachment
        mms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 1, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Photo",
                "attachments": [
                    {
                        "filename": "photo.jpg",
                        "size": 1024,
                        "mime_type": "image/jpeg",
                    }
                ],
            },
        )
        state.apply_input(mms)

        result = state.query({"has_attachments": True})
        assert result["count"] == 1
        assert len(result["messages"]) == 1
        assert result["messages"][0]["body"] == "Photo"

    def test_query_with_limit(self):
        """MODALITY-SPECIFIC: Verify query limit."""
        state = create_sms_state()

        # Send 10 messages
        for i in range(10):
            send_input = SMSInput(
                timestamp=datetime(2025, 1, 1, 12, i, tzinfo=timezone.utc),
                action="send_message",
                message_data={
                    "from_number": "+15559876543",
                    "to_numbers": ["+15551234567"],
                    "body": f"Message {i}",
                },
            )
            state.apply_input(send_input)

        result = state.query({"limit": 5})
        assert result["count"] == 5
        assert len(result["messages"]) == 5


class TestSMSStateHelperMethods:
    """Test SMSState helper methods.

    MODALITY-SPECIFIC: SMS-specific utility methods.
    """

    def test_get_conversation_by_id(self):
        """MODALITY-SPECIFIC: Verify get_conversation() method."""
        state = create_sms_state()

        send_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Test",
            },
        )
        state.apply_input(send_input)
        thread_id = list(state.conversations.keys())[0]

        conversation = state.get_conversation(thread_id)
        assert conversation is not None
        assert conversation.thread_id == thread_id

    def test_get_message_by_id(self):
        """MODALITY-SPECIFIC: Verify get_message() method."""
        state = create_sms_state()

        send_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Test",
            },
        )
        state.apply_input(send_input)
        message_id = list(state.messages.keys())[0]

        message = state.get_message(message_id)
        assert message is not None
        assert message.message_id == message_id


class TestSMSStateSerialization:
    """Test SMSState serialization.

    GENERAL PATTERN: Verify state can be serialized and deserialized.
    """

    def test_simple_serialization(self):
        """GENERAL PATTERN: Verify state serializes and deserializes."""
        original = create_sms_state()

        send_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Test",
            },
        )
        original.apply_input(send_input)

        dumped = original.model_dump()
        restored = SMSState.model_validate(dumped)

        assert restored.user_phone_number == original.user_phone_number
        assert len(restored.messages) == len(original.messages)
        assert len(restored.conversations) == len(original.conversations)


class TestSMSStateFromFixtures:
    """Test using pre-built SMS fixtures.

    GENERAL PATTERN: Verify fixtures work correctly.
    """

    def test_empty_sms_state_fixture(self):
        """Verify EMPTY_SMS_STATE fixture."""
        from tests.fixtures.modalities.sms import EMPTY_SMS_STATE

        assert EMPTY_SMS_STATE.modality_type == "sms"
        assert EMPTY_SMS_STATE.user_phone_number == "+15559876543"


# ============================================================================
# UNDO FUNCTIONALITY TESTS
# ============================================================================


class TestSMSStateUndoCreateUndoData:
    """Test create_undo_data captures correct information for each action.

    GENERAL PATTERN: Verify undo data contains all information needed to reverse.
    """

    def test_send_message_undo_data_contains_message_info(self):
        """Verify send_message undo data tracks new conversation creation."""
        state = create_sms_state()

        send_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Hello!",
            },
        )

        undo_data = state.create_undo_data(send_input)

        assert undo_data["action"] == "remove_message"
        assert undo_data["was_new_conversation"] is True
        assert "state_previous_update_count" in undo_data
        assert "state_previous_last_updated" in undo_data

    def test_receive_message_undo_data_with_existing_conversation(self):
        """Verify receive_message undo data captures existing conversation state."""
        state = create_sms_state()

        # Create conversation first
        send_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "First message",
            },
        )
        state.apply_input(send_input)
        thread_id = list(state.conversations.keys())[0]

        # Receive in same conversation
        receive_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            action="receive_message",
            message_data={
                "from_number": "+15551234567",
                "to_numbers": ["+15559876543"],
                "body": "Reply",
                "thread_id": thread_id,
            },
        )

        undo_data = state.create_undo_data(receive_input)

        assert undo_data["action"] == "remove_message"
        assert undo_data["was_new_conversation"] is False
        assert undo_data["thread_id"] == thread_id
        assert undo_data["previous_conv_data"] is not None
        assert undo_data["previous_conv_data"]["message_count"] == 1

    def test_update_delivery_status_undo_data(self):
        """Verify update_delivery_status undo data captures previous status."""
        state = create_sms_state()

        # Send message (outgoing messages start with is_read=True)
        send_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Test",
            },
        )
        state.apply_input(send_input)
        message_id = list(state.messages.keys())[0]

        # Update status
        update_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            action="update_delivery_status",
            delivery_update_data={
                "message_id": message_id,
                "new_status": "delivered",
                "delivered_at": datetime(2025, 1, 1, 12, 31, tzinfo=timezone.utc),
            },
        )

        undo_data = state.create_undo_data(update_input)

        assert undo_data["action"] == "restore_delivery_status"
        assert undo_data["message_id"] == message_id
        assert undo_data["previous_delivery_status"] == "sent"
        # Outgoing messages are marked as read (you sent them)
        assert undo_data["previous_is_read"] is True

    def test_add_reaction_undo_data(self):
        """Verify add_reaction undo data tracks reaction count."""
        state = create_sms_state()

        # Receive message
        receive_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="receive_message",
            message_data={
                "from_number": "+15551234567",
                "to_numbers": ["+15559876543"],
                "body": "Test",
            },
        )
        state.apply_input(receive_input)
        message_id = list(state.messages.keys())[0]

        # Add reaction
        reaction_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            action="add_reaction",
            reaction_data={
                "message_id": message_id,
                "phone_number": "+15559876543",
                "emoji": "👍",
            },
        )

        undo_data = state.create_undo_data(reaction_input)

        assert undo_data["action"] == "remove_added_reaction"
        assert undo_data["message_id"] == message_id
        assert undo_data["previous_reaction_count"] == 0

    def test_remove_reaction_undo_data(self):
        """Verify remove_reaction undo data captures removed reaction."""
        state = create_sms_state()

        # Receive message
        receive_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="receive_message",
            message_data={
                "from_number": "+15551234567",
                "to_numbers": ["+15559876543"],
                "body": "Test",
            },
        )
        state.apply_input(receive_input)
        message_id = list(state.messages.keys())[0]

        # Add reaction
        reaction_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            action="add_reaction",
            reaction_data={
                "message_id": message_id,
                "phone_number": "+15559876543",
                "emoji": "👍",
            },
        )
        state.apply_input(reaction_input)
        reaction_id = state.messages[message_id].reactions[0].reaction_id

        # Remove reaction
        remove_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            action="remove_reaction",
            reaction_data={
                "message_id": message_id,
                "phone_number": "+15559876543",
                "reaction_id": reaction_id,
            },
        )

        undo_data = state.create_undo_data(remove_input)

        assert undo_data["action"] == "restore_reaction"
        assert undo_data["message_id"] == message_id
        assert undo_data["removed_reaction"]["emoji"] == "👍"

    def test_edit_message_undo_data(self):
        """Verify edit_message undo data captures previous body."""
        state = create_sms_state()

        # Send message
        send_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Original message",
            },
        )
        state.apply_input(send_input)
        message_id = list(state.messages.keys())[0]

        # Edit message
        edit_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            action="edit_message",
            edit_data={
                "message_id": message_id,
                "new_body": "Edited message",
            },
        )

        undo_data = state.create_undo_data(edit_input)

        assert undo_data["action"] == "restore_message_body"
        assert undo_data["message_id"] == message_id
        assert undo_data["previous_body"] == "Original message"
        assert undo_data["previous_edited_at"] is None

    def test_delete_message_undo_data(self):
        """Verify delete_message undo data captures previous deleted state."""
        state = create_sms_state()

        # Receive message
        receive_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="receive_message",
            message_data={
                "from_number": "+15551234567",
                "to_numbers": ["+15559876543"],
                "body": "Test",
            },
        )
        state.apply_input(receive_input)
        message_id = list(state.messages.keys())[0]

        # Delete message
        delete_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            action="delete_message",
            delete_data={"message_id": message_id},
        )

        undo_data = state.create_undo_data(delete_input)

        assert undo_data["action"] == "restore_message_deleted"
        assert undo_data["message_id"] == message_id
        assert undo_data["previous_is_deleted"] is False

    def test_create_group_undo_data(self):
        """Verify create_group undo data tracks new conversation."""
        state = create_sms_state()

        group_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="create_group",
            group_data={
                "group_name": "Test Group",
                "creator_number": "+15559876543",
                "participant_numbers": ["+15559876543", "+15551111111"],
            },
        )

        undo_data = state.create_undo_data(group_input)

        assert undo_data["action"] == "remove_group"
        assert undo_data["previous_conversation_ids"] == []

    def test_update_group_undo_data(self):
        """Verify update_group undo data captures previous settings."""
        state = create_sms_state()

        # Create group first (creator must be in participants)
        group_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="create_group",
            group_data={
                "group_name": "Original Name",
                "creator_number": "+15559876543",
                "participant_numbers": ["+15559876543", "+15551111111"],
            },
        )
        state.apply_input(group_input)
        thread_id = list(state.conversations.keys())[0]

        # Update group
        update_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            action="update_group",
            group_data={
                "thread_id": thread_id,
                "group_name": "New Name",
            },
        )

        undo_data = state.create_undo_data(update_input)

        assert undo_data["action"] == "restore_group_settings"
        assert undo_data["thread_id"] == thread_id
        assert undo_data["previous_group_name"] == "Original Name"

    def test_add_participant_undo_data(self):
        """Verify add_participant undo data tracks participant count."""
        state = create_sms_state()

        # Create group first (creator + at least 2 participants)
        group_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="create_group",
            group_data={
                "group_name": "Test Group",
                "creator_number": "+15559876543",
                "participant_numbers": ["+15559876543", "+15551111111"],
            },
        )
        state.apply_input(group_input)
        thread_id = list(state.conversations.keys())[0]
        initial_count = len(state.conversations[thread_id].participants)

        # Add participant
        add_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            action="add_participant",
            participant_data={
                "thread_id": thread_id,
                "phone_number": "+15552222222",
                "added_by": "+15559876543",
            },
        )

        undo_data = state.create_undo_data(add_input)

        assert undo_data["action"] == "remove_added_participant"
        assert undo_data["thread_id"] == thread_id
        assert undo_data["phone_number"] == "+15552222222"
        assert undo_data["previous_participant_count"] == initial_count

    def test_remove_participant_undo_data(self):
        """Verify remove_participant undo data captures participant info."""
        state = create_sms_state()

        # Create group with participants (creator must be in list)
        group_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="create_group",
            group_data={
                "group_name": "Test Group",
                "creator_number": "+15559876543",
                "participant_numbers": ["+15559876543", "+15551111111", "+15552222222"],
            },
        )
        state.apply_input(group_input)
        thread_id = list(state.conversations.keys())[0]

        # Remove participant
        remove_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            action="remove_participant",
            participant_data={
                "thread_id": thread_id,
                "phone_number": "+15552222222",
            },
        )

        undo_data = state.create_undo_data(remove_input)

        assert undo_data["action"] == "restore_participant"
        assert undo_data["thread_id"] == thread_id
        assert undo_data["participant_data"]["phone_number"] == "+15552222222"

    def test_leave_group_undo_data(self):
        """Verify leave_group undo data captures user participant info."""
        state = create_sms_state()

        # Create group with user as participant (creator included in participants)
        group_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="create_group",
            group_data={
                "group_name": "Test Group",
                "creator_number": "+15559876543",
                "participant_numbers": ["+15559876543", "+15551111111", "+15552222222"],
            },
        )
        state.apply_input(group_input)
        thread_id = list(state.conversations.keys())[0]

        # Leave group
        leave_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            action="leave_group",
            participant_data={"thread_id": thread_id},
        )

        undo_data = state.create_undo_data(leave_input)

        assert undo_data["action"] == "restore_participant"
        assert undo_data["thread_id"] == thread_id
        assert undo_data["participant_data"]["phone_number"] == "+15559876543"

    def test_update_conversation_undo_data_simple(self):
        """Verify update_conversation undo data captures settings."""
        state = create_sms_state()

        # Create conversation
        send_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Test",
            },
        )
        state.apply_input(send_input)
        thread_id = list(state.conversations.keys())[0]

        # Update conversation (use "pin" not "is_pinned")
        update_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            action="update_conversation",
            conversation_update_data={
                "thread_id": thread_id,
                "pin": True,
            },
        )

        undo_data = state.create_undo_data(update_input)

        assert undo_data["action"] == "restore_conversation_settings"
        assert undo_data["thread_id"] == thread_id
        assert undo_data["is_pinned"] is False
        assert undo_data["is_muted"] is False
        assert undo_data["is_archived"] is False

    def test_update_conversation_mark_all_read_captures_affected_messages(self):
        """Verify update_conversation with mark_all_read tracks affected messages."""
        state = create_sms_state()

        # Create conversation with multiple unread messages
        for i in range(3):
            receive_input = SMSInput(
                timestamp=datetime(2025, 1, 1, 12 + i, 0, tzinfo=timezone.utc),
                action="receive_message",
                message_data={
                    "from_number": "+15551234567",
                    "to_numbers": ["+15559876543"],
                    "body": f"Message {i}",
                },
            )
            state.apply_input(receive_input)

        thread_id = list(state.conversations.keys())[0]
        unread_count = sum(
            1
            for m in state.messages.values()
            if m.thread_id == thread_id and not m.is_read
        )

        # Mark all read
        update_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 15, 0, tzinfo=timezone.utc),
            action="update_conversation",
            conversation_update_data={
                "thread_id": thread_id,
                "mark_all_read": True,
            },
        )

        undo_data = state.create_undo_data(update_input)

        assert undo_data["action"] == "restore_conversation_settings"
        assert len(undo_data["affected_messages"]) == unread_count
        for msg_data in undo_data["affected_messages"]:
            assert msg_data["previous_is_read"] is False


class TestSMSStateUndoApplyUndo:
    """Test apply_undo correctly reverses state changes.

    GENERAL PATTERN: After apply_undo, state should match pre-apply state.
    """

    def test_apply_undo_noop_restores_metadata(self):
        """Verify noop undo restores state metadata only."""
        state = create_sms_state()
        original_update_count = state.update_count
        original_last_updated = state.last_updated

        # Create a noop situation (missing message for status update)
        update_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="update_delivery_status",
            delivery_update_data={
                "message_id": "nonexistent-msg",
                "new_status": "delivered",
            },
        )

        undo_data = state.create_undo_data(update_input)
        assert undo_data["action"] == "noop"

        # Manually change metadata to verify restoration
        state.update_count = 999
        state.last_updated = datetime(2030, 1, 1, tzinfo=timezone.utc)

        state.apply_undo(undo_data)

        assert state.update_count == original_update_count
        assert state.last_updated == original_last_updated

    def test_apply_undo_raises_for_missing_action(self):
        """Verify apply_undo raises ValueError for missing action."""
        state = create_sms_state()

        with pytest.raises(ValueError, match="missing 'action'"):
            state.apply_undo({})

    def test_apply_undo_raises_for_unknown_action(self):
        """Verify apply_undo raises ValueError for unknown action."""
        state = create_sms_state()

        with pytest.raises(ValueError, match="Unknown undo action"):
            state.apply_undo({
                "action": "unknown_action",
                "state_previous_update_count": 0,
                "state_previous_last_updated": "2025-01-01T00:00:00+00:00",
            })


class TestSMSStateUndoFullCycle:
    """Test full create_undo_data → apply_input → apply_undo cycles.

    GENERAL PATTERN: After undo, state should match pre-apply state.
    """

    def test_full_cycle_send_message_new_conversation(self):
        """Verify send_message (new conversation) → undo returns to original."""
        state = create_sms_state()

        original_snapshot = state.get_snapshot()

        send_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Hello!",
            },
        )

        undo_data = state.create_undo_data(send_input)
        state.apply_input(send_input)

        # Verify message was sent
        assert len(state.messages) == 1
        assert len(state.conversations) == 1

        state.apply_undo(undo_data)

        assert state.get_snapshot() == original_snapshot

    def test_full_cycle_receive_message_new_conversation(self):
        """Verify receive_message (new conversation) → undo returns to original."""
        state = create_sms_state()

        original_snapshot = state.get_snapshot()

        receive_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="receive_message",
            message_data={
                "from_number": "+15551234567",
                "to_numbers": ["+15559876543"],
                "body": "Hello!",
            },
        )

        undo_data = state.create_undo_data(receive_input)
        state.apply_input(receive_input)

        assert len(state.messages) == 1
        assert len(state.conversations) == 1

        state.apply_undo(undo_data)

        assert state.get_snapshot() == original_snapshot

    def test_full_cycle_send_message_existing_conversation(self):
        """Verify send_message to existing conversation → undo works."""
        state = create_sms_state()

        # Setup: Create initial conversation
        initial_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "First message",
            },
        )
        state.apply_input(initial_input)

        # Capture state after initial message
        messages_before = len(state.messages)
        conversations_before = len(state.conversations)
        thread_id = list(state.conversations.keys())[0]
        conv_message_count_before = state.conversations[thread_id].message_count
        update_count_before = state.update_count
        last_updated_before = state.last_updated

        # Send another message
        send_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Second message",
            },
        )

        undo_data = state.create_undo_data(send_input)
        state.apply_input(send_input)

        assert len(state.messages) == messages_before + 1

        state.apply_undo(undo_data)

        assert len(state.messages) == messages_before
        assert len(state.conversations) == conversations_before
        assert state.conversations[thread_id].message_count == conv_message_count_before
        assert state.update_count == update_count_before
        assert state.last_updated == last_updated_before

    def test_full_cycle_update_delivery_status(self):
        """Verify update_delivery_status → undo restores previous status."""
        state = create_sms_state()

        # Send message
        send_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Test",
            },
        )
        state.apply_input(send_input)
        message_id = list(state.messages.keys())[0]

        # Capture before update
        previous_status = state.messages[message_id].delivery_status
        update_count_before = state.update_count
        last_updated_before = state.last_updated

        # Update status
        update_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            action="update_delivery_status",
            delivery_update_data={
                "message_id": message_id,
                "new_status": "delivered",
                "delivered_at": datetime(2025, 1, 1, 12, 31, tzinfo=timezone.utc),
            },
        )

        undo_data = state.create_undo_data(update_input)
        state.apply_input(update_input)

        assert state.messages[message_id].delivery_status == "delivered"

        state.apply_undo(undo_data)

        assert state.messages[message_id].delivery_status == previous_status
        assert state.update_count == update_count_before
        assert state.last_updated == last_updated_before

    def test_full_cycle_add_reaction(self):
        """Verify add_reaction → undo removes added reaction."""
        state = create_sms_state()

        # Receive message
        receive_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="receive_message",
            message_data={
                "from_number": "+15551234567",
                "to_numbers": ["+15559876543"],
                "body": "Test",
            },
        )
        state.apply_input(receive_input)
        message_id = list(state.messages.keys())[0]

        reactions_before = len(state.messages[message_id].reactions)
        update_count_before = state.update_count
        last_updated_before = state.last_updated

        # Add reaction
        reaction_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            action="add_reaction",
            reaction_data={
                "message_id": message_id,
                "phone_number": "+15559876543",
                "emoji": "👍",
            },
        )

        undo_data = state.create_undo_data(reaction_input)
        state.apply_input(reaction_input)

        assert len(state.messages[message_id].reactions) == reactions_before + 1

        state.apply_undo(undo_data)

        assert len(state.messages[message_id].reactions) == reactions_before
        assert state.update_count == update_count_before
        assert state.last_updated == last_updated_before

    def test_full_cycle_remove_reaction(self):
        """Verify remove_reaction → undo restores reaction."""
        state = create_sms_state()

        # Receive message
        receive_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="receive_message",
            message_data={
                "from_number": "+15551234567",
                "to_numbers": ["+15559876543"],
                "body": "Test",
            },
        )
        state.apply_input(receive_input)
        message_id = list(state.messages.keys())[0]

        # Add reaction
        reaction_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            action="add_reaction",
            reaction_data={
                "message_id": message_id,
                "phone_number": "+15559876543",
                "emoji": "👍",
            },
        )
        state.apply_input(reaction_input)
        reaction_id = state.messages[message_id].reactions[0].reaction_id

        reactions_before = len(state.messages[message_id].reactions)
        update_count_before = state.update_count
        last_updated_before = state.last_updated

        # Remove reaction
        remove_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            action="remove_reaction",
            reaction_data={
                "message_id": message_id,
                "phone_number": "+15559876543",
                "reaction_id": reaction_id,
            },
        )

        undo_data = state.create_undo_data(remove_input)
        state.apply_input(remove_input)

        assert len(state.messages[message_id].reactions) == reactions_before - 1

        state.apply_undo(undo_data)

        assert len(state.messages[message_id].reactions) == reactions_before
        assert state.messages[message_id].reactions[0].emoji == "👍"
        assert state.update_count == update_count_before
        assert state.last_updated == last_updated_before

    def test_full_cycle_edit_message(self):
        """Verify edit_message → undo restores original body."""
        state = create_sms_state()

        # Send RCS message (only RCS can be edited)
        send_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Original message",
                "message_type": "rcs",
            },
        )
        state.apply_input(send_input)
        message_id = list(state.messages.keys())[0]

        body_before = state.messages[message_id].body
        edited_at_before = state.messages[message_id].edited_at
        update_count_before = state.update_count
        last_updated_before = state.last_updated

        # Edit message
        edit_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            action="edit_message",
            edit_data={
                "message_id": message_id,
                "new_body": "Edited message",
            },
        )

        undo_data = state.create_undo_data(edit_input)
        state.apply_input(edit_input)

        assert state.messages[message_id].body == "Edited message"
        assert state.messages[message_id].edited_at is not None

        state.apply_undo(undo_data)

        assert state.messages[message_id].body == body_before
        assert state.messages[message_id].edited_at == edited_at_before
        assert state.update_count == update_count_before
        assert state.last_updated == last_updated_before

    def test_full_cycle_delete_message(self):
        """Verify delete_message → undo restores deleted state."""
        state = create_sms_state()

        # Receive message
        receive_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="receive_message",
            message_data={
                "from_number": "+15551234567",
                "to_numbers": ["+15559876543"],
                "body": "Test",
            },
        )
        state.apply_input(receive_input)
        message_id = list(state.messages.keys())[0]

        is_deleted_before = state.messages[message_id].is_deleted
        update_count_before = state.update_count
        last_updated_before = state.last_updated

        # Delete message
        delete_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            action="delete_message",
            delete_data={"message_id": message_id},
        )

        undo_data = state.create_undo_data(delete_input)
        state.apply_input(delete_input)

        assert state.messages[message_id].is_deleted is True

        state.apply_undo(undo_data)

        assert state.messages[message_id].is_deleted == is_deleted_before
        assert state.update_count == update_count_before
        assert state.last_updated == last_updated_before

    def test_full_cycle_create_group(self):
        """Verify create_group → undo removes group."""
        state = create_sms_state()

        original_snapshot = state.get_snapshot()

        group_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="create_group",
            group_data={
                "group_name": "Test Group",
                "creator_number": "+15559876543",
                "participant_numbers": ["+15559876543", "+15551111111"],
            },
        )

        undo_data = state.create_undo_data(group_input)
        state.apply_input(group_input)

        assert len(state.conversations) == 1

        state.apply_undo(undo_data)

        assert state.get_snapshot() == original_snapshot

    def test_full_cycle_update_group(self):
        """Verify update_group → undo restores previous settings."""
        state = create_sms_state()

        # Create group
        group_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="create_group",
            group_data={
                "group_name": "Original Name",
                "creator_number": "+15559876543",
                "participant_numbers": ["+15559876543", "+15551111111"],
            },
        )
        state.apply_input(group_input)
        thread_id = list(state.conversations.keys())[0]

        name_before = state.conversations[thread_id].group_name
        update_count_before = state.update_count
        last_updated_before = state.last_updated

        # Update group
        update_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            action="update_group",
            group_data={
                "thread_id": thread_id,
                "group_name": "New Name",
                "group_photo_url": "https://example.com/photo.jpg",
            },
        )

        undo_data = state.create_undo_data(update_input)
        state.apply_input(update_input)

        assert state.conversations[thread_id].group_name == "New Name"
        assert state.conversations[thread_id].group_photo_url == "https://example.com/photo.jpg"

        state.apply_undo(undo_data)

        assert state.conversations[thread_id].group_name == name_before
        assert state.conversations[thread_id].group_photo_url is None
        assert state.update_count == update_count_before
        assert state.last_updated == last_updated_before

    def test_full_cycle_add_participant(self):
        """Verify add_participant → undo removes participant."""
        state = create_sms_state()

        # Create group (need at least 2 participants)
        group_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="create_group",
            group_data={
                "group_name": "Test Group",
                "creator_number": "+15559876543",
                "participant_numbers": ["+15559876543", "+15551111111"],
            },
        )
        state.apply_input(group_input)
        thread_id = list(state.conversations.keys())[0]

        participants_before = len(state.conversations[thread_id].participants)
        update_count_before = state.update_count
        last_updated_before = state.last_updated

        # Add participant
        add_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            action="add_participant",
            participant_data={
                "thread_id": thread_id,
                "phone_number": "+15552222222",
                "added_by": "+15559876543",
            },
        )

        undo_data = state.create_undo_data(add_input)
        state.apply_input(add_input)

        assert len(state.conversations[thread_id].participants) == participants_before + 1

        state.apply_undo(undo_data)

        assert len(state.conversations[thread_id].participants) == participants_before
        assert state.update_count == update_count_before
        assert state.last_updated == last_updated_before

    def test_full_cycle_remove_participant(self):
        """Verify remove_participant → undo restores participant."""
        state = create_sms_state()

        # Create group with participants (creator must be in list)
        group_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="create_group",
            group_data={
                "group_name": "Test Group",
                "creator_number": "+15559876543",
                "participant_numbers": ["+15559876543", "+15551111111", "+15552222222"],
            },
        )
        state.apply_input(group_input)
        thread_id = list(state.conversations.keys())[0]

        # Find the participant to remove
        target_participant = None
        for p in state.conversations[thread_id].participants:
            if p.phone_number == "+15552222222":
                target_participant = p
                break

        assert target_participant is not None
        assert target_participant.left_at is None
        update_count_before = state.update_count
        last_updated_before = state.last_updated

        # Remove participant
        remove_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            action="remove_participant",
            participant_data={
                "thread_id": thread_id,
                "phone_number": "+15552222222",
            },
        )

        undo_data = state.create_undo_data(remove_input)
        state.apply_input(remove_input)

        # Participant should now have left_at set
        for p in state.conversations[thread_id].participants:
            if p.phone_number == "+15552222222":
                assert p.left_at is not None
                break

        state.apply_undo(undo_data)

        # Participant should be restored (left_at cleared)
        for p in state.conversations[thread_id].participants:
            if p.phone_number == "+15552222222":
                assert p.left_at is None
                break
        assert state.update_count == update_count_before
        assert state.last_updated == last_updated_before

    def test_full_cycle_leave_group(self):
        """Verify leave_group → undo restores user as active participant."""
        state = create_sms_state()

        # Create group with user as participant (creator must be in list)
        group_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="create_group",
            group_data={
                "group_name": "Test Group",
                "creator_number": "+15559876543",
                "participant_numbers": ["+15559876543", "+15551111111", "+15552222222"],
            },
        )
        state.apply_input(group_input)
        thread_id = list(state.conversations.keys())[0]

        update_count_before = state.update_count
        last_updated_before = state.last_updated

        # Leave group
        leave_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            action="leave_group",
            participant_data={"thread_id": thread_id},
        )

        undo_data = state.create_undo_data(leave_input)
        state.apply_input(leave_input)

        # User should now have left_at set
        for p in state.conversations[thread_id].participants:
            if p.phone_number == "+15559876543":
                assert p.left_at is not None
                break

        state.apply_undo(undo_data)

        # User should be active again
        for p in state.conversations[thread_id].participants:
            if p.phone_number == "+15559876543":
                assert p.left_at is None
                break
        assert state.update_count == update_count_before
        assert state.last_updated == last_updated_before

    def test_full_cycle_update_conversation_pin(self):
        """Verify update_conversation (pin) → undo restores unpinned."""
        state = create_sms_state()

        # Create conversation
        send_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Test",
            },
        )
        state.apply_input(send_input)
        thread_id = list(state.conversations.keys())[0]

        is_pinned_before = state.conversations[thread_id].is_pinned
        update_count_before = state.update_count
        last_updated_before = state.last_updated

        # Pin conversation
        update_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            action="update_conversation",
            conversation_update_data={
                "thread_id": thread_id,
                "pin": True,
            },
        )

        undo_data = state.create_undo_data(update_input)
        state.apply_input(update_input)

        assert state.conversations[thread_id].is_pinned is True

        state.apply_undo(undo_data)

        assert state.conversations[thread_id].is_pinned == is_pinned_before
        assert state.update_count == update_count_before
        assert state.last_updated == last_updated_before

    def test_full_cycle_update_conversation_mute(self):
        """Verify update_conversation (mute) → undo restores unmuted."""
        state = create_sms_state()

        # Create conversation
        send_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Test",
            },
        )
        state.apply_input(send_input)
        thread_id = list(state.conversations.keys())[0]

        is_muted_before = state.conversations[thread_id].is_muted
        update_count_before = state.update_count
        last_updated_before = state.last_updated

        # Mute conversation
        update_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            action="update_conversation",
            conversation_update_data={
                "thread_id": thread_id,
                "mute": True,
            },
        )

        undo_data = state.create_undo_data(update_input)
        state.apply_input(update_input)

        assert state.conversations[thread_id].is_muted is True

        state.apply_undo(undo_data)

        assert state.conversations[thread_id].is_muted == is_muted_before
        assert state.update_count == update_count_before
        assert state.last_updated == last_updated_before

    def test_full_cycle_update_conversation_archive(self):
        """Verify update_conversation (archive) → undo restores unarchived."""
        state = create_sms_state()

        # Create conversation
        send_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Test",
            },
        )
        state.apply_input(send_input)
        thread_id = list(state.conversations.keys())[0]

        is_archived_before = state.conversations[thread_id].is_archived
        update_count_before = state.update_count
        last_updated_before = state.last_updated

        # Archive conversation
        update_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            action="update_conversation",
            conversation_update_data={
                "thread_id": thread_id,
                "archive": True,
            },
        )

        undo_data = state.create_undo_data(update_input)
        state.apply_input(update_input)

        assert state.conversations[thread_id].is_archived is True

        state.apply_undo(undo_data)

        assert state.conversations[thread_id].is_archived == is_archived_before
        assert state.update_count == update_count_before
        assert state.last_updated == last_updated_before

    def test_full_cycle_update_conversation_draft(self):
        """Verify update_conversation (draft) → undo restores no draft."""
        state = create_sms_state()

        # Create conversation
        send_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Test",
            },
        )
        state.apply_input(send_input)
        thread_id = list(state.conversations.keys())[0]

        draft_before = state.conversations[thread_id].draft_message
        update_count_before = state.update_count
        last_updated_before = state.last_updated

        # Set draft
        update_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            action="update_conversation",
            conversation_update_data={
                "thread_id": thread_id,
                "draft_message": "Draft text",
            },
        )

        undo_data = state.create_undo_data(update_input)
        state.apply_input(update_input)

        assert state.conversations[thread_id].draft_message == "Draft text"

        state.apply_undo(undo_data)

        assert state.conversations[thread_id].draft_message == draft_before
        assert state.update_count == update_count_before
        assert state.last_updated == last_updated_before

    def test_full_cycle_update_conversation_mark_all_read(self):
        """Verify update_conversation (mark_all_read) → undo restores unread."""
        state = create_sms_state()

        # Create conversation with multiple unread messages
        for i in range(3):
            receive_input = SMSInput(
                timestamp=datetime(2025, 1, 1, 12 + i, 0, tzinfo=timezone.utc),
                action="receive_message",
                message_data={
                    "from_number": "+15551234567",
                    "to_numbers": ["+15559876543"],
                    "body": f"Message {i}",
                },
            )
            state.apply_input(receive_input)

        thread_id = list(state.conversations.keys())[0]

        # Capture which messages are unread
        unread_messages_before = [
            msg.message_id
            for msg in state.messages.values()
            if msg.thread_id == thread_id and not msg.is_read
        ]
        update_count_before = state.update_count
        last_updated_before = state.last_updated

        # Mark all read
        update_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 15, 0, tzinfo=timezone.utc),
            action="update_conversation",
            conversation_update_data={
                "thread_id": thread_id,
                "mark_all_read": True,
            },
        )

        undo_data = state.create_undo_data(update_input)
        state.apply_input(update_input)

        # All should be read
        for msg_id in unread_messages_before:
            assert state.messages[msg_id].is_read is True

        state.apply_undo(undo_data)

        # All should be unread again
        for msg_id in unread_messages_before:
            assert state.messages[msg_id].is_read is False
        assert state.update_count == update_count_before
        assert state.last_updated == last_updated_before

    def test_full_cycle_multiple_operations_reverse_order(self):
        """Verify multiple operations can be undone in reverse order."""
        state = create_sms_state()

        # Op 1: Send RCS message (so we can edit it later)
        send_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Hello!",
                "message_type": "rcs",
            },
        )
        undo1 = state.create_undo_data(send_input)
        state.apply_input(send_input)
        message_id = list(state.messages.keys())[0]

        # Op 2: Add reaction
        reaction_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            action="add_reaction",
            reaction_data={
                "message_id": message_id,
                "phone_number": "+15559876543",
                "emoji": "👍",
            },
        )
        undo2 = state.create_undo_data(reaction_input)
        state.apply_input(reaction_input)

        # Op 3: Edit message
        edit_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            action="edit_message",
            edit_data={
                "message_id": message_id,
                "new_body": "Edited hello!",
            },
        )
        undo3 = state.create_undo_data(edit_input)
        state.apply_input(edit_input)

        # Verify final state
        assert state.messages[message_id].body == "Edited hello!"
        assert len(state.messages[message_id].reactions) == 1
        assert state.update_count == 3

        # Undo op 3 (edit)
        state.apply_undo(undo3)
        assert state.messages[message_id].body == "Hello!"
        assert state.update_count == 2

        # Undo op 2 (reaction)
        state.apply_undo(undo2)
        assert len(state.messages[message_id].reactions) == 0
        assert state.update_count == 1

        # Undo op 1 (send)
        state.apply_undo(undo1)
        assert len(state.messages) == 0
        assert len(state.conversations) == 0
        assert state.update_count == 0

    def test_full_cycle_edit_message_multiple_times(self):
        """Verify multiple edits can be undone sequentially."""
        state = create_sms_state()

        # Send RCS message (only RCS can be edited)
        send_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Original",
                "message_type": "rcs",
            },
        )
        state.apply_input(send_input)
        message_id = list(state.messages.keys())[0]

        # Edit 1
        edit1 = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            action="edit_message",
            edit_data={
                "message_id": message_id,
                "new_body": "First edit",
            },
        )
        undo1 = state.create_undo_data(edit1)
        state.apply_input(edit1)

        # Edit 2
        edit2 = SMSInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            action="edit_message",
            edit_data={
                "message_id": message_id,
                "new_body": "Second edit",
            },
        )
        undo2 = state.create_undo_data(edit2)
        state.apply_input(edit2)

        assert state.messages[message_id].body == "Second edit"

        # Undo edit 2
        state.apply_undo(undo2)
        assert state.messages[message_id].body == "First edit"

        # Undo edit 1
        state.apply_undo(undo1)
        assert state.messages[message_id].body == "Original"
        assert state.messages[message_id].edited_at is None

    def test_full_cycle_group_with_messages(self):
        """Verify create_group with subsequent messages can be undone."""
        state = create_sms_state()

        original_snapshot = state.get_snapshot()

        # Create group (creator must be in participant_numbers)
        group_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="create_group",
            group_data={
                "group_name": "Test Group",
                "creator_number": "+15559876543",
                "participant_numbers": ["+15559876543", "+15551111111", "+15552222222"],
            },
        )
        undo_group = state.create_undo_data(group_input)
        state.apply_input(group_input)
        thread_id = list(state.conversations.keys())[0]

        # Send message to group
        send_input = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551111111", "+15552222222"],
                "body": "Hello group!",
                "thread_id": thread_id,
            },
        )
        undo_send = state.create_undo_data(send_input)
        state.apply_input(send_input)

        # Verify state
        assert len(state.conversations) == 1
        assert len(state.messages) == 1

        # Undo message
        state.apply_undo(undo_send)
        assert len(state.messages) == 0

        # Undo group creation
        state.apply_undo(undo_group)
        assert state.get_snapshot() == original_snapshot