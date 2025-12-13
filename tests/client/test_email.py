"""Unit tests for the EmailClient and AsyncEmailClient.

This module tests the email modality sub-client that provides methods for
sending, receiving, organizing, and querying email messages.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from client._email import (
    AsyncEmailClient,
    Email,
    EmailAttachment,
    EmailClient,
    EmailQueryResponse,
    EmailStateResponse,
    EmailSummary,
    EmailSummaryStateResponse,
    EmailThread,
)
from client.models import ModalityActionResponse


# =============================================================================
# Response Model Tests
# =============================================================================


class TestEmailAttachment:
    """Tests for the EmailAttachment model."""

    def test_instantiation_with_all_fields(self):
        """Test creating an EmailAttachment with all fields."""
        attachment = EmailAttachment(
            filename="document.pdf",
            size=1024,
            mime_type="application/pdf",
            content_id="cid:doc123",
        )
        assert attachment.filename == "document.pdf"
        assert attachment.size == 1024
        assert attachment.mime_type == "application/pdf"
        assert attachment.content_id == "cid:doc123"

    def test_instantiation_with_required_fields_only(self):
        """Test creating an EmailAttachment with only required fields."""
        attachment = EmailAttachment(
            filename="image.png",
            size=2048,
            mime_type="image/png",
        )
        assert attachment.filename == "image.png"
        assert attachment.content_id is None


class TestEmail:
    """Tests for the Email model."""

    def test_instantiation_with_all_fields(self):
        """Test creating an Email with all fields."""
        email = Email(
            message_id="msg-123",
            thread_id="thread-456",
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
            cc_addresses=["cc@example.com"],
            bcc_addresses=["bcc@example.com"],
            reply_to_address="reply@example.com",
            subject="Test Subject",
            body_text="This is the body",
            body_html="<p>This is the body</p>",
            attachments=[],
            in_reply_to="msg-100",
            references=["msg-100", "msg-50"],
            sent_at=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
            received_at=datetime(2025, 1, 15, 10, 1, tzinfo=timezone.utc),
            is_read=True,
            is_starred=True,
            priority="high",
            folder="inbox",
            labels=["work", "important"],
        )
        assert email.message_id == "msg-123"
        assert email.from_address == "sender@example.com"
        assert email.is_read is True
        assert email.priority == "high"
        assert len(email.labels) == 2

    def test_instantiation_with_required_fields_only(self):
        """Test creating an Email with only required fields."""
        email = Email(
            message_id="msg-123",
            thread_id="thread-456",
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
            subject="Test Subject",
            body_text="This is the body",
            sent_at=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
            received_at=datetime(2025, 1, 15, 10, 1, tzinfo=timezone.utc),
        )
        assert email.cc_addresses == []
        assert email.bcc_addresses == []
        assert email.is_read is False
        assert email.is_starred is False
        assert email.priority == "normal"
        assert email.folder == "inbox"


class TestEmailThread:
    """Tests for the EmailThread model."""

    def test_instantiation(self):
        """Test creating an EmailThread."""
        thread = EmailThread(
            thread_id="thread-123",
            subject="Thread Subject",
            participant_addresses=["a@example.com", "b@example.com"],
            message_ids=["msg-1", "msg-2", "msg-3"],
            created_at=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
            last_message_at=datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc),
            message_count=3,
            unread_count=1,
        )
        assert thread.thread_id == "thread-123"
        assert thread.message_count == 3
        assert thread.unread_count == 1


class TestEmailStateResponse:
    """Tests for the EmailStateResponse model."""

    def test_instantiation(self):
        """Test creating an EmailStateResponse."""
        response = EmailStateResponse(
            modality_type="email",
            current_time=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
            user_email_address="user@example.com",
            emails={},
            threads={},
            folders={"inbox": 5, "sent": 3, "drafts": 0},
            labels={"work": 2, "personal": 3},
            total_email_count=8,
            unread_count=2,
            starred_count=1,
        )
        assert response.modality_type == "email"
        assert response.user_email_address == "user@example.com"
        assert response.total_email_count == 8


class TestEmailQueryResponse:
    """Tests for the EmailQueryResponse model."""

    def test_instantiation(self):
        """Test creating an EmailQueryResponse."""
        response = EmailQueryResponse(
            modality_type="email",
            emails=[],
            total_count=10,
            returned_count=5,
            query={"folder": "inbox", "is_read": False},
        )
        assert response.total_count == 10
        assert response.returned_count == 5


# =============================================================================
# EmailClient Tests
# =============================================================================


class TestEmailClientGetState:
    """Tests for EmailClient.get_state() method."""

    def test_get_state(self):
        """Test getting email state."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "modality_type": "email",
            "current_time": "2025-01-15T10:00:00+00:00",
            "user_email_address": "user@example.com",
            "emails": {},
            "threads": {},
            "folders": {"inbox": 5, "sent": 3},
            "labels": {"work": 2},
            "total_email_count": 8,
            "unread_count": 2,
            "starred_count": 1,
        }

        client = EmailClient(mock_http)
        result = client.get_state()

        mock_http.get.assert_called_once_with("/email/state", params=None)
        assert isinstance(result, EmailStateResponse)
        assert result.total_email_count == 8

    def test_get_state_summary(self):
        """Test getting email state with summary=True."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "modality_type": "email",
            "current_time": "2025-01-15T10:00:00+00:00",
            "user_email_address": "user@example.com",
            "statistics": {"total": 8, "unread": 2},
            "folders": {"inbox": {"count": 5, "unread": 2}},
            "labels": {"work": 2},
            "emails": {},
            "threads": {},
        }

        client = EmailClient(mock_http)
        result = client.get_state(summary=True)

        mock_http.get.assert_called_once_with("/email/state", params={"summary": True})
        assert isinstance(result, EmailSummaryStateResponse)


class TestEmailClientQuery:
    """Tests for EmailClient.query() method."""

    def test_query_no_filters(self):
        """Test querying emails with no filters."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "modality_type": "email",
            "emails": [],
            "total_count": 0,
            "returned_count": 0,
            "query": {},
        }

        client = EmailClient(mock_http)
        result = client.query()

        mock_http.post.assert_called_once_with("/email/query", json={}, params=None)
        assert isinstance(result, EmailQueryResponse)

    def test_query_with_filters(self):
        """Test querying emails with various filters."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "modality_type": "email",
            "emails": [],
            "total_count": 5,
            "returned_count": 5,
            "query": {"folder": "inbox", "is_read": False},
        }

        client = EmailClient(mock_http)
        result = client.query(
            folder="inbox",
            is_read=False,
            is_starred=True,
            from_address="sender@example.com",
            limit=10,
        )

        call_args = mock_http.post.call_args
        assert call_args[1]["json"]["folder"] == "inbox"
        assert call_args[1]["json"]["is_read"] is False
        assert call_args[1]["json"]["is_starred"] is True
        assert call_args[1]["json"]["from_address"] == "sender@example.com"
        assert call_args[1]["json"]["limit"] == 10

    def test_query_with_date_filters(self):
        """Test querying emails with date filters."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "modality_type": "email",
            "emails": [],
            "total_count": 0,
            "returned_count": 0,
            "query": {},
        }

        client = EmailClient(mock_http)
        sent_after = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
        sent_before = datetime(2025, 1, 15, 0, 0, tzinfo=timezone.utc)
        client.query(sent_after=sent_after, sent_before=sent_before)

        call_args = mock_http.post.call_args
        assert "sent_after" in call_args[1]["json"]
        assert "sent_before" in call_args[1]["json"]


