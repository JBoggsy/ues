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

        messages = state.query({})
        assert len(messages) == 3

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

        messages = state.query({"thread_id": thread_a})
        assert len(messages) == 1
        assert messages[0].body == "Thread A"

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

        messages = state.query({"phone_number": "+15551234567"})
        assert len(messages) == 1
        assert messages[0].body == "From Alice"

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
        assert len(outgoing) == 1
        assert outgoing[0].body == "Outgoing"

        incoming = state.query({"direction": "incoming"})
        assert len(incoming) == 1
        assert incoming[0].body == "Incoming"

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

        unread = state.query({"is_read": False})
        assert len(unread) == 1

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

        with_attachments = state.query({"has_attachments": True})
        assert len(with_attachments) == 1
        assert with_attachments[0].body == "Photo"

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

        messages = state.query({"limit": 5})
        assert len(messages) == 5


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
