"""Unit tests for email state modality.

This module tests both general ModalityState behavior and email-specific features.
"""

from datetime import datetime, timezone

import pytest

from models.modalities.email_input import EmailAttachment, EmailInput
from models.modalities.email_state import Email, EmailState, EmailThread


class TestEmailStateInstantiation:
    """Test instantiation patterns for EmailState.

    GENERAL PATTERN: All ModalityState subclasses should instantiate with last_updated.
    """

    def test_minimal_instantiation(self):
        """Verify EmailState instantiates with minimal required fields."""
        state = EmailState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        assert state.last_updated == datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        assert len(state.emails) == 0
        assert len(state.threads) == 0
        assert len(state.folders) == 6  # inbox, sent, drafts, trash, spam, archive

    def test_default_folder_structure(self):
        """Verify EmailState initializes with standard folder structure."""
        state = EmailState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        # Standard folders are pre-initialized
        assert "inbox" in state.folders
        assert "sent" in state.folders
        assert "drafts" in state.folders
        assert "trash" in state.folders
        assert "spam" in state.folders
        assert "archive" in state.folders
        assert len(state.folders) == 6


class TestEmailPydanticModel:
    """Test Email Pydantic helper class.

    MODALITY-SPECIFIC: Email as Pydantic model with state-modifying methods.
    """

    def test_email_instantiation(self):
        """Verify Email instantiates as Pydantic model."""
        email = Email(
            message_id="msg-123",
            thread_id="thread-456",
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
            subject="Test Subject",
            body_text="Test body",
            sent_at=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
            received_at=datetime(2025, 1, 1, 10, 5, tzinfo=timezone.utc),
        )

        assert email.message_id == "msg-123"
        assert email.thread_id == "thread-456"
        assert email.from_address == "sender@example.com"
        assert email.to_addresses == ["recipient@example.com"]
        assert email.subject == "Test Subject"
        assert email.is_read is False
        assert email.is_starred is False
        assert email.folder == "inbox"
        assert email.priority == "normal"

    def test_email_mark_read_unread(self):
        """MODALITY-SPECIFIC: Verify Email read/unread methods."""
        email = Email(
            message_id="msg-123",
            thread_id="thread-456",
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
            subject="Test",
            body_text="Test",
            sent_at=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
            received_at=datetime(2025, 1, 1, 10, 5, tzinfo=timezone.utc),
        )

        assert email.is_read is False
        email.mark_read()
        assert email.is_read is True
        email.mark_unread()
        assert email.is_read is False

    def test_email_toggle_star(self):
        """MODALITY-SPECIFIC: Verify Email star toggle."""
        email = Email(
            message_id="msg-123",
            thread_id="thread-456",
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
            subject="Test",
            body_text="Test",
            sent_at=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
            received_at=datetime(2025, 1, 1, 10, 5, tzinfo=timezone.utc),
        )

        assert email.is_starred is False
        email.toggle_star()
        assert email.is_starred is True
        email.toggle_star()
        assert email.is_starred is False

    def test_email_label_operations(self):
        """MODALITY-SPECIFIC: Verify Email label add/remove."""
        email = Email(
            message_id="msg-123",
            thread_id="thread-456",
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
            subject="Test",
            body_text="Test",
            sent_at=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
            received_at=datetime(2025, 1, 1, 10, 5, tzinfo=timezone.utc),
        )

        assert email.labels == []
        email.add_label("work")
        assert "work" in email.labels
        email.add_label("urgent")
        assert len(email.labels) == 2
        email.remove_label("work")
        assert "work" not in email.labels
        assert len(email.labels) == 1

    def test_email_move_folder(self):
        """MODALITY-SPECIFIC: Verify Email folder movement."""
        email = Email(
            message_id="msg-123",
            thread_id="thread-456",
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
            subject="Test",
            body_text="Test",
            sent_at=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
            received_at=datetime(2025, 1, 1, 10, 5, tzinfo=timezone.utc),
        )

        assert email.folder == "inbox"
        email.move_to_folder("archive")
        assert email.folder == "archive"
        email.move_to_folder("trash")
        assert email.folder == "trash"

    def test_email_serialization(self):
        """Verify Email Pydantic model can be serialized/deserialized."""
        original = Email(
            message_id="msg-123",
            thread_id="thread-456",
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
            cc_addresses=["cc@example.com"],
            subject="Test Subject",
            body_text="Test body",
            body_html="<p>Test body</p>",
            priority="high",
            sent_at=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
            received_at=datetime(2025, 1, 1, 10, 5, tzinfo=timezone.utc),
            is_read=True,
            is_starred=True,
            labels=["work", "urgent"],
        )

        dumped = original.model_dump()
        restored = Email.model_validate(dumped)

        assert restored.message_id == original.message_id
        assert restored.subject == original.subject
        assert restored.is_read == original.is_read
        assert restored.is_starred == original.is_starred
        assert restored.labels == original.labels
        assert restored.priority == original.priority


class TestEmailThreadPydanticModel:
    """Test EmailThread Pydantic helper class.

    MODALITY-SPECIFIC: EmailThread as Pydantic model with threading logic.
    """

    def test_thread_instantiation(self):
        """Verify EmailThread instantiates as Pydantic model."""
        thread = EmailThread(
            thread_id="thread-123",
            subject="Project Discussion",
            created_at=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
            last_message_at=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            participant_addresses={"alice@example.com", "bob@example.com"},
            message_ids=["msg-1", "msg-2"],
            message_count=2,
            unread_count=1,
        )

        assert thread.thread_id == "thread-123"
        assert thread.subject == "Project Discussion"
        assert thread.message_count == 2
        assert thread.unread_count == 1
        assert len(thread.participant_addresses) == 2
        assert len(thread.message_ids) == 2

    def test_thread_add_message(self):
        """MODALITY-SPECIFIC: Verify EmailThread add_message updates counts."""
        thread = EmailThread(
            thread_id="thread-123",
            subject="Discussion",
            created_at=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
            last_message_at=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
            message_ids=["msg-1"],
            message_count=1,
        )

        thread.add_message("msg-2", datetime(2025, 1, 1, 11, 0, tzinfo=timezone.utc))
        assert thread.message_count == 2
        assert thread.last_message_at == datetime(2025, 1, 1, 11, 0, tzinfo=timezone.utc)
        assert "msg-2" in thread.message_ids

    def test_thread_update_unread_count(self):
        """MODALITY-SPECIFIC: Verify EmailThread unread count tracking."""
        thread = EmailThread(
            thread_id="thread-123",
            subject="Discussion",
            created_at=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
            last_message_at=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
            unread_count=3,
        )

        thread.update_unread_count(-1)
        assert thread.unread_count == 2
        thread.update_unread_count(-2)
        assert thread.unread_count == 0
        thread.update_unread_count(1)
        assert thread.unread_count == 1

    def test_thread_serialization(self):
        """Verify EmailThread Pydantic model can be serialized/deserialized."""
        original = EmailThread(
            thread_id="thread-123",
            subject="Test Thread",
            created_at=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
            last_message_at=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            participant_addresses={"user1@example.com", "user2@example.com", "user3@example.com"},
            message_ids=["msg-1", "msg-2", "msg-3"],
            message_count=3,
            unread_count=1,
        )

        dumped = original.model_dump()
        restored = EmailThread.model_validate(dumped)

        assert restored.thread_id == original.thread_id
        assert restored.subject == original.subject
        assert restored.message_count == original.message_count
        assert restored.unread_count == original.unread_count
        assert restored.participant_addresses == original.participant_addresses
        assert restored.message_ids == original.message_ids