class TestEmailClientSend:
    """Tests for EmailClient.send() method."""

    def test_send_minimal(self):
        """Test sending an email with minimal parameters."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Email sent successfully",
            "modality": "email",
        }

        client = EmailClient(mock_http)
        result = client.send(
            from_address="me@example.com",
            to_addresses=["recipient@example.com"],
            subject="Test Subject",
            body_text="Test body",
        )

        mock_http.post.assert_called_once()
        call_args = mock_http.post.call_args
        assert call_args[0][0] == "/email/send"
        assert call_args[1]["json"]["from_address"] == "me@example.com"
        assert call_args[1]["json"]["to_addresses"] == ["recipient@example.com"]
        assert call_args[1]["json"]["subject"] == "Test Subject"
        assert call_args[1]["json"]["body_text"] == "Test body"
        assert isinstance(result, ModalityActionResponse)

    def test_send_with_all_options(self):
        """Test sending an email with all options."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Email sent successfully",
            "modality": "email",
        }

        client = EmailClient(mock_http)
        result = client.send(
            from_address="me@example.com",
            to_addresses=["recipient@example.com"],
            subject="Test Subject",
            body_text="Test body",
            cc_addresses=["cc@example.com"],
            bcc_addresses=["bcc@example.com"],
            reply_to_address="reply@example.com",
            body_html="<p>Test body</p>",
            attachments=[{"filename": "doc.pdf", "size": 1024, "mime_type": "application/pdf"}],
            priority="high",
        )

        call_args = mock_http.post.call_args
        assert call_args[1]["json"]["cc_addresses"] == ["cc@example.com"]
        assert call_args[1]["json"]["bcc_addresses"] == ["bcc@example.com"]
        assert call_args[1]["json"]["priority"] == "high"


