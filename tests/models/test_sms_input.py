"""Unit tests for SMS input modality.

This module tests both general ModalityInput behavior and SMS-specific features.
"""

from datetime import datetime, timezone

import pytest

from models.modalities.sms_input import MessageAttachmentData, SMSInput


class TestSMSInputInstantiation:
    """Test instantiation patterns for SMSInput.

    GENERAL PATTERN: All ModalityInput subclasses should instantiate with timestamp
    and modality parameters.
    """

    def test_minimal_send_message_instantiation(self):
        """GENERAL PATTERN: Verify SMSInput instantiates with minimal required fields."""
        sms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Hello!",
            },
        )

        assert sms.timestamp == datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        assert sms.modality_type == "sms"
        assert sms.action == "send_message"
        assert sms.message_data["from_number"] == "+15559876543"
        assert sms.message_data["to_numbers"] == ["+15551234567"]
        assert sms.message_data["body"] == "Hello!"

    def test_receive_message_instantiation(self):
        """MODALITY-SPECIFIC: Verify receive_message action."""
        sms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="receive_message",
            message_data={
                "from_number": "+15551234567",
                "to_numbers": ["+15559876543"],
                "body": "Got your message!",
            },
        )

        assert sms.action == "receive_message"
        assert sms.message_data["from_number"] == "+15551234567"

    def test_delivery_status_update_instantiation(self):
        """MODALITY-SPECIFIC: Verify delivery status update action."""
        sms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="update_delivery_status",
            delivery_update_data={
                "message_id": "msg-123",
                "new_status": "delivered",
            },
        )

        assert sms.action == "update_delivery_status"
        assert sms.delivery_update_data["message_id"] == "msg-123"
        assert sms.delivery_update_data["new_status"] == "delivered"

    def test_add_reaction_instantiation(self):
        """MODALITY-SPECIFIC: Verify add reaction action."""
        sms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="add_reaction",
            reaction_data={
                "message_id": "msg-123",
                "phone_number": "+15559876543",
                "emoji": "👍",
            },
        )

        assert sms.action == "add_reaction"
        assert sms.reaction_data["emoji"] == "👍"

    def test_create_group_instantiation(self):
        """MODALITY-SPECIFIC: Verify group creation action."""
        sms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="create_group",
            group_data={
                "creator_number": "+15559876543",
                "participant_numbers": ["+15551234567", "+15555555555"],
                "group_name": "Family Chat",
            },
        )

        assert sms.action == "create_group"
        assert sms.group_data["group_name"] == "Family Chat"
        assert len(sms.group_data["participant_numbers"]) == 2

    def test_default_values(self):
        """GENERAL PATTERN: Verify SMSInput applies correct defaults."""
        sms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Test",
            },
        )

        assert sms.delivery_update_data is None
        assert sms.reaction_data is None
        assert sms.edit_data is None
        assert sms.delete_data is None
        assert sms.group_data is None


class TestMessageAttachmentData:
    """Test MessageAttachmentData helper class.

    MODALITY-SPECIFIC: Attachment metadata for media messages.
    """

    def test_image_attachment(self):
        """MODALITY-SPECIFIC: Verify image attachment data."""
        attachment = MessageAttachmentData(
            filename="photo.jpg",
            size=2048000,
            mime_type="image/jpeg",
            thumbnail_url="https://example.com/thumb.jpg",
        )

        assert attachment.filename == "photo.jpg"
        assert attachment.size == 2048000
        assert attachment.mime_type == "image/jpeg"
        assert attachment.thumbnail_url == "https://example.com/thumb.jpg"

    def test_video_attachment(self):
        """MODALITY-SPECIFIC: Verify video attachment with duration."""
        attachment = MessageAttachmentData(
            filename="video.mp4",
            size=10240000,
            mime_type="video/mp4",
            duration=45,
        )

        assert attachment.mime_type == "video/mp4"
        assert attachment.duration == 45

    def test_audio_attachment(self):
        """MODALITY-SPECIFIC: Verify audio attachment."""
        attachment = MessageAttachmentData(
            filename="voice.m4a",
            size=512000,
            mime_type="audio/mp4",
            duration=30,
        )

        assert attachment.mime_type == "audio/mp4"
        assert attachment.duration == 30


