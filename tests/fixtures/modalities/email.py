"""Fixtures for Email modality."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from models.modalities.email_input import EmailInput, EmailAttachment
from models.modalities.email_state import EmailState


def create_email_input(
    operation: str = "receive",
    from_address: str = "sender@example.com",
    to_addresses: list[str] | None = None,
    subject: str = "Test Email",
    body_text: str = "This is a test email.",
    timestamp: datetime | None = None,
    **kwargs,
) -> EmailInput:
    """Create an EmailInput with sensible defaults.

    Args:
        operation: Email operation type (default: "receive").
        from_address: Sender email address.
        to_addresses: List of recipient addresses.
        subject: Email subject line.
        body_text: Email body content.
        timestamp: When operation occurred (defaults to now).
        **kwargs: Additional fields to override.

    Returns:
        EmailInput instance ready for testing.
    """
    return EmailInput(
        operation=operation,
        from_address=from_address,
        to_addresses=to_addresses or ["recipient@example.com"],
        subject=subject,
        body_text=body_text,
        timestamp=timestamp or datetime.now(timezone.utc),
        **kwargs,
    )


def create_email_state(
    last_updated: datetime | None = None,
    **kwargs,
) -> EmailState:
    """Create an EmailState with sensible defaults.

    Args:
        last_updated: When state was last updated (defaults to now).
        **kwargs: Additional fields to override.

    Returns:
        EmailState instance ready for testing.
    """
    return EmailState(
        last_updated=last_updated or datetime.now(timezone.utc),
        **kwargs,
    )


# Pre-built email examples
SIMPLE_EMAIL = create_email_input()

WORK_EMAIL = create_email_input(
    from_address="boss@company.com",
    to_addresses=["you@company.com"],
    subject="Project Update",
    body_text="Please review the attached project status report.",
)

MEETING_INVITE = create_email_input(
    from_address="calendar@company.com",
    to_addresses=["you@company.com"],
    cc_addresses=["team@company.com"],
    subject="Team Meeting - Tomorrow 2pm",
    body_text="Join us for the quarterly planning meeting.\n\nAgenda:\n1. Q4 Review\n2. Q1 Planning\n3. Team Updates",
)

EMAIL_WITH_ATTACHMENT = create_email_input(
    from_address="colleague@company.com",
    to_addresses=["you@company.com"],
    subject="Report Attached",
    body_text="Here's the report you requested.",
    attachments=[
        EmailAttachment(
            filename="report.pdf",
            size=1024000,
            mime_type="application/pdf",
        )
    ],
)

EMAIL_WITH_MULTIPLE_ATTACHMENTS = create_email_input(
    from_address="finance@company.com",
    to_addresses=["you@company.com"],
    subject="Q4 Financial Documents",
    body_text="Attached are the financial statements.",
    attachments=[
        EmailAttachment(filename="q4_report.pdf", size=500000, mime_type="application/pdf"),
        EmailAttachment(filename="budget.xlsx", size=250000, mime_type="application/vnd.ms-excel"),
        EmailAttachment(filename="summary.docx", size=100000, mime_type="application/msword"),
    ],
)

SPAM_EMAIL = create_email_input(
    from_address="spam@suspicious.com",
    to_addresses=["you@example.com"],
    subject="You won the lottery!!!",
    body_text="Click here now to claim your prize!!!",
)

REPLY_EMAIL = create_email_input(
    operation="reply",
    from_address="you@company.com",
    to_addresses=["boss@company.com"],
    subject="Re: Project Update",
    body_text="Thank you for the update. I'll review it today.",
    in_reply_to=str(uuid4()),
)

FORWARD_EMAIL = create_email_input(
    operation="forward",
    from_address="you@company.com",
    to_addresses=["colleague@company.com"],
    subject="Fwd: Important Information",
    body_text="FYI - see below",
)

DRAFT_EMAIL = create_email_input(
    operation="save_draft",
    from_address="you@company.com",
    to_addresses=["client@external.com"],
    subject="Proposal Draft",
    body_text="Dear Client,\n\n[Work in progress]",
)

HIGH_PRIORITY_EMAIL = create_email_input(
    from_address="ceo@company.com",
    to_addresses=["all@company.com"],
    subject="URGENT: Company Announcement",
    body_text="Please read this important announcement.",
    priority="high",
)

EMAIL_WITH_CC_BCC = create_email_input(
    from_address="manager@company.com",
    to_addresses=["team-lead@company.com"],
    cc_addresses=["team@company.com"],
    bcc_addresses=["hr@company.com"],
    subject="Performance Review Schedule",
    body_text="Please see the attached schedule for Q1 reviews.",
)

HTML_EMAIL = create_email_input(
    from_address="marketing@company.com",
    to_addresses=["you@company.com"],
    subject="Newsletter - January 2025",
    body_text="Plain text version of newsletter",
    body_html="<html><body><h1>Newsletter</h1><p>HTML content here</p></body></html>",
)

THREADED_EMAIL = create_email_input(
    from_address="colleague@company.com",
    to_addresses=["you@company.com"],
    subject="Re: Re: Project Discussion",
    body_text="I agree with your latest point.",
    thread_id="thread-12345",
    in_reply_to="msg-previous",
    references=["msg-1", "msg-2", "msg-previous"],
)


# State examples
EMPTY_INBOX = create_email_state()


# Invalid examples for validation testing
INVALID_EMAIL_INPUTS = {
    "missing_from": {
        "operation": "receive",
        "to_addresses": ["test@example.com"],
        "timestamp": datetime.now(timezone.utc),
    },
    "bad_email_format": {
        "operation": "receive",
        "from_address": "not-an-email",
        "to_addresses": ["test@example.com"],
        "timestamp": datetime.now(timezone.utc),
    },
    "empty_to_addresses": {
        "operation": "send",
        "from_address": "sender@example.com",
        "to_addresses": [],
        "timestamp": datetime.now(timezone.utc),
    },
}


# JSON fixtures for API testing
EMAIL_JSON_EXAMPLES = {
    "simple": {
        "modality_type": "email",
        "timestamp": "2025-01-15T10:30:00Z",
        "operation": "receive",
        "from_address": "sender@example.com",
        "to_addresses": ["you@example.com"],
        "subject": "Hello",
        "body_text": "Test message",
    },
    "with_attachment": {
        "modality_type": "email",
        "timestamp": "2025-01-15T14:00:00Z",
        "operation": "receive",
        "from_address": "colleague@company.com",
        "to_addresses": ["you@company.com"],
        "subject": "Document",
        "body_text": "See attached",
        "attachments": [
            {
                "filename": "doc.pdf",
                "size": 50000,
                "mime_type": "application/pdf",
            }
        ],
    },
    "reply": {
        "modality_type": "email",
        "timestamp": "2025-01-15T16:00:00Z",
        "operation": "reply",
        "from_address": "you@company.com",
        "to_addresses": ["boss@company.com"],
        "subject": "Re: Project Update",
        "body_text": "I'll review this today.",
        "in_reply_to": "msg-12345",
    },
}


# Pytest fixtures for use in tests
@pytest.fixture
def simple_email_input():
    """Provide a simple email input for testing."""
    return create_email_input(
        from_address="sender@example.com",
        to_addresses=["recipient@example.com"],
        subject="Simple Test Email",
        body_text="This is a simple test message.",
    )


@pytest.fixture
def work_email_input():
    """Provide a work email with CC and high priority."""
    return create_email_input(
        from_address="boss@company.com",
        to_addresses=["you@company.com"],
        cc_addresses=["boss@company.com"],
        subject="Urgent Project Update",
        body_text="Please review ASAP.",
        priority="high",
    )


@pytest.fixture
def meeting_invite_input():
    """Provide a meeting invitation email."""
    return create_email_input(
        from_address="calendar@company.com",
        to_addresses=["you@company.com"],
        subject="Team Meeting - Tomorrow 2pm",
        body_text="Join us for the quarterly planning meeting.",
    )


@pytest.fixture
def email_with_attachment_input():
    """Provide an email with a PDF attachment."""
    return create_email_input(
        from_address="colleague@company.com",
        to_addresses=["you@company.com"],
        subject="Report Attached",
        body_text="Here's the report you requested.",
        attachments=[
            EmailAttachment(
                filename="report.pdf",
                size=1024000,
                mime_type="application/pdf",
            )
        ],
    )


@pytest.fixture
def email_state():
    """Provide a fresh EmailState instance for testing."""
    return create_email_state()
