"""Fixtures for SMS modality."""

from datetime import datetime, timezone

from models.modalities.sms_input import SMSInput, MessageAttachmentData
from models.modalities.sms_state import SMSState


def create_sms_input(
    action: str = "receive_message",
    timestamp: datetime | None = None,
    **kwargs,
) -> SMSInput:
    """Create an SMSInput with sensible defaults.

    Args:
        action: SMS action type (default: "receive_message").
        timestamp: When action occurred (defaults to now).
        **kwargs: Additional fields including action-specific data.

    Returns:
        SMSInput instance ready for testing.
    """
    return SMSInput(
        action=action,
        timestamp=timestamp or datetime.now(timezone.utc),
        **kwargs,
    )


def create_sms_state(
    user_phone_number: str = "+15559876543",
    last_updated: datetime | None = None,
    **kwargs,
) -> SMSState:
    """Create an SMSState with sensible defaults.

    Args:
        user_phone_number: The simulated user's phone number (default: +15559876543).
        last_updated: When state was last updated (defaults to now).
        **kwargs: Additional fields to override.

    Returns:
        SMSState instance ready for testing.
    """
    return SMSState(
        user_phone_number=user_phone_number,
        last_updated=last_updated or datetime.now(timezone.utc),
        **kwargs,
    )


# Pre-built SMS examples
SIMPLE_RECEIVE = create_sms_input(
    action="receive_message",
    message_data={
        "from_number": "+15551234567",
        "to_number": "+15559876543",
        "body": "Hey, are we still on for lunch?",
        "message_type": "sms",
    },
)

SIMPLE_SEND = create_sms_input(
    action="send_message",
    message_data={
        "from_number": "+15559876543",
        "to_number": "+15551234567",
        "body": "Yes! See you at noon.",
        "message_type": "sms",
    },
)

GROUP_MESSAGE_RECEIVE = create_sms_input(
    action="receive_message",
    message_data={
        "from_number": "+15551234567",
        "to_number": "+15559876543",
        "body": "Who wants to grab dinner tonight?",
        "message_type": "rcs",
        "conversation_id": "group-family-chat",
        "is_group": True,
        "group_participants": ["+15551234567", "+15559876543", "+15555555555"],
    },
)

GROUP_MESSAGE_SEND = create_sms_input(
    action="send_message",
    message_data={
        "from_number": "+15559876543",
        "to_number": "+15559876543",
        "body": "I'm in! What time?",
        "message_type": "rcs",
        "conversation_id": "group-family-chat",
        "is_group": True,
        "group_participants": ["+15551234567", "+15559876543", "+15555555555"],
    },
)

MMS_WITH_IMAGE = create_sms_input(
    action="receive_message",
    message_data={
        "from_number": "+15551234567",
        "to_number": "+15559876543",
        "body": "Check out this photo!",
        "message_type": "rcs",
        "attachments": [
            {
                "filename": "vacation.jpg",
                "size": 2048000,
                "mime_type": "image/jpeg",
                "thumbnail_url": "https://example.com/thumb.jpg",
            }
        ],
    },
)

VIDEO_MESSAGE = create_sms_input(
    action="receive_message",
    message_data={
        "from_number": "+15551234567",
        "to_number": "+15559876543",
        "body": "Here's the video from yesterday",
        "message_type": "rcs",
        "attachments": [
            {
                "filename": "video.mp4",
                "size": 10240000,
                "mime_type": "video/mp4",
                "duration": 30,
            }
        ],
    },
)

DELIVERY_STATUS_UPDATE = create_sms_input(
    action="update_delivery_status",
    delivery_update_data={
        "message_id": "msg-12345",
        "new_status": "delivered",
        "conversation_id": "conv-1",
    },
)

READ_STATUS_UPDATE = create_sms_input(
    action="update_delivery_status",
    delivery_update_data={
        "message_id": "msg-12345",
        "new_status": "read",
        "conversation_id": "conv-1",
    },
)