class TestEmailStateApplyInput:
    """Test EmailState.apply_input() method.

    GENERAL PATTERN: apply_input() processes inputs and updates state.
    MODALITY-SPECIFIC: Email operations (receive, send, reply, mark_read, etc.).
    """

    def test_receive_email(self):
        """MODALITY-SPECIFIC: Verify receiving email creates new email and thread."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        email_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Test Email",
            body_text="This is a test.",
        )

        state.apply_input(email_input)

        assert len(state.emails) == 1
        assert len(state.threads) == 1
        assert state.last_updated == datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc)

    def test_send_email(self):
        """MODALITY-SPECIFIC: Verify sending email."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        email_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="send",
            from_address="you@example.com",
            to_addresses=["recipient@example.com"],
            subject="Sent Email",
            body_text="This is my message.",
        )

        state.apply_input(email_input)

        assert len(state.emails) == 1
        # Sent emails should be in "sent" folder
        email = list(state.emails.values())[0]
        assert email.folder == "sent"

    def test_reply_to_email(self):
        """MODALITY-SPECIFIC: Verify replying adds email to same thread."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        # Receive original email
        original = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Original Email",
            body_text="Original message.",
            message_id="msg-original",
            thread_id="thread-1",
        )
        state.apply_input(original)

        # Send reply
        reply = EmailInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="reply",
            from_address="you@example.com",
            to_addresses=["sender@example.com"],
            subject="Re: Original Email",
            body_text="My reply.",
            thread_id="thread-1",
            in_reply_to="msg-original",
        )
        state.apply_input(reply)

        assert len(state.emails) == 2
        assert len(state.threads) == 1  # Same thread
        thread = state.threads["thread-1"]
        assert thread.message_count == 2

    def test_mark_read(self):
        """MODALITY-SPECIFIC: Verify marking email as read."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        # Receive email
        email_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Test",
            body_text="Test",
            message_id="msg-123",
        )
        state.apply_input(email_input)

        email = state.emails["msg-123"]
        assert email.is_read is False

        # Mark as read
        mark_read = EmailInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="mark_read",
            message_ids=["msg-123"],
            from_address="you@example.com",
            to_addresses=["you@example.com"],
            subject="",
            body_text="",
        )
        state.apply_input(mark_read)

        assert email.is_read is True

    def test_star_email(self):
        """MODALITY-SPECIFIC: Verify starring email."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        # Receive email
        email_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Important",
            body_text="Important message",
            message_id="msg-123",
        )
        state.apply_input(email_input)

        # Star it
        star_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="star",
            message_ids=["msg-123"],
            from_address="you@example.com",
            to_addresses=["you@example.com"],
            subject="",
            body_text="",
        )
        state.apply_input(star_input)

        email = state.emails["msg-123"]
        assert email.is_starred is True

    def test_move_to_folder(self):
        """MODALITY-SPECIFIC: Verify moving email to different folder."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        # Receive email
        email_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Test",
            body_text="Test",
            message_id="msg-123",
        )
        state.apply_input(email_input)

        # Move to archive
        move_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="archive",
            message_ids=["msg-123"],
            from_address="you@example.com",
            to_addresses=["you@example.com"],
            subject="",
            body_text="",
        )
        state.apply_input(move_input)

        email = state.emails["msg-123"]
        assert email.folder == "archive"

    def test_add_label(self):
        """MODALITY-SPECIFIC: Verify adding label to email."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        # Receive email
        email_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Test",
            body_text="Test",
            message_id="msg-123",
        )
        state.apply_input(email_input)

        # Add label
        label_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="add_label",
            message_ids=["msg-123"],
            labels=["work", "urgent"],
            from_address="you@example.com",
            to_addresses=["you@example.com"],
            subject="",
            body_text="",
        )
        state.apply_input(label_input)

        email = state.emails["msg-123"]
        assert "work" in email.labels
        assert "urgent" in email.labels


class TestEmailStateGetSnapshot:
    """Test EmailState.get_snapshot() method.

    GENERAL PATTERN: get_snapshot() returns current state for agent observation.
    """

    def test_snapshot_empty_state(self):
        """Verify snapshot of empty email state."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        snapshot = state.get_snapshot()

        assert "folders" in snapshot
        assert "inbox" in snapshot["folders"]
        assert snapshot["folders"]["inbox"]["message_count"] == 0
        assert snapshot["folders"]["inbox"]["unread_count"] == 0
        assert snapshot["total_emails"] == 0

    def test_snapshot_with_emails(self):
        """Verify snapshot includes recent emails."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        # Add some emails
        for i in range(5):
            email_input = EmailInput(
                timestamp=datetime(2025, 1, 1, 12 + i, 0, tzinfo=timezone.utc),
                operation="receive",
                from_address=f"sender{i}@example.com",
                to_addresses=["you@example.com"],
                subject=f"Email {i}",
                body_text=f"Message {i}",
            )
            state.apply_input(email_input)

        snapshot = state.get_snapshot()

        assert snapshot["folders"]["inbox"]["message_count"] == 5
        assert snapshot["folders"]["inbox"]["unread_count"] == 5
        assert snapshot["total_emails"] == 5


class TestEmailStateValidation:
    """Test EmailState.validate_state() method.

    GENERAL PATTERN: validate_state() ensures state consistency.
    """

    def test_validate_empty_state(self):
        """Verify validation passes for empty state."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        errors = state.validate_state()

        assert len(errors) == 0

    def test_validate_populated_state(self):
        """Verify validation passes for populated state."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        # Add email
        email_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Test",
            body_text="Test",
        )
        state.apply_input(email_input)

        errors = state.validate_state()

        assert len(errors) == 0


class TestEmailStateQuery:
    """Test EmailState.query() method.

    GENERAL PATTERN: query() retrieves filtered state data.
    MODALITY-SPECIFIC: Email queries by folder, label, read status, sender, etc.
    """

    def test_query_by_folder(self):
        """MODALITY-SPECIFIC: Verify querying emails by folder."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        # Add emails to different folders
        inbox_email = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Inbox Email",
            body_text="Test",
        )
        state.apply_input(inbox_email)

        result = state.query({"folder": "inbox"})

        assert "emails" in result
        assert len(result["emails"]) == 1

    def test_query_unread_emails(self):
        """MODALITY-SPECIFIC: Verify querying unread emails."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        # Add read and unread emails
        email1 = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender1@example.com",
            to_addresses=["you@example.com"],
            subject="Unread",
            body_text="Test",
            message_id="msg-1",
        )
        state.apply_input(email1)

        email2 = EmailInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender2@example.com",
            to_addresses=["you@example.com"],
            subject="Will be read",
            body_text="Test",
            message_id="msg-2",
        )
        state.apply_input(email2)

        # Mark one as read
        state.emails["msg-2"].mark_read()

        result = state.query({"is_read": False})

        assert len(result["emails"]) == 1
        assert result["emails"][0]["subject"] == "Unread"

    def test_query_by_sender(self):
        """MODALITY-SPECIFIC: Verify querying emails by sender."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        # Add emails from different senders
        for i, sender in enumerate(["alice@example.com", "bob@example.com", "alice@example.com"]):
            email = EmailInput(
                timestamp=datetime(2025, 1, 1, 12 + i, 0, tzinfo=timezone.utc),
                operation="receive",
                from_address=sender,
                to_addresses=["you@example.com"],
                subject=f"Email {i}",
                body_text="Test",
            )
            state.apply_input(email)

        result = state.query({"from_address": "alice@example.com"})

        assert len(result["emails"]) == 2