class TestEmailClientReceive:
    """Tests for EmailClient.receive() method."""

    def test_receive_minimal(self):
        """Test receiving an email with minimal parameters."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Email received",
            "modality": "email",
        }

        client = EmailClient(mock_http)
        result = client.receive(
            from_address="sender@example.com",
            to_addresses=["me@example.com"],
            subject="Incoming Email",
            body_text="Hello!",
        )

        mock_http.post.assert_called_once()
        call_args = mock_http.post.call_args
        assert call_args[0][0] == "/email/receive"
        assert isinstance(result, ModalityActionResponse)

    def test_receive_with_thread_info(self):
        """Test receiving an email with thread information."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Email received",
            "modality": "email",
        }

        client = EmailClient(mock_http)
        client.receive(
            from_address="sender@example.com",
            to_addresses=["me@example.com"],
            subject="Re: Original Subject",
            body_text="Reply content",
            thread_id="thread-123",
            in_reply_to="msg-456",
            references=["msg-456", "msg-123"],
        )

        call_args = mock_http.post.call_args
        assert call_args[1]["json"]["thread_id"] == "thread-123"
        assert call_args[1]["json"]["in_reply_to"] == "msg-456"


class TestEmailClientActions:
    """Tests for EmailClient action methods (read, unread, star, etc.)."""

    def test_read(self):
        """Test marking emails as read."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Marked as read",
            "modality": "email",
        }

        client = EmailClient(mock_http)
        result = client.read(message_ids=["msg-1", "msg-2"])

        mock_http.post.assert_called_once_with(
            "/email/read",
            json={"message_ids": ["msg-1", "msg-2"]},
            params=None,
        )
        assert isinstance(result, ModalityActionResponse)

    def test_unread(self):
        """Test marking emails as unread."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Marked as unread",
            "modality": "email",
        }

        client = EmailClient(mock_http)
        result = client.unread(message_ids=["msg-1"])

        mock_http.post.assert_called_once_with(
            "/email/unread",
            json={"message_ids": ["msg-1"]},
            params=None,
        )

    def test_star(self):
        """Test starring emails."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Starred",
            "modality": "email",
        }

        client = EmailClient(mock_http)
        client.star(message_ids=["msg-1"])

        mock_http.post.assert_called_once_with(
            "/email/star",
            json={"message_ids": ["msg-1"]},
            params=None,
        )

    def test_unstar(self):
        """Test unstarring emails."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Unstarred",
            "modality": "email",
        }

        client = EmailClient(mock_http)
        client.unstar(message_ids=["msg-1"])

        mock_http.post.assert_called_once_with(
            "/email/unstar",
            json={"message_ids": ["msg-1"]},
            params=None,
        )

    def test_archive(self):
        """Test archiving emails."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Archived",
            "modality": "email",
        }

        client = EmailClient(mock_http)
        client.archive(message_ids=["msg-1", "msg-2"])

        mock_http.post.assert_called_once_with(
            "/email/archive",
            json={"message_ids": ["msg-1", "msg-2"]},
            params=None,
        )

    def test_delete(self):
        """Test deleting emails."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Deleted",
            "modality": "email",
        }

        client = EmailClient(mock_http)
        client.delete(message_ids=["msg-1"])

        mock_http.post.assert_called_once_with(
            "/email/delete",
            json={"message_ids": ["msg-1"]},
            params=None,
        )

    def test_label(self):
        """Test adding labels to emails."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Labels added",
            "modality": "email",
        }

        client = EmailClient(mock_http)
        client.label(message_ids=["msg-1"], labels=["work", "important"])

        mock_http.post.assert_called_once_with(
            "/email/label",
            json={"message_ids": ["msg-1"], "labels": ["work", "important"]},
            params=None,
        )

    def test_unlabel(self):
        """Test removing labels from emails."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Labels removed",
            "modality": "email",
        }

        client = EmailClient(mock_http)
        client.unlabel(message_ids=["msg-1"], labels=["work"])

        mock_http.post.assert_called_once_with(
            "/email/unlabel",
            json={"message_ids": ["msg-1"], "labels": ["work"]},
            params=None,
        )

    def test_move(self):
        """Test moving emails to a folder."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Moved to folder",
            "modality": "email",
        }

        client = EmailClient(mock_http)
        client.move(message_ids=["msg-1", "msg-2"], folder="archive")

        mock_http.post.assert_called_once_with(
            "/email/move",
            json={"message_ids": ["msg-1", "msg-2"], "folder": "archive"},
            params=None,
        )


# =============================================================================
# AsyncEmailClient Tests
# =============================================================================


class TestAsyncEmailClientGetState:
    """Tests for AsyncEmailClient.get_state() method."""

    async def test_get_state(self):
        """Test getting email state asynchronously."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {
            "modality_type": "email",
            "current_time": "2025-01-15T10:00:00+00:00",
            "user_email_address": "user@example.com",
            "emails": {},
            "threads": {},
            "folders": {"inbox": 5},
            "labels": {},
            "total_email_count": 5,
            "unread_count": 2,
            "starred_count": 0,
        }

        client = AsyncEmailClient(mock_http)
        result = await client.get_state()

        mock_http.get.assert_called_once_with("/email/state", params=None)
        assert isinstance(result, EmailStateResponse)