class TestSMSInputValidation:
    """Test SMSInput validation logic.

    MODALITY-SPECIFIC: SMS-specific validation constraints.
    """

    def test_validate_send_message_requires_message_data(self):
        """MODALITY-SPECIFIC: Send message requires message_data."""
        sms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
        )

        with pytest.raises(ValueError, match="message_data is required"):
            sms.validate_input()

    def test_validate_send_message_requires_from_number(self):
        """MODALITY-SPECIFIC: Message requires from_number."""
        sms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "to_numbers": ["+15551234567"],
                "body": "Hello!",
            },
        )

        with pytest.raises(ValueError, match="from_number is required"):
            sms.validate_input()

    def test_validate_send_message_requires_to_numbers(self):
        """MODALITY-SPECIFIC: Message requires to_numbers."""
        sms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "body": "Hello!",
            },
        )

        with pytest.raises(ValueError, match="to_numbers is required"):
            sms.validate_input()

    def test_validate_send_message_requires_body(self):
        """MODALITY-SPECIFIC: Message requires body text."""
        sms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
            },
        )

        with pytest.raises(ValueError, match="body is required"):
            sms.validate_input()

    def test_validate_to_numbers_must_be_list(self):
        """MODALITY-SPECIFIC: to_numbers must be a list."""
        sms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": "+15551234567",  # String instead of list
                "body": "Hello!",
            },
        )

        with pytest.raises(ValueError, match="to_numbers must be a list"):
            sms.validate_input()

    def test_validate_to_numbers_cannot_be_empty(self):
        """MODALITY-SPECIFIC: to_numbers cannot be empty list."""
        sms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": [],  # Empty list
                "body": "Hello!",
            },
        )

        with pytest.raises(ValueError, match="to_numbers cannot be empty"):
            sms.validate_input()

    def test_validate_message_type_must_be_valid(self):
        """MODALITY-SPECIFIC: message_type must be 'sms' or 'rcs'."""
        sms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Hello!",
                "message_type": "invalid",
            },
        )

        with pytest.raises(ValueError, match="must be 'sms' or 'rcs'"):
            sms.validate_input()

    def test_validate_delivery_update_requires_data(self):
        """MODALITY-SPECIFIC: Delivery update requires delivery_update_data."""
        sms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="update_delivery_status",
        )

        with pytest.raises(ValueError, match="delivery_update_data is required"):
            sms.validate_input()

    def test_validate_delivery_update_requires_message_id(self):
        """MODALITY-SPECIFIC: Delivery update requires message_id."""
        sms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="update_delivery_status",
            delivery_update_data={
                "new_status": "delivered",
            },
        )

        with pytest.raises(ValueError, match="message_id is required"):
            sms.validate_input()

    def test_validate_delivery_status_must_be_valid(self):
        """MODALITY-SPECIFIC: new_status must be valid value."""
        sms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="update_delivery_status",
            delivery_update_data={
                "message_id": "msg-123",
                "new_status": "invalid",
            },
        )

        with pytest.raises(ValueError, match="must be one of"):
            sms.validate_input()

    def test_validate_add_reaction_requires_emoji(self):
        """MODALITY-SPECIFIC: add_reaction requires emoji field."""
        sms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="add_reaction",
            reaction_data={
                "message_id": "msg-123",
                "phone_number": "+15559876543",
            },
        )

        with pytest.raises(ValueError, match="emoji is required"):
            sms.validate_input()

    def test_validate_remove_reaction_requires_reaction_id(self):
        """MODALITY-SPECIFIC: remove_reaction requires reaction_id field."""
        sms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="remove_reaction",
            reaction_data={
                "message_id": "msg-123",
                "phone_number": "+15559876543",
            },
        )

        with pytest.raises(ValueError, match="reaction_id is required"):
            sms.validate_input()

    def test_validate_edit_message_requires_new_body(self):
        """MODALITY-SPECIFIC: edit_message requires new_body."""
        sms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="edit_message",
            edit_data={
                "message_id": "msg-123",
            },
        )

        with pytest.raises(ValueError, match="new_body is required"):
            sms.validate_input()

    def test_validate_delete_message_requires_message_id(self):
        """MODALITY-SPECIFIC: delete_message requires message_id."""
        sms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="delete_message",
            delete_data={
                "message_id": "msg-123",
            },
        )

        # Should not raise - message_id is provided
        sms.validate_input()

    def test_validate_create_group_requires_participants(self):
        """MODALITY-SPECIFIC: create_group requires participant_numbers."""
        sms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="create_group",
            group_data={
                "creator_number": "+15559876543",
            },
        )

        with pytest.raises(ValueError, match="participant_numbers is required"):
            sms.validate_input()

    def test_validate_create_group_minimum_participants(self):
        """MODALITY-SPECIFIC: Groups need at least 2 participants."""
        sms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="create_group",
            group_data={
                "creator_number": "+15559876543",
                "participant_numbers": ["+15559876543"],  # Only 1
            },
        )

        with pytest.raises(ValueError, match="at least 2 participants"):
            sms.validate_input()

    def test_validate_update_group_requires_thread_id(self):
        """MODALITY-SPECIFIC: update_group requires thread_id."""
        sms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="update_group",
            group_data={
                "group_name": "New Name",
            },
        )

        with pytest.raises(ValueError, match="thread_id is required"):
            sms.validate_input()

    def test_validate_conversation_update_requires_at_least_one_field(self):
        """MODALITY-SPECIFIC: Conversation update needs at least one change."""
        sms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="update_conversation",
            conversation_update_data={
                "thread_id": "thread-123",
            },
        )

        with pytest.raises(ValueError, match="at least one update"):
            sms.validate_input()


