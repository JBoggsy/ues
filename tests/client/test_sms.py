"""Unit tests for the SMSClient and AsyncSMSClient.

This module tests the SMS modality sub-client that provides methods for
sending, receiving, and managing SMS and RCS messages.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from client._sms import (
    AsyncSMSClient,
    GroupParticipant,
    MessageAttachment,
    MessageReaction,
    SMSClient,
    SMSConversation,
    SMSMessage,
    SMSQueryResponse,
    SMSStateResponse,
)
from client.models import ModalityActionResponse


# =============================================================================
# Response Model Tests
# =============================================================================


class TestMessageAttachment:
    """Tests for the MessageAttachment model."""

    def test_instantiation_with_all_fields(self):
        """Test creating a MessageAttachment with all fields."""
        attachment = MessageAttachment(
            filename="photo.jpg",
            size=2048,
            mime_type="image/jpeg",
            thumbnail_url="https://example.com/thumb.jpg",
            duration=None,
        )
        assert attachment.filename == "photo.jpg"
        assert attachment.size == 2048
        assert attachment.mime_type == "image/jpeg"
        assert attachment.thumbnail_url == "https://example.com/thumb.jpg"

    def test_instantiation_video(self):
        """Test creating a video attachment with duration."""
        attachment = MessageAttachment(
            filename="video.mp4",
            size=10240,
            mime_type="video/mp4",
            thumbnail_url="https://example.com/thumb.jpg",
            duration=30,
        )
        assert attachment.duration == 30


class TestMessageReaction:
    """Tests for the MessageReaction model."""

    def test_instantiation(self):
        """Test creating a MessageReaction."""
        reaction = MessageReaction(
            emoji="👍",
            phone_number="+1234567890",
            timestamp=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
        )
        assert reaction.emoji == "👍"
        assert reaction.phone_number == "+1234567890"


class TestSMSMessage:
    """Tests for the SMSMessage model."""

    def test_instantiation_with_all_fields(self):
        """Test creating an SMSMessage with all fields."""
        message = SMSMessage(
            message_id="sms-123",
            thread_id="thread-456",
            from_number="+1234567890",
            to_numbers=["+0987654321"],
            body="Hello!",
            message_type="rcs",
            direction="outgoing",
            sent_at=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
            received_at=datetime(2025, 1, 15, 10, 1, tzinfo=timezone.utc),
            is_read=True,
            read_at=datetime(2025, 1, 15, 10, 2, tzinfo=timezone.utc),
            delivery_status="delivered",
            attachments=[],
            reactions=[],
            replied_to_message_id="sms-100",
            is_deleted=False,
            deleted_at=None,
            is_spam=False,
        )
        assert message.message_id == "sms-123"
        assert message.message_type == "rcs"
        assert message.direction == "outgoing"
        assert message.delivery_status == "delivered"

    def test_instantiation_with_defaults(self):
        """Test creating an SMSMessage with only required fields."""
        message = SMSMessage(
            message_id="sms-123",
            thread_id="thread-456",
            from_number="+1234567890",
            to_numbers=["+0987654321"],
            body="Hello!",
            sent_at=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
        )
        assert message.message_type == "sms"
        assert message.direction == "outgoing"
        assert message.is_read is False
        assert message.delivery_status == "sent"
        assert message.is_deleted is False


class TestSMSConversation:
    """Tests for the SMSConversation model."""

    def test_instantiation(self):
        """Test creating an SMSConversation."""
        now = datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc)
        conversation = SMSConversation(
            thread_id="thread-123",
            conversation_type="one_on_one",
            participants=[
                GroupParticipant(
                    phone_number="+1234567890",
                    joined_at=now,
                ),
                GroupParticipant(
                    phone_number="+0987654321",
                    joined_at=now,
                ),
            ],
            is_group=False,
            group_name=None,
            message_ids=["sms-1", "sms-2"],
            created_at=now,
            last_message_at=datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc),
            message_count=2,
            unread_count=1,
            is_muted=False,
            is_archived=False,
        )
        assert conversation.thread_id == "thread-123"
        assert len(conversation.participants) == 2
        assert conversation.message_count == 2

    def test_instantiation_group(self):
        """Test creating a group conversation."""
        now = datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc)
        conversation = SMSConversation(
            thread_id="group-123",
            conversation_type="group",
            participants=[
                GroupParticipant(
                    phone_number="+111",
                    display_name="Alice",
                    joined_at=now,
                    is_admin=True,
                ),
                GroupParticipant(
                    phone_number="+222",
                    display_name="Bob",
                    joined_at=now,
                ),
                GroupParticipant(
                    phone_number="+333",
                    display_name="Carol",
                    joined_at=now,
                ),
            ],
            is_group=True,
            group_name="Friends Group",
            message_ids=[],
            created_at=now,
            last_message_at=now,
        )
        assert conversation.is_group is True
        assert conversation.group_name == "Friends Group"


class TestSMSStateResponse:
    """Tests for the SMSStateResponse model."""

    def test_instantiation(self):
        """Test creating an SMSStateResponse."""
        response = SMSStateResponse(
            modality_type="sms",
            current_time=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
            user_phone_number="+1234567890",
            messages={},
            conversations={},
            total_message_count=10,
            unread_count=3,
            total_conversation_count=5,
        )
        assert response.modality_type == "sms"
        assert response.user_phone_number == "+1234567890"
        assert response.total_message_count == 10


class TestSMSQueryResponse:
    """Tests for the SMSQueryResponse model."""

    def test_instantiation(self):
        """Test creating an SMSQueryResponse."""
        response = SMSQueryResponse(
            modality_type="sms",
            messages=[],
            total_count=5,
            returned_count=5,
            query={"is_read": False},
        )
        assert response.total_count == 5


# =============================================================================
# SMSClient Tests
# =============================================================================


class TestSMSClientGetState:
    """Tests for SMSClient.get_state() method."""

    def test_get_state(self):
        """Test getting SMS state."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "modality_type": "sms",
            "current_time": "2025-01-15T10:00:00+00:00",
            "user_phone_number": "+1234567890",
            "messages": {},
            "conversations": {},
            "total_message_count": 10,
            "unread_count": 3,
            "total_conversation_count": 5,
        }

        client = SMSClient(mock_http)
        result = client.get_state()

        mock_http.get.assert_called_once_with("/sms/state", params=None)
        assert isinstance(result, SMSStateResponse)
        assert result.total_message_count == 10


