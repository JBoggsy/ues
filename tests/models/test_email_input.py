"""Unit tests for email input modality.

This module tests both general ModalityInput behavior and email-specific features.
"""

from datetime import datetime, timezone

import pytest

from models.modalities.email_input import EmailAttachment, EmailInput


class TestEmailInputInstantiation:
    """Test instantiation patterns for EmailInput.

    GENERAL PATTERN: All ModalityInput subclasses should instantiate with timestamp
    and modality parameters.
    """

    def test_minimal_instantiation(self):
        """Verify EmailInput instantiates with minimal required fields."""
        email = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
            subject="Test Subject",
            body_text="Test body content.",
        )

        assert email.timestamp == datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        assert email.modality_type == "email"
        assert email.operation == "receive"
        assert email.from_address == "sender@example.com"
        assert email.to_addresses == ["recipient@example.com"]
        assert email.subject == "Test Subject"
        assert email.body_text == "Test body content."

    def test_full_instantiation(self):
        """Verify EmailInput instantiates with all optional fields."""
        attachments = [
            EmailAttachment(
                filename="document.pdf",
                size=102400,
                mime_type="application/pdf",
            )
        ]

        email = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
            cc_addresses=["cc@example.com"],
            bcc_addresses=["bcc@example.com"],
            reply_to_address="reply@example.com",
            subject="Test Subject",
            body_text="Plain text body.",
            body_html="<p>HTML body.</p>",
            attachments=attachments,
            message_id="msg-123",
            thread_id="thread-456",
            in_reply_to="msg-100",
            references=["msg-100", "msg-101"],
            priority="high",
        )

        assert email.cc_addresses == ["cc@example.com"]
        assert email.bcc_addresses == ["bcc@example.com"]
        assert email.reply_to_address == "reply@example.com"
        assert email.body_html == "<p>HTML body.</p>"
        assert len(email.attachments) == 1
        assert email.attachments[0].filename == "document.pdf"
        assert email.message_id == "msg-123"
        assert email.thread_id == "thread-456"
        assert email.in_reply_to == "msg-100"
        assert email.references == ["msg-100", "msg-101"]
        assert email.priority == "high"

    def test_default_values(self):
        """Verify EmailInput applies correct defaults for optional fields."""
        email = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
            subject="Test",
            body_text="Test",
        )

        assert email.cc_addresses is None
        assert email.bcc_addresses is None
        assert email.reply_to_address is None
        assert email.body_html is None
        assert email.attachments is None
        assert email.message_id is None
        assert email.thread_id is None
        assert email.in_reply_to is None
        assert email.references is None
        assert email.priority == "normal"

    def test_modality_auto_set(self):
        """GENERAL PATTERN: Verify modality field is automatically set."""
        email = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
            subject="Test",
            body_text="Test",
        )

        assert email.modality_type == "email"