class TestAsyncEmailClientQuery:
    """Tests for AsyncEmailClient.query() method."""

    async def test_query(self):
        """Test querying emails asynchronously."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "modality_type": "email",
            "emails": [],
            "total_count": 0,
            "returned_count": 0,
            "query": {"is_read": False},
        }

        client = AsyncEmailClient(mock_http)
        result = await client.query(is_read=False)

        mock_http.post.assert_called_once()
        assert isinstance(result, EmailQueryResponse)


class TestAsyncEmailClientSend:
    """Tests for AsyncEmailClient.send() method."""

    async def test_send(self):
        """Test sending an email asynchronously."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Email sent",
            "modality": "email",
        }

        client = AsyncEmailClient(mock_http)
        result = await client.send(
            from_address="me@example.com",
            to_addresses=["recipient@example.com"],
            subject="Test",
            body_text="Body",
        )

        assert isinstance(result, ModalityActionResponse)


class TestAsyncEmailClientActions:
    """Tests for AsyncEmailClient action methods."""

    async def test_read(self):
        """Test marking emails as read asynchronously."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Marked as read",
            "modality": "email",
        }

        client = AsyncEmailClient(mock_http)
        result = await client.read(message_ids=["msg-1"])

        mock_http.post.assert_called_once_with(
            "/email/read",
            json={"message_ids": ["msg-1"]},
            params=None,
        )
        assert isinstance(result, ModalityActionResponse)
