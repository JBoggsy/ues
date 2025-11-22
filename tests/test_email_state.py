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