class TestSMSInputMethods:
    """Test SMSInput methods.

    GENERAL PATTERN: Test interface methods defined by ModalityInput.
    """

    def test_get_affected_entities_send_message(self):
        """GENERAL PATTERN: Verify affected entities for message send."""
        sms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Hello!",
                "thread_id": "thread-123",
            },
        )

        entities = sms.get_affected_entities()
        assert "thread-123" in entities

    def test_get_affected_entities_new_conversation(self):
        """MODALITY-SPECIFIC: New conversation has special entity marker."""
        sms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Hello!",
            },
        )

        entities = sms.get_affected_entities()
        assert "new_conversation" in entities

    def test_get_summary_send_message(self):
        """GENERAL PATTERN: Verify summary for send_message."""
        sms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Hello, this is a test message!",
            },
        )

        summary = sms.get_summary()
        assert "Send SMS" in summary
        assert "+15559876543" in summary
        assert "Hello" in summary

    def test_get_summary_receive_message(self):
        """GENERAL PATTERN: Verify summary for receive_message."""
        sms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="receive_message",
            message_data={
                "from_number": "+15551234567",
                "to_numbers": ["+15559876543"],
                "body": "Got it, thanks!",
            },
        )

        summary = sms.get_summary()
        assert "Receive SMS" in summary
        assert "+15551234567" in summary

    def test_get_summary_long_message_truncated(self):
        """MODALITY-SPECIFIC: Long message bodies are truncated in summary."""
        long_body = "A" * 100  # 100 character message
        sms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": long_body,
            },
        )

        summary = sms.get_summary()
        assert "..." in summary  # Should be truncated

    def test_get_summary_group_message(self):
        """MODALITY-SPECIFIC: Summary shows recipient count for group."""
        sms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567", "+15555555555", "+15556666666"],
                "body": "Group message",
            },
        )

        summary = sms.get_summary()
        assert "3 recipients" in summary

    def test_get_summary_create_group(self):
        """MODALITY-SPECIFIC: Summary shows group name and participant count."""
        sms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="create_group",
            group_data={
                "creator_number": "+15559876543",
                "participant_numbers": ["+15551234567", "+15555555555"],
                "group_name": "Family Chat",
            },
        )

        summary = sms.get_summary()
        assert "Create group" in summary
        assert "Family Chat" in summary
        assert "2 participants" in summary

    def test_should_merge_with(self):
        """GENERAL PATTERN: SMS inputs don't merge."""
        sms1 = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "First message",
            },
        )
        sms2 = SMSInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Second message",
            },
        )

        assert sms1.should_merge_with(sms2) is False