ADD_REACTION = create_sms_input(
    action="add_reaction",
    reaction_data={
        "message_id": "msg-12345",
        "emoji": "👍",
        "phone_number": "+15559876543",
        "conversation_id": "conv-1",
    },
)

REMOVE_REACTION = create_sms_input(
    action="remove_reaction",
    reaction_data={
        "message_id": "msg-12345",
        "emoji": "👍",
        "phone_number": "+15559876543",
        "conversation_id": "conv-1",
    },
)

EDIT_MESSAGE = create_sms_input(
    action="edit_message",
    edit_data={
        "message_id": "msg-12345",
        "new_body": "Corrected message text",
        "conversation_id": "conv-1",
    },
)

DELETE_MESSAGE = create_sms_input(
    action="delete_message",
    delete_data={
        "message_id": "msg-12345",
        "conversation_id": "conv-1",
        "delete_for_everyone": False,
    },
)

CREATE_GROUP = create_sms_input(
    action="create_group",
    group_data={
        "group_name": "Weekend Plans",
        "participants": ["+15551234567", "+15559876543", "+15555555555"],
        "creator_number": "+15559876543",
    },
)

ADD_PARTICIPANT = create_sms_input(
    action="add_participant",
    participant_data={
        "conversation_id": "group-weekend",
        "phone_number": "+15554444444",
        "added_by": "+15559876543",
    },
)

REMOVE_PARTICIPANT = create_sms_input(
    action="remove_participant",
    participant_data={
        "conversation_id": "group-weekend",
        "phone_number": "+15554444444",
        "removed_by": "+15559876543",
    },
)

UPDATE_CONVERSATION = create_sms_input(
    action="update_conversation",
    conversation_update_data={
        "conversation_id": "conv-1",
        "is_muted": True,
        "mute_until": datetime(2025, 1, 16, tzinfo=timezone.utc),
    },
)

ARCHIVE_CONVERSATION = create_sms_input(
    action="update_conversation",
    conversation_update_data={
        "conversation_id": "conv-1",
        "is_archived": True,
    },
)


# State examples
EMPTY_SMS_STATE = create_sms_state()


# Invalid examples for validation testing
INVALID_SMS_INPUTS = {
    "bad_phone_number": {
        "action": "send_message",
        "timestamp": datetime.now(timezone.utc),
        "message_data": {
            "from_number": "not-a-phone",
            "to_number": "+15551234567",
            "body": "Test",
        },
    },
    "missing_message_data": {
        "action": "send_message",
        "timestamp": datetime.now(timezone.utc),
    },
}


# JSON fixtures for API testing
SMS_JSON_EXAMPLES = {
    "simple_receive": {
        "modality_type": "sms",
        "timestamp": "2025-01-15T10:30:00Z",
        "action": "receive_message",
        "message_data": {
            "from_number": "+15551234567",
            "to_number": "+15559876543",
            "body": "Hello!",
            "message_type": "sms",
        },
    },
    "with_image": {
        "modality_type": "sms",
        "timestamp": "2025-01-15T14:00:00Z",
        "action": "receive_message",
        "message_data": {
            "from_number": "+15551234567",
            "to_number": "+15559876543",
            "body": "Check this out",
            "message_type": "rcs",
            "attachments": [
                {
                    "filename": "photo.jpg",
                    "size": 1024000,
                    "mime_type": "image/jpeg",
                }
            ],
        },
    },
    "group_message": {
        "modality_type": "sms",
        "timestamp": "2025-01-15T16:00:00Z",
        "action": "receive_message",
        "message_data": {
            "from_number": "+15551234567",
            "to_number": "+15559876543",
            "body": "Group chat message",
            "message_type": "rcs",
            "conversation_id": "group-1",
            "is_group": True,
            "group_participants": ["+15551234567", "+15559876543", "+15555555555"],
        },
    },
}