class TestEmailInputValidation:
    """Test validation logic for EmailInput.

    MODALITY-SPECIFIC: Email addresses, operation types, priority levels.
    """

    def test_valid_email_addresses(self):
        """Verify EmailInput accepts valid email address formats."""
        email = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="user.name+tag@example.co.uk",
            to_addresses=["recipient@example.com"],
            cc_addresses=["cc.user@example.org"],
            subject="Test",
            body_text="Test",
        )

        assert email.from_address == "user.name+tag@example.co.uk"
        assert email.cc_addresses == ["cc.user@example.org"]

    def test_valid_operations(self):
        """MODALITY-SPECIFIC: Verify all 18 email operations are valid."""
        operations = [
            "receive",
            "send",
            "reply",
            "reply_all",
            "forward",
            "mark_read",
            "mark_unread",
            "star",
            "unstar",
            "move",
            "delete",
            "archive",
            "add_label",
            "remove_label",
            "mark_spam",
            "mark_not_spam",
            "save_draft",
            "send_draft",
        ]

        for operation in operations:
            email = EmailInput(
                timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
                operation=operation,
                from_address="sender@example.com",
                to_addresses=["recipient@example.com"],
                subject="Test",
                body_text="Test",
            )
            assert email.operation == operation

    def test_valid_priorities(self):
        """MODALITY-SPECIFIC: Verify priority levels are valid."""
        priorities = ["low", "normal", "high"]

        for priority in priorities:
            email = EmailInput(
                timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
                operation="receive",
                from_address="sender@example.com",
                to_addresses=["recipient@example.com"],
                subject="Test",
                body_text="Test",
                priority=priority,
            )
            assert email.priority == priority

    def test_multiple_recipients(self):
        """MODALITY-SPECIFIC: Verify handling of multiple recipients."""
        email = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="send",
            from_address="sender@example.com",
            to_addresses=["user1@example.com", "user2@example.com", "user3@example.com"],
            cc_addresses=["cc1@example.com", "cc2@example.com"],
            bcc_addresses=["bcc1@example.com"],
            subject="Team Update",
            body_text="Hello team!",
        )

        assert len(email.to_addresses) == 3
        assert len(email.cc_addresses) == 2
        assert len(email.bcc_addresses) == 1

    def test_html_and_text_bodies(self):
        """MODALITY-SPECIFIC: Verify both plain text and HTML bodies can coexist."""
        email = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
            subject="Test",
            body_text="Plain text version",
            body_html="<html><body><p>HTML version</p></body></html>",
        )

        assert email.body_text == "Plain text version"
        assert email.body_html == "<html><body><p>HTML version</p></body></html>"


class TestEmailAttachment:
    """Test EmailAttachment Pydantic model.

    MODALITY-SPECIFIC: Email attachments with content IDs for inline images.
    """

    def test_attachment_instantiation(self):
        """Verify EmailAttachment instantiates with required fields."""
        attachment = EmailAttachment(
            filename="document.pdf",
            size=102400,
            mime_type="application/pdf",
        )

        assert attachment.filename == "document.pdf"
        assert attachment.size == 102400
        assert attachment.mime_type == "application/pdf"
        assert attachment.content_id is None
        assert attachment.attachment_id is not None  # Auto-generated UUID

    def test_attachment_with_content_id(self):
        """MODALITY-SPECIFIC: Verify inline images use content_id."""
        attachment = EmailAttachment(
            filename="logo.png",
            size=51200,
            mime_type="image/png",
            content_id="<image1@example.com>",
            attachment_id="att-123",
        )

        assert attachment.content_id == "<image1@example.com>"
        assert attachment.attachment_id == "att-123"

    def test_attachment_serialization(self):
        """Verify EmailAttachment can be serialized and deserialized."""
        attachment = EmailAttachment(
            filename="report.docx",
            size=204800,
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            attachment_id="att-456",
        )

        dumped = attachment.model_dump()
        restored = EmailAttachment.model_validate(dumped)

        assert restored.filename == attachment.filename
        assert restored.size == attachment.size
        assert restored.mime_type == attachment.mime_type
        assert restored.attachment_id == attachment.attachment_id


