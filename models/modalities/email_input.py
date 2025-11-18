"""Email input model."""

import re
from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from models.base_input import ModalityInput


EmailOperation = Literal[
    "receive",
    "send",
    "reply",
    "reply_all",
    "forward",
    "save_draft",
    "send_draft",
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
]


class EmailAttachment(BaseModel):
    """Represents a file attachment with metadata.

    Args:
        filename: Name of the attached file.
        size: File size in bytes.
        mime_type: MIME type (e.g., "application/pdf", "image/jpeg").
        content_id: Optional content ID for inline images (e.g., "cid:image001").
        attachment_id: Unique identifier (auto-generated UUID).
    """

    filename: str = Field(description="Name of the attached file")
    size: int = Field(description="File size in bytes")
    mime_type: str = Field(description="MIME type")
    content_id: Optional[str] = Field(
        default=None, description="Content ID for inline images"
    )
    attachment_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier",
    )

    def to_dict(self) -> dict:
        """Convert attachment to dictionary for API responses.

        Returns:
            Dictionary representation of this attachment.
        """
        result = {
            "filename": self.filename,
            "size": self.size,
            "mime_type": self.mime_type,
            "attachment_id": self.attachment_id,
        }
        if self.content_id:
            result["content_id"] = self.content_id
        return result

    def is_inline(self) -> bool:
        """Check if attachment is inline (has content_id).

        Returns:
            True if this is an inline attachment.
        """
        return self.content_id is not None