class TestEmailStateSerialization:
    """Test EmailState serialization and deserialization.

    GENERAL PATTERN: State must support model_dump() and model_validate()
    for persistence and API communication.
    """

    def test_empty_state_serialization(self):
        """Verify empty EmailState can be serialized and deserialized."""
        original = EmailState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        dumped = original.model_dump()
        restored = EmailState.model_validate(dumped)

        assert restored.last_updated == original.last_updated
        assert len(restored.emails) == 0
        assert len(restored.threads) == 0

    def test_populated_state_serialization(self):
        """Verify populated EmailState with emails and threads persists correctly."""
        original = EmailState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        # Add some emails
        email1 = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Test Email 1",
            body_text="First message",
            message_id="msg-1",
            thread_id="thread-1",
        )
        original.apply_input(email1)

        email2 = EmailInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="reply",
            from_address="you@example.com",
            to_addresses=["sender@example.com"],
            subject="Re: Test Email 1",
            body_text="Reply message",
            message_id="msg-2",
            thread_id="thread-1",
            in_reply_to="msg-1",
        )
        original.apply_input(email2)

        # Serialize and restore
        dumped = original.model_dump()
        restored = EmailState.model_validate(dumped)

        assert len(restored.emails) == 2
        assert len(restored.threads) == 1
        assert "msg-1" in restored.emails
        assert "msg-2" in restored.emails
        assert restored.emails["msg-1"].subject == "Test Email 1"
        assert restored.emails["msg-2"].subject == "Re: Test Email 1"
        assert restored.threads["thread-1"].message_count == 2

    def test_state_with_labels_and_folders_serialization(self):
        """Verify EmailState with labels and folder changes serializes correctly."""
        original = EmailState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        # Add email
        email_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Important Email",
            body_text="Test",
            message_id="msg-123",
        )
        original.apply_input(email_input)

        # Add labels
        email = original.emails["msg-123"]
        email.add_label("work")
        email.add_label("urgent")
        email.toggle_star()
        email.mark_read()

        # Serialize and restore
        dumped = original.model_dump()
        restored = EmailState.model_validate(dumped)

        restored_email = restored.emails["msg-123"]
        assert restored_email.is_read is True
        assert restored_email.is_starred is True
        assert "work" in restored_email.labels
        assert "urgent" in restored_email.labels


class TestEmailStateFromFixtures:
    """Test EmailState using pre-built fixtures.

    GENERAL PATTERN: Fixtures provide reusable test data.
    """

    def test_email_state_fixture(self, email_state):
        """Verify email_state fixture provides valid EmailState."""
        assert isinstance(email_state, EmailState)
        assert email_state.last_updated is not None
        assert len(email_state.emails) == 0