class TestEmailInputSerialization:
    """Test serialization and deserialization of EmailInput.

    GENERAL PATTERN: All ModalityInput instances must support model_dump() and
    model_validate() for persistence and API communication.
    """

    def test_simple_email_serialization(self):
        """Verify simple email can be serialized and deserialized."""
        original = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
            subject="Test Subject",
            body_text="Test body.",
        )

        dumped = original.model_dump()
        restored = EmailInput.model_validate(dumped)

        assert restored.timestamp == original.timestamp
        assert restored.operation == original.operation
        assert restored.from_address == original.from_address
        assert restored.to_addresses == original.to_addresses
        assert restored.subject == original.subject
        assert restored.body_text == original.body_text

    def test_complex_email_serialization(self):
        """Verify complex email with attachments can be serialized."""
        attachments = [
            EmailAttachment(
                filename="document.pdf",
                size=102400,
                mime_type="application/pdf",
                attachment_id="att-1",
            ),
            EmailAttachment(
                filename="image.png",
                size=51200,
                mime_type="image/png",
                content_id="<img1@example.com>",
                attachment_id="att-2",
            ),
        ]

        original = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
            cc_addresses=["cc@example.com"],
            subject="Complex Email",
            body_text="Plain text",
            body_html="<p>HTML content</p>",
            attachments=attachments,
            message_id="msg-123",
            thread_id="thread-456",
            priority="high",
        )

        dumped = original.model_dump()
        restored = EmailInput.model_validate(dumped)

        assert len(restored.attachments) == 2
        assert restored.attachments[0].filename == "document.pdf"
        assert restored.attachments[1].content_id == "<img1@example.com>"
        assert restored.message_id == "msg-123"
        assert restored.thread_id == "thread-456"
        assert restored.priority == "high"


class TestEmailInputFromFixtures:
    """Test EmailInput using pre-built fixtures.

    GENERAL PATTERN: Fixtures provide reusable test data.
    """

    def test_simple_email_fixture(self, simple_email_input):
        """Verify simple email fixture is valid."""
        assert simple_email_input.operation == "receive"
        assert simple_email_input.from_address == "sender@example.com"
        assert simple_email_input.subject == "Simple Test Email"
        assert simple_email_input.modality_type == "email"

    def test_work_email_fixture(self, work_email_input):
        """Verify work email fixture includes CC recipients."""
        assert work_email_input.operation == "receive"
        assert "boss@company.com" in work_email_input.cc_addresses
        assert work_email_input.priority == "high"

    def test_meeting_invite_fixture(self, meeting_invite_input):
        """Verify meeting invite fixture has calendar-related content."""
        assert "meeting" in meeting_invite_input.subject.lower()
        assert meeting_invite_input.operation == "receive"

    def test_email_with_attachment_fixture(self, email_with_attachment_input):
        """Verify email with attachment fixture includes attachments."""
        assert len(email_with_attachment_input.attachments) > 0
        assert email_with_attachment_input.attachments[0].filename is not None


class TestEmailInputEdgeCases:
    """Test edge cases and boundary conditions.

    MODALITY-SPECIFIC: Empty subjects, very long bodies, many attachments.
    """

    def test_empty_subject(self):
        """Verify email with empty subject is valid."""
        email = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
            subject="",
            body_text="Body without subject.",
        )

        assert email.subject == ""

    def test_empty_body(self):
        """Verify email with empty body is valid."""
        email = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
            subject="Subject without body",
            body_text="",
        )

        assert email.body_text == ""

    def test_very_long_body(self):
        """Verify email handles very long body text."""
        long_body = "Lorem ipsum dolor sit amet. " * 1000

        email = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
            subject="Long Email",
            body_text=long_body,
        )

        assert len(email.body_text) > 25000

    def test_many_attachments(self):
        """MODALITY-SPECIFIC: Verify email handles multiple attachments."""
        attachments = [
            EmailAttachment(
                filename=f"file{i}.pdf",
                size=10240 * i,
                mime_type="application/pdf",
            )
            for i in range(1, 11)
        ]

        email = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
            subject="Multiple Attachments",
            body_text="See attached files.",
            attachments=attachments,
        )

        assert len(email.attachments) == 10

    def test_thread_chain_references(self):
        """MODALITY-SPECIFIC: Verify handling of long thread reference chains."""
        references = [f"msg-{i}" for i in range(1, 21)]

        email = EmailInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="reply",
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
            subject="Re: Long Thread",
            body_text="Continuing the conversation.",
            in_reply_to="msg-20",
            references=references,
        )

        assert len(email.references) == 20
        assert email.in_reply_to == "msg-20"