class EmailInput(ModalityInput):
    """Input for email-related operations.

    Represents different types of email events (receive, send, reply, move, etc.)
    that modify the email state. Uses an operation-based design where different
    attributes are required depending on the operation type.

    Args:
        modality_type: Always "email" for this input type.
        timestamp: When operation occurred (simulator time).
        input_id: Unique input identifier (auto-generated).
        operation: Type of email operation to perform.
        message_id: For operations on existing emails (optional, auto-generated for new).
        message_ids: For bulk operations on multiple emails.
        from_address: Sender address for send/receive operations.
        to_addresses: Primary recipients for send/receive operations.
        cc_addresses: CC recipients for send operations.
        bcc_addresses: BCC recipients for send operations.
        reply_to_address: Reply-to address if different from sender.
        subject: Email subject line for send/receive operations.
        body_text: Plain text body content for send/receive operations.
        body_html: HTML body content for send/receive operations.
        attachments: File attachments for send/receive operations.
        thread_id: Thread identifier for grouping (auto-generated if new).
        in_reply_to: Message ID this email replies to.
        references: List of message IDs in thread chain.
        priority: Priority level ("high", "normal", "low").
        folder: Target folder for move operations.
        labels: Labels for label operations.
        is_draft: Whether this is a draft email.
    """

    modality_type: str = Field(default="email", frozen=True)
    operation: EmailOperation = Field(description="Type of email operation")
    message_id: Optional[str] = Field(
        default=None, description="Message ID (auto-generated if new)"
    )
    message_ids: Optional[list[str]] = Field(
        default=None, description="Message IDs for bulk operations"
    )
    from_address: Optional[str] = Field(
        default=None, description="Sender email address"
    )
    to_addresses: Optional[list[str]] = Field(
        default=None, description="Primary recipient addresses"
    )
    cc_addresses: Optional[list[str]] = Field(
        default=None, description="CC recipient addresses"
    )
    bcc_addresses: Optional[list[str]] = Field(
        default=None, description="BCC recipient addresses"
    )
    reply_to_address: Optional[str] = Field(
        default=None, description="Reply-to address"
    )
    subject: Optional[str] = Field(default=None, description="Email subject line")
    body_text: Optional[str] = Field(
        default=None, description="Plain text body content"
    )
    body_html: Optional[str] = Field(
        default=None, description="HTML body content"
    )
    attachments: Optional[list[EmailAttachment]] = Field(
        default=None, description="File attachments"
    )
    thread_id: Optional[str] = Field(
        default=None, description="Thread identifier"
    )
    in_reply_to: Optional[str] = Field(
        default=None, description="Message ID this replies to"
    )
    references: Optional[list[str]] = Field(
        default=None, description="Message IDs in thread chain"
    )
    priority: str = Field(default="normal", description="Priority level")
    folder: Optional[str] = Field(
        default=None, description="Target folder for move"
    )
    labels: Optional[list[str]] = Field(
        default=None, description="Labels for label operations"
    )
    is_draft: bool = Field(default=False, description="Whether this is a draft")

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: str) -> str:
        """Validate priority is one of the allowed values.

        Args:
            value: Priority value to validate.

        Returns:
            The validated priority value.

        Raises:
            ValueError: If priority is invalid.
        """
        allowed = {"high", "normal", "low"}
        if value not in allowed:
            raise ValueError(f"Priority must be one of {allowed}, got '{value}'")
        return value

    def _validate_email_address(self, address: str) -> None:
        """Validate email address format.

        Args:
            address: Email address to validate.

        Raises:
            ValueError: If email address format is invalid.
        """
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, address):
            raise ValueError(f"Invalid email address format: '{address}'")

    def _validate_compose_fields(self) -> None:
        """Validate fields required for composing/sending emails.

        Raises:
            ValueError: If required fields are missing or invalid.
        """
        if not self.from_address:
            raise ValueError(f"Operation '{self.operation}' requires from_address")
        self._validate_email_address(self.from_address)

        if not self.to_addresses or len(self.to_addresses) == 0:
            raise ValueError(f"Operation '{self.operation}' requires to_addresses")
        for addr in self.to_addresses:
            self._validate_email_address(addr)

        if self.cc_addresses:
            for addr in self.cc_addresses:
                self._validate_email_address(addr)

        if self.bcc_addresses:
            for addr in self.bcc_addresses:
                self._validate_email_address(addr)

        if self.reply_to_address:
            self._validate_email_address(self.reply_to_address)

        if not self.subject:
            raise ValueError(f"Operation '{self.operation}' requires subject")

        if not self.body_text:
            raise ValueError(f"Operation '{self.operation}' requires body_text")

    def _validate_single_message_operation(self) -> None:
        """Validate operations that require a single message_id.

        Raises:
            ValueError: If message_id is missing.
        """
        if not self.message_id:
            raise ValueError(f"Operation '{self.operation}' requires message_id")

    def _validate_bulk_operation(self) -> None:
        """Validate operations that can work on multiple messages.

        Raises:
            ValueError: If neither message_id nor message_ids is provided.
        """
        if not self.message_id and not self.message_ids:
            raise ValueError(
                f"Operation '{self.operation}' requires message_id or message_ids"
            )

    def _validate_reply_operation(self) -> None:
        """Validate reply/reply_all operations.

        Raises:
            ValueError: If required fields are missing.
        """
        if not self.in_reply_to:
            raise ValueError(f"Operation '{self.operation}' requires in_reply_to")
        self._validate_compose_fields()

    def _validate_forward_operation(self) -> None:
        """Validate forward operations.

        Raises:
            ValueError: If required fields are missing.
        """
        if not self.in_reply_to:
            raise ValueError(f"Operation '{self.operation}' requires in_reply_to")
        self._validate_compose_fields()

    def _validate_move_operation(self) -> None:
        """Validate move operations.

        Raises:
            ValueError: If required fields are missing.
        """
        self._validate_bulk_operation()
        if not self.folder:
            raise ValueError(f"Operation '{self.operation}' requires folder")

    def _validate_label_operation(self) -> None:
        """Validate add/remove label operations.

        Raises:
            ValueError: If required fields are missing.
        """
        self._validate_bulk_operation()
        if not self.labels or len(self.labels) == 0:
            raise ValueError(f"Operation '{self.operation}' requires labels")

    def validate_input(self) -> None:
        """Perform modality-specific validation beyond Pydantic field validation.

        Validates that required fields are present for each operation type
        and that email addresses are properly formatted.

        Raises:
            ValueError: If validation fails with descriptive message.
        """
        operation_validators = {
            "receive": self._validate_compose_fields,
            "send": self._validate_compose_fields,
            "reply": self._validate_reply_operation,
            "reply_all": self._validate_reply_operation,
            "forward": self._validate_forward_operation,
            "save_draft": self._validate_compose_fields,
            "send_draft": self._validate_single_message_operation,
            "mark_read": self._validate_bulk_operation,
            "mark_unread": self._validate_bulk_operation,
            "star": self._validate_bulk_operation,
            "unstar": self._validate_bulk_operation,
            "move": self._validate_move_operation,
            "delete": self._validate_bulk_operation,
            "archive": self._validate_bulk_operation,
            "add_label": self._validate_label_operation,
            "remove_label": self._validate_label_operation,
            "mark_spam": self._validate_bulk_operation,
            "mark_not_spam": self._validate_bulk_operation,
        }

        validator = operation_validators.get(self.operation)
        if validator:
            validator()

    def get_affected_entities(self) -> list[str]:
        """Return list of entity IDs affected by this input.

        For email operations, we track both individual messages and threads.

        Returns:
            List containing affected message and/or thread identifiers.
        """
        entities = []

        if self.message_id:
            entities.append(f"email:{self.message_id}")

        if self.message_ids:
            entities.extend([f"email:{mid}" for mid in self.message_ids])

        if self.thread_id:
            entities.append(f"thread:{self.thread_id}")

        if not entities and self.operation in ("receive", "send"):
            message_id = self.message_id or str(uuid4())
            entities.append(f"email:{message_id}")

        return entities

    def get_summary(self) -> str:
        """Return human-readable one-line summary of this input.

        Returns:
            Brief description of the operation for logging/UI display.
        """
        op = self.operation

        if op in ("receive", "send"):
            from_addr = self.from_address or "unknown"
            subject = self.subject or "(no subject)"
            if len(subject) > 40:
                subject = subject[:37] + "..."
            return f"{op.capitalize()} email from {from_addr}: '{subject}'"

        if op in ("reply", "reply_all", "forward"):
            to_addrs = ", ".join(self.to_addresses) if self.to_addresses else "unknown"
            return f"{op.replace('_', ' ').capitalize()} to {to_addrs}"

        if op in ("save_draft", "send_draft"):
            subject = self.subject or "(no subject)"
            if len(subject) > 40:
                subject = subject[:37] + "..."
            return f"{op.replace('_', ' ').capitalize()}: '{subject}'"

        if op in ("mark_read", "mark_unread", "star", "unstar", "delete", "archive"):
            count = 1 if self.message_id else len(self.message_ids or [])
            return f"{op.replace('_', ' ').capitalize()} {count} email(s)"

        if op == "move":
            count = 1 if self.message_id else len(self.message_ids or [])
            folder = self.folder or "unknown"
            return f"Move {count} email(s) to {folder}"

        if op in ("add_label", "remove_label"):
            count = 1 if self.message_id else len(self.message_ids or [])
            labels = ", ".join(self.labels) if self.labels else "unknown"
            action = "Add" if op == "add_label" else "Remove"
            return f"{action} labels [{labels}] to/from {count} email(s)"

        if op in ("mark_spam", "mark_not_spam"):
            count = 1 if self.message_id else len(self.message_ids or [])
            return f"{op.replace('_', ' ').capitalize()} {count} email(s)"

        return f"Email operation: {op}"

    def should_merge_with(self, other: ModalityInput) -> bool:
        """Determine if this input should be merged with another input.

        Email operations should not be merged as each represents a distinct
        action that should be tracked separately.

        Args:
            other: Another input to compare against.

        Returns:
            Always False for email operations.
        """
        return False