class TestEmailStateIntegration:
    """Test EmailState with complex real-world scenarios.

    MODALITY-SPECIFIC: Thread management, bulk operations, folder system.
    """

    def test_conversation_thread(self):
        """MODALITY-SPECIFIC: Verify multi-message conversation thread."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 8, 0, tzinfo=timezone.utc))

        # Original email
        original = EmailInput(
            timestamp=datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="alice@example.com",
            to_addresses=["you@example.com"],
            subject="Project Planning",
            body_text="Let's discuss the project.",
            thread_id="thread-project",
            message_id="msg-original",
        )
        state.apply_input(original)

        # Reply
        reply1 = EmailInput(
            timestamp=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
            operation="reply",
            from_address="you@example.com",
            to_addresses=["alice@example.com"],
            subject="Re: Project Planning",
            body_text="Sounds good!",
            thread_id="thread-project",
            in_reply_to="msg-original",
        )
        state.apply_input(reply1)

        # Another reply
        reply2 = EmailInput(
            timestamp=datetime(2025, 1, 1, 11, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="alice@example.com",
            to_addresses=["you@example.com"],
            subject="Re: Project Planning",
            body_text="Great! Let's meet tomorrow.",
            thread_id="thread-project",
            in_reply_to="msg-original",
        )
        state.apply_input(reply2)

        thread = state.threads["thread-project"]
        assert thread.message_count == 3
        assert len(thread.participant_addresses) == 2
        assert "alice@example.com" in thread.participant_addresses
        assert "you@example.com" in thread.participant_addresses

    def test_bulk_mark_read(self):
        """MODALITY-SPECIFIC: Verify marking multiple emails as read."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        # Add multiple emails
        message_ids = []
        for i in range(5):
            email = EmailInput(
                timestamp=datetime(2025, 1, 1, 12 + i, 0, tzinfo=timezone.utc),
                operation="receive",
                from_address=f"sender{i}@example.com",
                to_addresses=["you@example.com"],
                subject=f"Email {i}",
                body_text=f"Message {i}",
                message_id=f"msg-{i}",
            )
            state.apply_input(email)
            message_ids.append(f"msg-{i}")

        # Mark all as read
        mark_read = EmailInput(
            timestamp=datetime(2025, 1, 1, 18, 0, tzinfo=timezone.utc),
            operation="mark_read",
            message_ids=message_ids,
            from_address="you@example.com",
            to_addresses=["you@example.com"],
            subject="",
            body_text="",
        )
        state.apply_input(mark_read)

        for msg_id in message_ids:
            assert state.emails[msg_id].is_read is True

    def test_email_with_attachments(self):
        """MODALITY-SPECIFIC: Verify handling emails with attachments."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        attachments = [
            EmailAttachment(
                filename="report.pdf",
                size=1024000,
                mime_type="application/pdf",
            ),
            EmailAttachment(
                filename="chart.png",
                size=512000,
                mime_type="image/png",
            ),
        ]

        email_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Report with Charts",
            body_text="See attached.",
            attachments=attachments,
        )

        state.apply_input(email_input)

        email = list(state.emails.values())[0]
        assert len(email.attachments) == 2
        assert email.attachments[0].filename == "report.pdf"
        assert email.attachments[1].filename == "chart.png"


# =============================================================================
# UNDO FUNCTIONALITY TESTS
# =============================================================================


class TestEmailStateCreateUndoData:
    """Test EmailState.create_undo_data() method.

    GENERAL PATTERN: create_undo_data() captures minimal data needed to undo.
    """

    def test_create_undo_data_raises_for_invalid_input_type(self):
        """Verify create_undo_data raises ValueError for non-EmailInput."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        from models.modalities.chat_input import ChatInput

        invalid_input = ChatInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="send_message",
            conversation_id="conv-1",
            role="user",
            content="Hello",
        )

        with pytest.raises(ValueError, match="EmailState can only create undo data"):
            state.create_undo_data(invalid_input)

    def test_create_undo_data_does_not_modify_state(self):
        """Verify create_undo_data is read-only."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        email_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Test",
            body_text="Test body",
        )

        original_update_count = state.update_count
        original_last_updated = state.last_updated
        original_email_count = len(state.emails)

        state.create_undo_data(email_input)

        assert state.update_count == original_update_count
        assert state.last_updated == original_last_updated
        assert len(state.emails) == original_email_count

    def test_create_undo_data_captures_state_metadata(self):
        """Verify undo data includes state-level metadata."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        email_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Test",
            body_text="Test body",
        )

        undo_data = state.create_undo_data(email_input)

        assert "state_previous_update_count" in undo_data
        assert "state_previous_last_updated" in undo_data
        assert undo_data["state_previous_update_count"] == 0

    def test_create_undo_data_receive_returns_remove_email_and_thread(self):
        """Verify receive operation returns action to remove email and thread."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        email_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Test",
            body_text="Test body",
            message_id="msg-123",
        )

        undo_data = state.create_undo_data(email_input)

        assert undo_data["action"] == "remove_email_and_thread"
        assert undo_data["message_id"] == "msg-123"
        assert "thread_id" in undo_data

    def test_create_undo_data_send_returns_remove_email_and_thread(self):
        """Verify send operation returns action to remove email and thread."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        email_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="send",
            from_address="you@example.com",
            to_addresses=["recipient@example.com"],
            subject="Test",
            body_text="Test body",
            message_id="msg-456",
        )

        undo_data = state.create_undo_data(email_input)

        assert undo_data["action"] == "remove_email_and_thread"
        assert undo_data["message_id"] == "msg-456"

    def test_create_undo_data_reply_returns_remove_email_restore_thread(self):
        """Verify reply operation captures previous thread state."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        # First, receive an email
        original = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Original",
            body_text="Original message",
            message_id="msg-original",
            thread_id="thread-1",
        )
        state.apply_input(original)

        # Now prepare reply
        reply_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="reply",
            from_address="you@example.com",
            to_addresses=["sender@example.com"],
            subject="Re: Original",
            body_text="My reply",
            in_reply_to="msg-original",
            message_id="msg-reply",
        )

        undo_data = state.create_undo_data(reply_input)

        assert undo_data["action"] == "remove_email_restore_thread"
        assert undo_data["message_id"] == "msg-reply"
        assert undo_data["thread_id"] == "thread-1"
        assert "previous_thread" in undo_data
        # Previous thread should have 1 message
        assert undo_data["previous_thread"]["message_count"] == 1

    def test_create_undo_data_save_draft_returns_remove_draft(self):
        """Verify save_draft operation returns action to remove draft."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        draft_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="save_draft",
            from_address="you@example.com",
            to_addresses=["recipient@example.com"],
            subject="Draft Email",
            body_text="Draft content",
            message_id="draft-123",
        )

        undo_data = state.create_undo_data(draft_input)

        assert undo_data["action"] == "remove_draft"
        assert undo_data["message_id"] == "draft-123"

    def test_create_undo_data_send_draft_returns_restore_draft(self):
        """Verify send_draft operation captures draft state."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        # First save a draft
        draft_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="save_draft",
            from_address="you@example.com",
            to_addresses=["recipient@example.com"],
            subject="Draft Email",
            body_text="Draft content",
            message_id="draft-123",
        )
        state.apply_input(draft_input)

        # Now prepare to send it
        send_draft_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="send_draft",
            message_id="draft-123",
            from_address="you@example.com",
            to_addresses=["recipient@example.com"],
            subject="Draft Email",
            body_text="Draft content",
        )

        undo_data = state.create_undo_data(send_draft_input)

        assert undo_data["action"] == "restore_draft"
        assert undo_data["message_id"] == "draft-123"
        assert undo_data["previous_folder"] == "drafts"

    def test_create_undo_data_mark_read_captures_previous_states(self):
        """Verify mark_read captures previous read state for all emails."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        # Add emails
        for i in range(3):
            email = EmailInput(
                timestamp=datetime(2025, 1, 1, 12 + i, 0, tzinfo=timezone.utc),
                operation="receive",
                from_address=f"sender{i}@example.com",
                to_addresses=["you@example.com"],
                subject=f"Email {i}",
                body_text=f"Message {i}",
                message_id=f"msg-{i}",
            )
            state.apply_input(email)

        mark_read_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 15, 0, tzinfo=timezone.utc),
            operation="mark_read",
            message_ids=["msg-0", "msg-1", "msg-2"],
            from_address="you@example.com",
            to_addresses=["you@example.com"],
            subject="",
            body_text="",
        )

        undo_data = state.create_undo_data(mark_read_input)

        assert undo_data["action"] == "restore_read_states"
        assert len(undo_data["previous_states"]) == 3
        # All emails should have been unread
        for msg_id in ["msg-0", "msg-1", "msg-2"]:
            assert undo_data["previous_states"][msg_id]["was_read"] is False

    def test_create_undo_data_star_captures_previous_states(self):
        """Verify star captures previous starred state."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        email = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Test",
            body_text="Test",
            message_id="msg-1",
        )
        state.apply_input(email)

        star_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="star",
            message_ids=["msg-1"],
            from_address="you@example.com",
            to_addresses=["you@example.com"],
            subject="",
            body_text="",
        )

        undo_data = state.create_undo_data(star_input)

        assert undo_data["action"] == "restore_starred_states"
        assert undo_data["previous_states"]["msg-1"] is False

    def test_create_undo_data_move_captures_previous_folders(self):
        """Verify move captures previous folder for each email."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        email = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Test",
            body_text="Test",
            message_id="msg-1",
        )
        state.apply_input(email)

        move_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="move",
            message_ids=["msg-1"],
            folder="archive",
            from_address="you@example.com",
            to_addresses=["you@example.com"],
            subject="",
            body_text="",
        )

        undo_data = state.create_undo_data(move_input)

        assert undo_data["action"] == "restore_folders"
        assert undo_data["previous_folders"]["msg-1"] == "inbox"

    def test_create_undo_data_add_label_captures_previous_labels(self):
        """Verify add_label captures previous label state."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        email = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Test",
            body_text="Test",
            message_id="msg-1",
        )
        state.apply_input(email)

        add_label_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="add_label",
            message_ids=["msg-1"],
            labels=["work", "urgent"],
            from_address="you@example.com",
            to_addresses=["you@example.com"],
            subject="",
            body_text="",
        )

        undo_data = state.create_undo_data(add_label_input)

        assert undo_data["action"] == "restore_labels_after_add"
        assert undo_data["previous_label_states"]["msg-1"] == []
        assert set(undo_data["labels_added"]) == {"work", "urgent"}
        assert undo_data["labels_existed_before"] == []

    def test_create_undo_data_remove_label_captures_previous_labels(self):
        """Verify remove_label captures previous label state."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        # Add email with labels
        email = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Test",
            body_text="Test",
            message_id="msg-1",
        )
        state.apply_input(email)

        add_label = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="add_label",
            message_ids=["msg-1"],
            labels=["work", "urgent"],
            from_address="you@example.com",
            to_addresses=["you@example.com"],
            subject="",
            body_text="",
        )
        state.apply_input(add_label)

        remove_label_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="remove_label",
            message_ids=["msg-1"],
            labels=["work"],
            from_address="you@example.com",
            to_addresses=["you@example.com"],
            subject="",
            body_text="",
        )

        undo_data = state.create_undo_data(remove_label_input)

        assert undo_data["action"] == "restore_labels_after_remove"
        assert set(undo_data["previous_label_states"]["msg-1"]) == {"work", "urgent"}
        assert undo_data["labels_removed"] == ["work"]

    def test_create_undo_data_noop_for_nonexistent_message(self):
        """Verify operations on non-existent messages return noop."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        mark_read_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="mark_read",
            message_ids=["nonexistent-msg"],
            from_address="you@example.com",
            to_addresses=["you@example.com"],
            subject="",
            body_text="",
        )

        undo_data = state.create_undo_data(mark_read_input)

        assert undo_data["action"] == "noop"


class TestEmailStateApplyUndo:
    """Test EmailState.apply_undo() method.

    GENERAL PATTERN: apply_undo() reverses the effect of apply_input().
    """

    def test_apply_undo_raises_for_missing_action(self):
        """Verify apply_undo raises ValueError for missing action."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        with pytest.raises(ValueError, match="missing 'action' field"):
            state.apply_undo({})

    def test_apply_undo_raises_for_unknown_action(self):
        """Verify apply_undo raises ValueError for unknown action."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        with pytest.raises(ValueError, match="Unknown undo action"):
            state.apply_undo({
                "action": "unknown_action",
                "state_previous_update_count": 0,
                "state_previous_last_updated": "2025-01-01T12:00:00+00:00",
            })

    def test_apply_undo_noop_restores_metadata_only(self):
        """Verify noop action restores state metadata only."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        # Manually update state
        state.update_count = 5
        state.last_updated = datetime(2025, 1, 1, 15, 0, tzinfo=timezone.utc)

        state.apply_undo({
            "action": "noop",
            "state_previous_update_count": 3,
            "state_previous_last_updated": "2025-01-01T13:00:00+00:00",
        })

        assert state.update_count == 3
        assert state.last_updated == datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc)

    def test_apply_undo_receive_removes_email_and_thread(self):
        """Verify undo of receive removes email and thread."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        email_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Test",
            body_text="Test body",
            message_id="msg-123",
            thread_id="thread-123",
        )

        undo_data = state.create_undo_data(email_input)
        state.apply_input(email_input)

        assert len(state.emails) == 1
        assert len(state.threads) == 1

        state.apply_undo(undo_data)

        assert len(state.emails) == 0
        assert len(state.threads) == 0
        assert state.update_count == 0

    def test_apply_undo_send_removes_email_and_thread(self):
        """Verify undo of send removes email and thread."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        email_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="send",
            from_address="you@example.com",
            to_addresses=["recipient@example.com"],
            subject="Test",
            body_text="Test body",
            message_id="msg-456",
            thread_id="thread-456",
        )

        undo_data = state.create_undo_data(email_input)
        state.apply_input(email_input)

        assert len(state.emails) == 1
        assert "msg-456" in state.folders["sent"]

        state.apply_undo(undo_data)

        assert len(state.emails) == 0
        assert "msg-456" not in state.folders["sent"]

    def test_apply_undo_reply_restores_thread(self):
        """Verify undo of reply restores thread to previous state."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        # Receive original email
        original = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Original",
            body_text="Original message",
            message_id="msg-original",
            thread_id="thread-1",
        )
        state.apply_input(original)

        original_thread_dict = state.threads["thread-1"].model_dump()

        # Prepare reply
        reply_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="reply",
            from_address="you@example.com",
            to_addresses=["sender@example.com"],
            subject="Re: Original",
            body_text="My reply",
            in_reply_to="msg-original",
            message_id="msg-reply",
        )

        undo_data = state.create_undo_data(reply_input)
        state.apply_input(reply_input)

        assert len(state.emails) == 2
        assert state.threads["thread-1"].message_count == 2

        state.apply_undo(undo_data)

        assert len(state.emails) == 1
        assert "msg-reply" not in state.emails
        assert state.threads["thread-1"].message_count == 1
        assert state.threads["thread-1"].model_dump() == original_thread_dict

    def test_apply_undo_save_draft_removes_draft(self):
        """Verify undo of save_draft removes draft."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        draft_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="save_draft",
            from_address="you@example.com",
            to_addresses=["recipient@example.com"],
            subject="Draft Email",
            body_text="Draft content",
            message_id="draft-123",
        )

        undo_data = state.create_undo_data(draft_input)
        state.apply_input(draft_input)

        assert len(state.drafts) == 1
        assert "draft-123" in state.folders["drafts"]

        state.apply_undo(undo_data)

        assert len(state.drafts) == 0
        assert "draft-123" not in state.folders["drafts"]
        assert "draft-123" not in state.emails

    def test_apply_undo_send_draft_restores_draft(self):
        """Verify undo of send_draft restores draft state."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        # Save draft
        draft_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="save_draft",
            from_address="you@example.com",
            to_addresses=["recipient@example.com"],
            subject="Draft Email",
            body_text="Draft content",
            message_id="draft-123",
        )
        state.apply_input(draft_input)

        # Prepare to send draft
        send_draft_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="send_draft",
            message_id="draft-123",
            from_address="you@example.com",
            to_addresses=["recipient@example.com"],
            subject="Draft Email",
            body_text="Draft content",
        )

        undo_data = state.create_undo_data(send_draft_input)
        state.apply_input(send_draft_input)

        assert "draft-123" not in state.drafts
        assert "draft-123" in state.folders["sent"]
        assert "draft-123" not in state.folders["drafts"]

        state.apply_undo(undo_data)

        assert "draft-123" in state.drafts
        assert "draft-123" in state.folders["drafts"]
        assert "draft-123" not in state.folders["sent"]
        assert state.emails["draft-123"].folder == "drafts"

    def test_apply_undo_mark_read_restores_unread_state(self):
        """Verify undo of mark_read restores unread state."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        # Add email
        email = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Test",
            body_text="Test",
            message_id="msg-1",
            thread_id="thread-1",
        )
        state.apply_input(email)

        assert state.emails["msg-1"].is_read is False
        assert state.threads["thread-1"].unread_count == 1

        # Mark as read
        mark_read = EmailInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="mark_read",
            message_ids=["msg-1"],
            from_address="you@example.com",
            to_addresses=["you@example.com"],
            subject="",
            body_text="",
        )

        undo_data = state.create_undo_data(mark_read)
        state.apply_input(mark_read)

        assert state.emails["msg-1"].is_read is True
        assert state.threads["thread-1"].unread_count == 0

        state.apply_undo(undo_data)

        assert state.emails["msg-1"].is_read is False
        assert state.threads["thread-1"].unread_count == 1

    def test_apply_undo_mark_unread_restores_read_state(self):
        """Verify undo of mark_unread restores read state."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        # Add email and mark it read
        email = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Test",
            body_text="Test",
            message_id="msg-1",
            thread_id="thread-1",
        )
        state.apply_input(email)

        mark_read = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="mark_read",
            message_ids=["msg-1"],
            from_address="you@example.com",
            to_addresses=["you@example.com"],
            subject="",
            body_text="",
        )
        state.apply_input(mark_read)

        assert state.emails["msg-1"].is_read is True
        assert state.threads["thread-1"].unread_count == 0

        # Mark unread
        mark_unread = EmailInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="mark_unread",
            message_ids=["msg-1"],
            from_address="you@example.com",
            to_addresses=["you@example.com"],
            subject="",
            body_text="",
        )

        undo_data = state.create_undo_data(mark_unread)
        state.apply_input(mark_unread)

        assert state.emails["msg-1"].is_read is False
        assert state.threads["thread-1"].unread_count == 1

        state.apply_undo(undo_data)

        assert state.emails["msg-1"].is_read is True
        assert state.threads["thread-1"].unread_count == 0

    def test_apply_undo_star_restores_unstarred_state(self):
        """Verify undo of star restores unstarred state."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        email = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Test",
            body_text="Test",
            message_id="msg-1",
        )
        state.apply_input(email)

        star_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="star",
            message_ids=["msg-1"],
            from_address="you@example.com",
            to_addresses=["you@example.com"],
            subject="",
            body_text="",
        )

        undo_data = state.create_undo_data(star_input)
        state.apply_input(star_input)

        assert state.emails["msg-1"].is_starred is True

        state.apply_undo(undo_data)

        assert state.emails["msg-1"].is_starred is False

    def test_apply_undo_unstar_restores_starred_state(self):
        """Verify undo of unstar restores starred state."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        email = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Test",
            body_text="Test",
            message_id="msg-1",
        )
        state.apply_input(email)

        # Star it first
        star = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="star",
            message_ids=["msg-1"],
            from_address="you@example.com",
            to_addresses=["you@example.com"],
            subject="",
            body_text="",
        )
        state.apply_input(star)

        # Now unstar
        unstar_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="unstar",
            message_ids=["msg-1"],
            from_address="you@example.com",
            to_addresses=["you@example.com"],
            subject="",
            body_text="",
        )

        undo_data = state.create_undo_data(unstar_input)
        state.apply_input(unstar_input)

        assert state.emails["msg-1"].is_starred is False

        state.apply_undo(undo_data)

        assert state.emails["msg-1"].is_starred is True

    def test_apply_undo_move_restores_original_folder(self):
        """Verify undo of move restores original folder."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        email = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Test",
            body_text="Test",
            message_id="msg-1",
        )
        state.apply_input(email)

        assert state.emails["msg-1"].folder == "inbox"
        assert "msg-1" in state.folders["inbox"]

        move_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="move",
            message_ids=["msg-1"],
            folder="archive",
            from_address="you@example.com",
            to_addresses=["you@example.com"],
            subject="",
            body_text="",
        )

        undo_data = state.create_undo_data(move_input)
        state.apply_input(move_input)

        assert state.emails["msg-1"].folder == "archive"
        assert "msg-1" in state.folders["archive"]
        assert "msg-1" not in state.folders["inbox"]

        state.apply_undo(undo_data)

        assert state.emails["msg-1"].folder == "inbox"
        assert "msg-1" in state.folders["inbox"]
        assert "msg-1" not in state.folders["archive"]

    def test_apply_undo_delete_restores_original_folder(self):
        """Verify undo of delete restores original folder."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        email = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Test",
            body_text="Test",
            message_id="msg-1",
        )
        state.apply_input(email)

        delete_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="delete",
            message_ids=["msg-1"],
            from_address="you@example.com",
            to_addresses=["you@example.com"],
            subject="",
            body_text="",
        )

        undo_data = state.create_undo_data(delete_input)
        state.apply_input(delete_input)

        assert state.emails["msg-1"].folder == "trash"

        state.apply_undo(undo_data)

        assert state.emails["msg-1"].folder == "inbox"

    def test_apply_undo_archive_restores_original_folder(self):
        """Verify undo of archive restores original folder."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        email = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Test",
            body_text="Test",
            message_id="msg-1",
        )
        state.apply_input(email)

        archive_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="archive",
            message_ids=["msg-1"],
            from_address="you@example.com",
            to_addresses=["you@example.com"],
            subject="",
            body_text="",
        )

        undo_data = state.create_undo_data(archive_input)
        state.apply_input(archive_input)

        assert state.emails["msg-1"].folder == "archive"

        state.apply_undo(undo_data)

        assert state.emails["msg-1"].folder == "inbox"

    def test_apply_undo_mark_spam_restores_original_folder(self):
        """Verify undo of mark_spam restores original folder."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        email = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Test",
            body_text="Test",
            message_id="msg-1",
        )
        state.apply_input(email)

        spam_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="mark_spam",
            message_ids=["msg-1"],
            from_address="you@example.com",
            to_addresses=["you@example.com"],
            subject="",
            body_text="",
        )

        undo_data = state.create_undo_data(spam_input)
        state.apply_input(spam_input)

        assert state.emails["msg-1"].folder == "spam"

        state.apply_undo(undo_data)

        assert state.emails["msg-1"].folder == "inbox"

    def test_apply_undo_mark_not_spam_restores_spam_folder(self):
        """Verify undo of mark_not_spam restores spam folder."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        # Create email directly in spam
        email = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="spammer@example.com",
            to_addresses=["you@example.com"],
            subject="Spam",
            body_text="Spam content",
            message_id="msg-1",
        )
        state.apply_input(email)

        # Move to spam first
        spam_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="mark_spam",
            message_ids=["msg-1"],
            from_address="you@example.com",
            to_addresses=["you@example.com"],
            subject="",
            body_text="",
        )
        state.apply_input(spam_input)

        # Now mark as not spam
        not_spam_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="mark_not_spam",
            message_ids=["msg-1"],
            from_address="you@example.com",
            to_addresses=["you@example.com"],
            subject="",
            body_text="",
        )

        undo_data = state.create_undo_data(not_spam_input)
        state.apply_input(not_spam_input)

        assert state.emails["msg-1"].folder == "inbox"

        state.apply_undo(undo_data)

        assert state.emails["msg-1"].folder == "spam"

    def test_apply_undo_add_label_removes_labels(self):
        """Verify undo of add_label removes added labels."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        email = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Test",
            body_text="Test",
            message_id="msg-1",
        )
        state.apply_input(email)

        add_label = EmailInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="add_label",
            message_ids=["msg-1"],
            labels=["work", "urgent"],
            from_address="you@example.com",
            to_addresses=["you@example.com"],
            subject="",
            body_text="",
        )

        undo_data = state.create_undo_data(add_label)
        state.apply_input(add_label)

        assert "work" in state.emails["msg-1"].labels
        assert "urgent" in state.emails["msg-1"].labels
        assert "work" in state.labels
        assert "urgent" in state.labels

        state.apply_undo(undo_data)

        assert "work" not in state.emails["msg-1"].labels
        assert "urgent" not in state.emails["msg-1"].labels
        # Labels that were created by add_label should be removed if empty
        assert "work" not in state.labels
        assert "urgent" not in state.labels

    def test_apply_undo_remove_label_restores_labels(self):
        """Verify undo of remove_label restores removed labels."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        email = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Test",
            body_text="Test",
            message_id="msg-1",
        )
        state.apply_input(email)

        # Add labels first
        add_label = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="add_label",
            message_ids=["msg-1"],
            labels=["work", "urgent"],
            from_address="you@example.com",
            to_addresses=["you@example.com"],
            subject="",
            body_text="",
        )
        state.apply_input(add_label)

        # Remove one label
        remove_label = EmailInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="remove_label",
            message_ids=["msg-1"],
            labels=["work"],
            from_address="you@example.com",
            to_addresses=["you@example.com"],
            subject="",
            body_text="",
        )

        undo_data = state.create_undo_data(remove_label)
        state.apply_input(remove_label)

        assert "work" not in state.emails["msg-1"].labels
        assert "urgent" in state.emails["msg-1"].labels

        state.apply_undo(undo_data)

        assert "work" in state.emails["msg-1"].labels
        assert "urgent" in state.emails["msg-1"].labels
        assert "msg-1" in state.labels["work"]