class TestSMSClientQuery:
    """Tests for SMSClient.query() method."""

    def test_query_no_filters(self):
        """Test querying messages with no filters."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "modality_type": "sms",
            "messages": [],
            "total_count": 0,
            "returned_count": 0,
            "query": {},
        }

        client = SMSClient(mock_http)
        result = client.query()

        mock_http.post.assert_called_once_with("/sms/query", json={}, params=None)
        assert isinstance(result, SMSQueryResponse)

    def test_query_with_filters(self):
        """Test querying messages with various filters."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "modality_type": "sms",
            "messages": [],
            "total_count": 5,
            "returned_count": 5,
            "query": {"is_read": False, "message_type": "sms"},
        }

        client = SMSClient(mock_http)
        result = client.query(
            thread_id="thread-123",
            from_number="+1234567890",
            message_type="sms",
            is_read=False,
            direction="incoming",
            limit=10,
        )

        call_args = mock_http.post.call_args
        assert call_args[1]["json"]["thread_id"] == "thread-123"
        assert call_args[1]["json"]["from_number"] == "+1234567890"
        assert call_args[1]["json"]["message_type"] == "sms"
        assert call_args[1]["json"]["is_read"] is False
        assert call_args[1]["json"]["direction"] == "incoming"
        assert call_args[1]["json"]["limit"] == 10

    def test_query_with_date_filters(self):
        """Test querying messages with date filters."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "modality_type": "sms",
            "messages": [],
            "total_count": 0,
            "returned_count": 0,
            "query": {},
        }

        client = SMSClient(mock_http)
        sent_after = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
        sent_before = datetime(2025, 1, 15, 0, 0, tzinfo=timezone.utc)
        client.query(sent_after=sent_after, sent_before=sent_before)

        call_args = mock_http.post.call_args
        assert "sent_after" in call_args[1]["json"]
        assert "sent_before" in call_args[1]["json"]


class TestSMSClientSend:
    """Tests for SMSClient.send() method."""

    def test_send_minimal(self):
        """Test sending an SMS with minimal parameters."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "SMS sent successfully",
            "modality": "sms",
        }

        client = SMSClient(mock_http)
        result = client.send(
            from_number="+1234567890",
            to_numbers=["+0987654321"],
            body="Hello!",
        )

        mock_http.post.assert_called_once()
        call_args = mock_http.post.call_args
        assert call_args[0][0] == "/sms/send"
        assert call_args[1]["json"]["from_number"] == "+1234567890"
        assert call_args[1]["json"]["to_numbers"] == ["+0987654321"]
        assert call_args[1]["json"]["body"] == "Hello!"
        assert call_args[1]["json"]["message_type"] == "sms"
        assert isinstance(result, ModalityActionResponse)

    def test_send_rcs_with_attachments(self):
        """Test sending an RCS message with attachments."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "RCS sent",
            "modality": "sms",
        }

        client = SMSClient(mock_http)
        result = client.send(
            from_number="+1234567890",
            to_numbers=["+0987654321"],
            body="Check this out!",
            message_type="rcs",
            attachments=[{"filename": "photo.jpg", "size": 2048, "mime_type": "image/jpeg"}],
            replied_to_message_id="sms-100",
        )

        call_args = mock_http.post.call_args
        assert call_args[1]["json"]["message_type"] == "rcs"
        assert len(call_args[1]["json"]["attachments"]) == 1
        assert call_args[1]["json"]["replied_to_message_id"] == "sms-100"


class TestSMSClientReceive:
    """Tests for SMSClient.receive() method."""

    def test_receive_minimal(self):
        """Test receiving an SMS with minimal parameters."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "SMS received",
            "modality": "sms",
        }

        client = SMSClient(mock_http)
        result = client.receive(
            from_number="+0987654321",
            to_numbers=["+1234567890"],
            body="Incoming message!",
        )

        mock_http.post.assert_called_once()
        call_args = mock_http.post.call_args
        assert call_args[0][0] == "/sms/receive"
        assert isinstance(result, ModalityActionResponse)

    def test_receive_with_sent_at(self):
        """Test receiving an SMS with custom sent time."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "SMS received",
            "modality": "sms",
        }

        client = SMSClient(mock_http)
        sent_at = datetime(2025, 1, 15, 9, 0, tzinfo=timezone.utc)
        client.receive(
            from_number="+0987654321",
            to_numbers=["+1234567890"],
            body="Incoming message!",
            sent_at=sent_at,
        )

        call_args = mock_http.post.call_args
        assert "sent_at" in call_args[1]["json"]


class TestSMSClientActions:
    """Tests for SMSClient action methods (read, unread, delete, react)."""

    def test_read(self):
        """Test marking messages as read."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Marked as read",
            "modality": "sms",
        }

        client = SMSClient(mock_http)
        result = client.read(message_ids=["sms-1", "sms-2"])

        mock_http.post.assert_called_once_with(
            "/sms/read",
            json={"message_ids": ["sms-1", "sms-2"]},
            params=None,
        )
        assert isinstance(result, ModalityActionResponse)

    def test_unread(self):
        """Test marking messages as unread."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Marked as unread",
            "modality": "sms",
        }

        client = SMSClient(mock_http)
        result = client.unread(message_ids=["sms-1"])

        mock_http.post.assert_called_once_with(
            "/sms/unread",
            json={"message_ids": ["sms-1"]},
            params=None,
        )

    def test_delete(self):
        """Test deleting messages."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Messages deleted",
            "modality": "sms",
        }

        client = SMSClient(mock_http)
        result = client.delete(message_ids=["sms-1", "sms-2"])

        mock_http.post.assert_called_once_with(
            "/sms/delete",
            json={"message_ids": ["sms-1", "sms-2"]},
            params=None,
        )

    def test_react(self):
        """Test adding a reaction to a message."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Reaction added",
            "modality": "sms",
        }

        client = SMSClient(mock_http)
        result = client.react(
            message_id="sms-123",
            phone_number="+1234567890",
            emoji="👍",
        )

        mock_http.post.assert_called_once_with(
            "/sms/react",
            json={
                "message_id": "sms-123",
                "phone_number": "+1234567890",
                "emoji": "👍",
            },
            params=None,
        )
        assert isinstance(result, ModalityActionResponse)


# =============================================================================
# AsyncSMSClient Tests
# =============================================================================


class TestAsyncSMSClientGetState:
    """Tests for AsyncSMSClient.get_state() method."""

    async def test_get_state(self):
        """Test getting SMS state asynchronously."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {
            "modality_type": "sms",
            "current_time": "2025-01-15T10:00:00+00:00",
            "user_phone_number": "+1234567890",
            "messages": {},
            "conversations": {},
            "total_message_count": 10,
            "unread_count": 3,
            "total_conversation_count": 5,
        }

        client = AsyncSMSClient(mock_http)
        result = await client.get_state()

        mock_http.get.assert_called_once_with("/sms/state", params=None)
        assert isinstance(result, SMSStateResponse)


