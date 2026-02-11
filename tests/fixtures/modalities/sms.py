"""Fixtures for SMS modality."""

from datetime import datetime, timezone

from ues.models.modalities.sms_input import SMSInput, MessageAttachmentData
from ues.models.modalities.sms_state import SMSState


def create_sms_input(
    operation: str = "receive_message",
    timestamp: datetime | None = None,
    **kwargs,
) -> SMSInput:
    """Create an SMSInput with sensible defaults.

    Args:
        operation: SMS operation type (default: "receive_message").
        timestamp: When operation occurred (defaults to now).
        **kwargs: Additional typed fields for the SMSInput.

    Returns:
        SMSInput instance ready for testing.
    """
    return SMSInput(
        operation=operation,
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


# Pre-built SMS examples using typed top-level fields
SIMPLE_RECEIVE = create_sms_input(
    operation="receive_message",
    from_number="+15551234567",
    to_numbers=["+15559876543"],
    body="Hey, are we still on for lunch?",
    message_type="sms",
)

SIMPLE_SEND = create_sms_input(
    operation="send_message",
    from_number="+15559876543",
    to_numbers=["+15551234567"],
    body="Yes! See you at noon.",
    message_type="sms",
)

GROUP_MESSAGE_RECEIVE = create_sms_input(
    operation="receive_message",
    from_number="+15551234567",
    to_numbers=["+15559876543", "+15555555555"],
    body="Who wants to grab dinner tonight?",
    message_type="rcs",
    thread_id="group-family-chat",
)

GROUP_MESSAGE_SEND = create_sms_input(
    operation="send_message",
    from_number="+15559876543",
    to_numbers=["+15551234567", "+15555555555"],
    body="I'm in! What time?",
    message_type="rcs",
    thread_id="group-family-chat",
)

MMS_WITH_IMAGE = create_sms_input(
    operation="receive_message",
    from_number="+15551234567",
    to_numbers=["+15559876543"],
    body="Check out this photo!",
    message_type="rcs",
    attachments=[
        MessageAttachmentData(
            filename="vacation.jpg",
            size=2048000,
            mime_type="image/jpeg",
            thumbnail_url="https://example.com/thumb.jpg",
        )
    ],
)

VIDEO_MESSAGE = create_sms_input(
    operation="receive_message",
    from_number="+15551234567",
    to_numbers=["+15559876543"],
    body="Here's the video from yesterday",
    message_type="rcs",
    attachments=[
        MessageAttachmentData(
            filename="video.mp4",
            size=10240000,
            mime_type="video/mp4",
            duration=30,
        )
    ],
)

DELIVERY_STATUS_UPDATE = create_sms_input(
    operation="update_delivery_status",
    message_id="msg-12345",
    new_status="delivered",
    thread_id="conv-1",
)

READ_STATUS_UPDATE = create_sms_input(
    operation="update_delivery_status",
    message_id="msg-12345",
    new_status="read",
    thread_id="conv-1",
)

ADD_REACTION = create_sms_input(
    operation="add_reaction",
    message_id="msg-12345",
    emoji="👍",
    phone_number="+15559876543",
    thread_id="conv-1",
)

REMOVE_REACTION = create_sms_input(
    operation="remove_reaction",
    message_id="msg-12345",
    reaction_id="reaction-123",
    phone_number="+15559876543",
    thread_id="conv-1",
)

EDIT_MESSAGE = create_sms_input(
    operation="edit_message",
    message_id="msg-12345",
    new_body="Corrected message text",
    thread_id="conv-1",
)

DELETE_MESSAGE = create_sms_input(
    operation="delete_message",
    message_id="msg-12345",
    delete_for_everyone=False,
)

CREATE_GROUP = create_sms_input(
    operation="create_group",
    group_name="Weekend Plans",
    participant_numbers=["+15551234567", "+15559876543", "+15555555555"],
    creator_number="+15559876543",
)

ADD_PARTICIPANT = create_sms_input(
    operation="add_participant",
    thread_id="group-weekend",
    phone_number="+15554444444",
    added_by="+15559876543",
)

REMOVE_PARTICIPANT = create_sms_input(
    operation="remove_participant",
    thread_id="group-weekend",
    phone_number="+15554444444",
    removed_by="+15559876543",
)

UPDATE_CONVERSATION = create_sms_input(
    operation="update_conversation",
    thread_id="conv-1",
    mute=True,
    mute_until=datetime(2025, 1, 16, tzinfo=timezone.utc),
)

ARCHIVE_CONVERSATION = create_sms_input(
    operation="update_conversation",
    thread_id="conv-1",
    archive=True,
)


# State examples
EMPTY_SMS_STATE = create_sms_state()


# Invalid examples for validation testing
INVALID_SMS_INPUTS = {
    "bad_phone_number": {
        "operation": "send_message",
        "timestamp": datetime.now(timezone.utc),
        "from_number": "not-a-phone",
        "to_numbers": ["+15551234567"],
        "body": "Test",
    },
    "missing_body": {
        "operation": "send_message",
        "timestamp": datetime.now(timezone.utc),
        "from_number": "+15559876543",
        "to_numbers": ["+15551234567"],
        # body is missing
    },
}


# JSON fixtures for API testing
SMS_JSON_EXAMPLES = {
    "simple_receive": {
        "modality_type": "sms",
        "timestamp": "2025-01-15T10:30:00Z",
        "operation": "receive_message",
        "from_number": "+15551234567",
        "to_numbers": ["+15559876543"],
        "body": "Hello!",
        "message_type": "sms",
    },
    "with_image": {
        "modality_type": "sms",
        "timestamp": "2025-01-15T14:00:00Z",
        "operation": "receive_message",
        "from_number": "+15551234567",
        "to_numbers": ["+15559876543"],
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
    "group_message": {
        "modality_type": "sms",
        "timestamp": "2025-01-15T16:00:00Z",
        "operation": "receive_message",
        "from_number": "+15551234567",
        "to_numbers": ["+15559876543", "+15555555555"],
        "body": "Group chat message",
        "message_type": "rcs",
        "thread_id": "group-1",
    },
}