class TestEmailStateUndoFullCycle:
    """Test full create_undo_data → apply_input → apply_undo cycles.

    GENERAL PATTERN: After undo, state should match pre-apply state.
    """

    def test_full_cycle_receive(self):
        """Verify receive → undo returns to original state."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        original_snapshot = state.get_snapshot()

        email_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Test",
            body_text="Test body",
            message_id="msg-123",
        )

        undo_data = state.create_undo_data(email_input)
        state.apply_input(email_input)
        state.apply_undo(undo_data)

        assert state.get_snapshot() == original_snapshot

    def test_full_cycle_reply(self):
        """Verify reply → undo restores thread state."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        # Setup: receive original email
        original = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Original",
            body_text="Original message",
            message_id="msg-original",
            thread_id="thread-1",
        )
        state.apply_input(original)

        # Capture state after original email
        emails_before = dict(state.emails)
        thread_before = state.threads["thread-1"].model_dump()
        update_count_before = state.update_count
        last_updated_before = state.last_updated

        # Reply
        reply = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="reply",
            from_address="you@example.com",
            to_addresses=["sender@example.com"],
            subject="Re: Original",
            body_text="My reply",
            in_reply_to="msg-original",
            message_id="msg-reply",
        )

        undo_data = state.create_undo_data(reply)
        state.apply_input(reply)
        state.apply_undo(undo_data)

        assert len(state.emails) == len(emails_before)
        assert state.threads["thread-1"].model_dump() == thread_before
        assert state.update_count == update_count_before
        assert state.last_updated == last_updated_before

    def test_full_cycle_multiple_operations(self):
        """Verify multiple operations can be undone in reverse order."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        # Operation 1: Receive email
        receive = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Test",
            body_text="Test",
            message_id="msg-1",
        )
        undo1 = state.create_undo_data(receive)
        state.apply_input(receive)

        # Operation 2: Star email
        star = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="star",
            message_ids=["msg-1"],
            from_address="you@example.com",
            to_addresses=["you@example.com"],
            subject="",
            body_text="",
        )
        undo2 = state.create_undo_data(star)
        state.apply_input(star)

        # Operation 3: Mark as read
        mark_read = EmailInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="mark_read",
            message_ids=["msg-1"],
            from_address="you@example.com",
            to_addresses=["you@example.com"],
            subject="",
            body_text="",
        )
        undo3 = state.create_undo_data(mark_read)
        state.apply_input(mark_read)

        # Verify current state
        assert state.emails["msg-1"].is_starred is True
        assert state.emails["msg-1"].is_read is True
        assert state.update_count == 3

        # Undo operation 3 (mark_read)
        state.apply_undo(undo3)
        assert state.emails["msg-1"].is_read is False
        assert state.update_count == 2

        # Undo operation 2 (star)
        state.apply_undo(undo2)
        assert state.emails["msg-1"].is_starred is False
        assert state.update_count == 1

        # Undo operation 1 (receive)
        state.apply_undo(undo1)
        assert len(state.emails) == 0
        assert state.update_count == 0

    def test_full_cycle_bulk_operations(self):
        """Verify bulk operations can be undone correctly."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        # Add multiple emails
        message_ids = []
        for i in range(3):
            email = EmailInput(
                timestamp=datetime(2025, 1, 1, 12 + i, 0, tzinfo=timezone.utc),
                operation="receive",
                from_address=f"sender{i}@example.com",
                to_addresses=["you@example.com"],
                subject=f"Email {i}",
                body_text=f"Message {i}",
                message_id=f"msg-{i}",
            )
            state.apply_input(email)
            message_ids.append(f"msg-{i}")

        # Bulk mark read
        mark_read = EmailInput(
            timestamp=datetime(2025, 1, 1, 15, 0, tzinfo=timezone.utc),
            operation="mark_read",
            message_ids=message_ids,
            from_address="you@example.com",
            to_addresses=["you@example.com"],
            subject="",
            body_text="",
        )

        undo_data = state.create_undo_data(mark_read)
        state.apply_input(mark_read)

        # All should be read
        for msg_id in message_ids:
            assert state.emails[msg_id].is_read is True

        # Undo
        state.apply_undo(undo_data)

        # All should be unread again
        for msg_id in message_ids:
            assert state.emails[msg_id].is_read is False

    def test_full_cycle_forward(self):
        """Verify forward → undo removes forwarded email and new thread."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        # Receive original
        original = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Original",
            body_text="Original content",
            message_id="msg-original",
        )
        state.apply_input(original)

        emails_before = len(state.emails)
        threads_before = len(state.threads)
        update_count_before = state.update_count
        last_updated_before = state.last_updated

        # Forward
        forward = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="forward",
            from_address="you@example.com",
            to_addresses=["other@example.com"],
            subject="Fwd: Original",
            body_text="Forwarded content",
            in_reply_to="msg-original",
            message_id="msg-forward",
        )

        undo_data = state.create_undo_data(forward)
        state.apply_input(forward)

        assert len(state.emails) == emails_before + 1
        assert len(state.threads) == threads_before + 1

        state.apply_undo(undo_data)

        assert len(state.emails) == emails_before
        assert len(state.threads) == threads_before
        assert state.update_count == update_count_before
        assert state.last_updated == last_updated_before

    def test_full_cycle_reply_all(self):
        """Verify reply_all → undo works same as reply."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        # Receive original with multiple recipients
        original = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com", "other@example.com"],
            cc_addresses=["cc@example.com"],
            subject="Group Thread",
            body_text="Group message",
            message_id="msg-original",
            thread_id="thread-1",
        )
        state.apply_input(original)

        thread_before = state.threads["thread-1"].model_dump()
        update_count_before = state.update_count
        last_updated_before = state.last_updated

        # Reply all
        reply_all = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="reply_all",
            from_address="you@example.com",
            to_addresses=["sender@example.com", "other@example.com"],
            cc_addresses=["cc@example.com"],
            subject="Re: Group Thread",
            body_text="My reply to all",
            in_reply_to="msg-original",
            message_id="msg-reply-all",
        )

        undo_data = state.create_undo_data(reply_all)
        state.apply_input(reply_all)
        state.apply_undo(undo_data)

        assert len(state.emails) == 1
        assert state.threads["thread-1"].model_dump() == thread_before
        assert state.update_count == update_count_before
        assert state.last_updated == last_updated_before

    def test_full_cycle_add_and_remove_labels(self):
        """Verify add_label → remove_label → undo each restores correctly."""
        state = EmailState(last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))

        email = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Test",
            body_text="Test",
            message_id="msg-1",
        )
        state.apply_input(email)

        # Add labels
        add_label = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
            operation="add_label",
            message_ids=["msg-1"],
            labels=["work", "urgent"],
            from_address="you@example.com",
            to_addresses=["you@example.com"],
            subject="",
            body_text="",
        )
        undo_add = state.create_undo_data(add_label)
        state.apply_input(add_label)

        # Remove one label
        remove_label = EmailInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="remove_label",
            message_ids=["msg-1"],
            labels=["work"],
            from_address="you@example.com",
            to_addresses=["you@example.com"],
            subject="",
            body_text="",
        )
        undo_remove = state.create_undo_data(remove_label)
        state.apply_input(remove_label)

        # Verify state
        assert "work" not in state.emails["msg-1"].labels
        assert "urgent" in state.emails["msg-1"].labels

        # Undo remove_label
        state.apply_undo(undo_remove)
        assert "work" in state.emails["msg-1"].labels
        assert "urgent" in state.emails["msg-1"].labels

        # Undo add_label
        state.apply_undo(undo_add)
        assert "work" not in state.emails["msg-1"].labels
        assert "urgent" not in state.emails["msg-1"].labels