class TestSMSInputSerialization:
    """Test SMSInput serialization.

    GENERAL PATTERN: Verify input can be serialized and deserialized.
    """

    def test_simple_serialization(self):
        """GENERAL PATTERN: Verify input serializes and deserializes."""
        original = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Hello!",
            },
        )

        dumped = original.model_dump()
        restored = SMSInput.model_validate(dumped)

        assert restored.timestamp == original.timestamp
        assert restored.action == original.action
        assert restored.message_data == original.message_data

    def test_complex_serialization(self):
        """Verify complex input with attachments serializes."""
        original = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Check this out!",
                "message_type": "rcs",
                "attachments": [
                    {
                        "filename": "photo.jpg",
                        "size": 2048000,
                        "mime_type": "image/jpeg",
                    }
                ],
            },
        )

        dumped = original.model_dump()
        restored = SMSInput.model_validate(dumped)

        assert len(restored.message_data["attachments"]) == 1
        assert restored.message_data["attachments"][0]["filename"] == "photo.jpg"


class TestSMSInputEdgeCases:
    """Test SMSInput edge cases.

    GENERAL PATTERN: Test boundary conditions and edge cases.
    """

    def test_multiple_recipients(self):
        """MODALITY-SPECIFIC: Message can have many recipients."""
        sms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": [f"+1555{i:07d}" for i in range(20)],
                "body": "Mass message",
            },
        )

        assert len(sms.message_data["to_numbers"]) == 20

    def test_empty_body_allowed(self):
        """MODALITY-SPECIFIC: Messages can have empty body if they have attachments."""
        sms = SMSInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "",  # Empty string
                "attachments": [
                    {
                        "filename": "photo.jpg",
                        "size": 1024,
                        "mime_type": "image/jpeg",
                    }
                ],
            },
        )

        assert sms.message_data["body"] == ""

    def test_all_sms_actions(self):
        """MODALITY-SPECIFIC: Test all valid action types."""
        actions = [
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

        for action in actions:
            sms = SMSInput(
                timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
                action=action,
            )
            assert sms.action == action


class TestSMSInputFromFixtures:
    """Test using pre-built SMS fixtures.

    GENERAL PATTERN: Verify fixtures work correctly.
    """

    def test_create_sms_input_fixture(self):
        """Verify create_sms_input factory function."""
        from tests.fixtures.modalities.sms import create_sms_input

        sms = create_sms_input(
            action="send_message",
            message_data={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Test",
            },
        )

        assert sms.modality_type == "sms"
        assert sms.action == "send_message"

    def test_simple_receive_fixture(self):
        """Verify SIMPLE_RECEIVE fixture."""
        from tests.fixtures.modalities.sms import SIMPLE_RECEIVE

        assert SIMPLE_RECEIVE.action == "receive_message"
        assert SIMPLE_RECEIVE.message_data is not None

    def test_group_message_fixture(self):
        """Verify GROUP_MESSAGE_RECEIVE fixture."""
        from tests.fixtures.modalities.sms import GROUP_MESSAGE_RECEIVE

        assert GROUP_MESSAGE_RECEIVE.action == "receive_message"
        assert "is_group" in GROUP_MESSAGE_RECEIVE.message_data

    def test_mms_with_image_fixture(self):
        """Verify MMS_WITH_IMAGE fixture with attachments."""
        from tests.fixtures.modalities.sms import MMS_WITH_IMAGE

        assert "attachments" in MMS_WITH_IMAGE.message_data
        assert len(MMS_WITH_IMAGE.message_data["attachments"]) > 0