class TestAsyncSMSClientQuery:
    """Tests for AsyncSMSClient.query() method."""

    async def test_query(self):
        """Test querying messages asynchronously."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "modality_type": "sms",
            "messages": [],
            "total_count": 0,
            "returned_count": 0,
            "query": {"is_read": False},
        }

        client = AsyncSMSClient(mock_http)
        result = await client.query(is_read=False)

        mock_http.post.assert_called_once()
        assert isinstance(result, SMSQueryResponse)


class TestAsyncSMSClientSend:
    """Tests for AsyncSMSClient.send() method."""

    async def test_send(self):
        """Test sending an SMS asynchronously."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "SMS sent",
            "modality": "sms",
        }

        client = AsyncSMSClient(mock_http)
        result = await client.send(
            from_number="+1234567890",
            to_numbers=["+0987654321"],
            body="Hello!",
        )

        assert isinstance(result, ModalityActionResponse)


class TestAsyncSMSClientActions:
    """Tests for AsyncSMSClient action methods."""

    async def test_react(self):
        """Test adding a reaction asynchronously."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Reaction added",
            "modality": "sms",
        }

        client = AsyncSMSClient(mock_http)
        result = await client.react(
            message_id="sms-123",
            phone_number="+1234567890",
            emoji="❤️",
        )

        mock_http.post.assert_called_once()
        assert isinstance(result, ModalityActionResponse)
