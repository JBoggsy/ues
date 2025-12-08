"""Email state model."""

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from models.base_input import ModalityInput
from models.base_state import ModalityState


class Email(BaseModel):
    """Represents a complete email message with all metadata.

    Args:
        message_id: Unique message identifier (UUID).
        thread_id: Thread identifier for conversation grouping.
        from_address: Sender email address.
        to_addresses: Primary recipient addresses.
        cc_addresses: CC recipient addresses.
        bcc_addresses: BCC recipient addresses.
        reply_to_address: Reply-to address if different from sender.
        subject: Email subject line.
        body_text: Plain text body content.
        body_html: HTML body content.
        attachments: List of attachments.
        in_reply_to: Message ID this email replies to.
        references: List of message IDs in thread chain.
        sent_at: When email was originally sent.
        received_at: When email arrived in inbox.
        is_read: Read/unread status.
        is_starred: Starred/flagged status.
        priority: Priority level.
        folder: Current folder location.
        labels: List of applied labels/tags.
    """

    message_id: str = Field(description="Unique message identifier")
    thread_id: str = Field(description="Thread identifier for conversation grouping")
    from_address: str = Field(description="Sender email address")
    to_addresses: list[str] = Field(description="Primary recipient addresses")
    cc_addresses: list[str] = Field(default_factory=list, description="CC recipient addresses")
    bcc_addresses: list[str] = Field(default_factory=list, description="BCC recipient addresses")
    reply_to_address: Optional[str] = Field(default=None, description="Reply-to address if different from sender")
    subject: str = Field(description="Email subject line")
    body_text: str = Field(description="Plain text body content")
    body_html: Optional[str] = Field(default=None, description="HTML body content")
    attachments: list = Field(default_factory=list, description="List of attachments")
    in_reply_to: Optional[str] = Field(default=None, description="Message ID this email replies to")
    references: list[str] = Field(default_factory=list, description="List of message IDs in thread chain")
    sent_at: datetime = Field(description="When email was originally sent")
    received_at: datetime = Field(description="When email arrived in inbox")
    is_read: bool = Field(default=False, description="Read/unread status")
    is_starred: bool = Field(default=False, description="Starred/flagged status")
    priority: str = Field(default="normal", description="Priority level")
    folder: str = Field(default="inbox", description="Current folder location")
    labels: list[str] = Field(default_factory=list, description="List of applied labels/tags")

    def mark_read(self) -> None:
        """Set email as read."""
        self.is_read = True

    def mark_unread(self) -> None:
        """Set email as unread."""
        self.is_read = False

    def toggle_star(self) -> None:
        """Toggle starred status."""
        self.is_starred = not self.is_starred

    def add_label(self, label: str) -> None:
        """Add a label if not already present.

        Args:
            label: Label to add.
        """
        if label not in self.labels:
            self.labels.append(label)

    def remove_label(self, label: str) -> None:
        """Remove a label if present.

        Args:
            label: Label to remove.
        """
        if label in self.labels:
            self.labels.remove(label)

    def move_to_folder(self, folder: str) -> None:
        """Change folder location.

        Args:
            folder: Target folder name.
        """
        self.folder = folder


class EmailThread(BaseModel):
    """Represents a conversation thread grouping related emails.

    Args:
        thread_id: Unique thread identifier.
        subject: Thread subject (from first email).
        participant_addresses: All email addresses involved.
        message_ids: Ordered list of message IDs in thread.
        created_at: When thread started.
        last_message_at: When last email was added.
        message_count: Number of emails in thread.
        unread_count: Number of unread emails in thread.
    """

    thread_id: str = Field(description="Unique thread identifier")
    subject: str = Field(description="Thread subject (from first email)")
    participant_addresses: set[str] = Field(default_factory=set, description="All email addresses involved")
    message_ids: list[str] = Field(default_factory=list, description="Ordered list of message IDs in thread")
    created_at: datetime = Field(description="When thread started")
    last_message_at: datetime = Field(description="When last email was added")
    message_count: int = Field(default=0, description="Number of emails in thread")
    unread_count: int = Field(default=0, description="Number of unread emails in thread")

    def add_message(self, message_id: str, timestamp: datetime) -> None:
        """Add message to thread.

        Args:
            message_id: Message to add.
            timestamp: Message timestamp.
        """
        if message_id not in self.message_ids:
            self.message_ids.append(message_id)
            self.message_count += 1
            if timestamp > self.last_message_at:
                self.last_message_at = timestamp

    def update_unread_count(self, delta: int) -> None:
        """Adjust unread count.

        Args:
            delta: Amount to change count by (positive or negative).
        """
        self.unread_count = max(0, self.unread_count + delta)


class EmailSummary(BaseModel):
    """Summary representation of an email for compact API responses.

    Contains only essential metadata without full body content.

    Args:
        message_id: Unique message identifier.
        thread_id: Thread identifier for conversation grouping.
        from_address: Sender email address.
        to_addresses: Primary recipient addresses.
        subject: Email subject line.
        sent_at: When email was originally sent.
        received_at: When email arrived in inbox.
        is_read: Read/unread status.
        is_starred: Starred/flagged status.
        folder: Current folder location.
        has_attachments: Whether email has attachments.
        attachment_count: Number of attachments.
        body_preview: First ~100 chars of body text.
    """

    message_id: str = Field(description="Unique message identifier")
    thread_id: str = Field(description="Thread identifier for conversation grouping")
    from_address: str = Field(description="Sender email address")
    to_addresses: list[str] = Field(description="Primary recipient addresses")
    subject: str = Field(description="Email subject line")
    sent_at: datetime = Field(description="When email was originally sent")
    received_at: datetime = Field(description="When email arrived in inbox")
    is_read: bool = Field(description="Read/unread status")
    is_starred: bool = Field(description="Starred/flagged status")
    folder: str = Field(description="Current folder location")
    has_attachments: bool = Field(description="Whether email has attachments")
    attachment_count: int = Field(description="Number of attachments")
    body_preview: str = Field(description="First ~100 chars of body text")

    @classmethod
    def from_email(cls, email: "Email", preview_length: int = 100) -> "EmailSummary":
        """Create an EmailSummary from a full Email object.

        Args:
            email: The full Email object to summarize.
            preview_length: Maximum length of body preview (default 100).

        Returns:
            An EmailSummary instance.
        """
        body_preview = email.body_text[:preview_length]
        if len(email.body_text) > preview_length:
            body_preview = body_preview.rstrip() + "..."

        return cls(
            message_id=email.message_id,
            thread_id=email.thread_id,
            from_address=email.from_address,
            to_addresses=email.to_addresses,
            subject=email.subject,
            sent_at=email.sent_at,
            received_at=email.received_at,
            is_read=email.is_read,
            is_starred=email.is_starred,
            folder=email.folder,
            has_attachments=len(email.attachments) > 0,
            attachment_count=len(email.attachments),
            body_preview=body_preview,
        )


class EmailState(ModalityState):
    """Current email system state.

    Tracks complete email storage including messages, threads, folders, labels, and drafts.

    Args:
        modality_type: Always "email" for this state type.
        last_updated: When state was last modified.
        update_count: Number of operations applied.
        emails: All emails indexed by message_id.
        threads: All threads indexed by thread_id.
        folders: Folder name to list of message_ids.
        labels: Label name to list of message_ids.
        drafts: Draft emails indexed by message_id.
        user_email_address: The simulated user's email address.
    """

    modality_type: str = Field(default="email", frozen=True)
    emails: dict[str, Email] = Field(
        default_factory=dict, description="All emails indexed by message_id"
    )
    threads: dict[str, EmailThread] = Field(
        default_factory=dict, description="All threads indexed by thread_id"
    )
    folders: dict[str, list[str]] = Field(
        default_factory=dict, description="Folder to message_ids mapping"
    )
    labels: dict[str, list[str]] = Field(
        default_factory=dict, description="Label to message_ids mapping"
    )
    drafts: dict[str, Email] = Field(
        default_factory=dict, description="Draft emails indexed by message_id"
    )
    user_email_address: str = Field(
        default="user@example.com", description="User's email address"
    )

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True

    def model_post_init(self, __context: Any) -> None:
        """Initialize standard folders after model creation.

        Args:
            __context: Pydantic context (unused).
        """
        standard_folders = ["inbox", "sent", "drafts", "trash", "spam", "archive"]
        for folder in standard_folders:
            if folder not in self.folders:
                self.folders[folder] = []

    def apply_input(self, input_data: ModalityInput) -> None:
        """Apply an EmailInput to modify this state.

        Dispatches to operation-specific handlers based on operation type.

        Args:
            input_data: The EmailInput to apply to this state.

        Raises:
            ValueError: If input_data is not an EmailInput.
        """
        from models.modalities.email_input import EmailInput

        if not isinstance(input_data, EmailInput):
            raise ValueError(
                f"EmailState can only apply EmailInput, got {type(input_data)}"
            )

        input_data.validate_input()

        operation_handlers = {
            "receive": self._handle_receive,
            "send": self._handle_send,
            "reply": self._handle_reply,
            "reply_all": self._handle_reply_all,
            "forward": self._handle_forward,
            "save_draft": self._handle_save_draft,
            "send_draft": self._handle_send_draft,
            "mark_read": self._handle_mark_read,
            "mark_unread": self._handle_mark_unread,
            "star": self._handle_star,
            "unstar": self._handle_unstar,
            "move": self._handle_move,
            "delete": self._handle_delete,
            "archive": self._handle_archive,
            "add_label": self._handle_add_label,
            "remove_label": self._handle_remove_label,
            "mark_spam": self._handle_mark_spam,
            "mark_not_spam": self._handle_mark_not_spam,
        }

        handler = operation_handlers.get(input_data.operation)
        if handler:
            handler(input_data)
            self.last_updated = input_data.timestamp
            self.update_count += 1
        else:
            raise ValueError(f"Unknown operation: {input_data.operation}")

    def _handle_receive(self, input_data: "EmailInput") -> None:
        """Handle receiving a new email.

        Args:
            input_data: Email input data.
        """
        message_id = input_data.message_id or str(uuid4())
        thread_id = input_data.thread_id or f"thread-{message_id}"

        email = Email(
            message_id=message_id,
            thread_id=thread_id,
            from_address=input_data.from_address,
            to_addresses=input_data.to_addresses,
            cc_addresses=input_data.cc_addresses or [],
            bcc_addresses=input_data.bcc_addresses or [],
            reply_to_address=input_data.reply_to_address,
            subject=input_data.subject,
            body_text=input_data.body_text,
            body_html=input_data.body_html,
            attachments=input_data.attachments or [],
            in_reply_to=input_data.in_reply_to,
            references=input_data.references or [],
            sent_at=input_data.timestamp,
            received_at=input_data.timestamp,
            priority=input_data.priority,
            folder="inbox",
            is_read=False,
        )

        self.emails[message_id] = email
        self.folders["inbox"].append(message_id)

        if thread_id not in self.threads:
            self._create_thread(email)
        else:
            self._add_to_thread(email, thread_id)

    def _handle_send(self, input_data: "EmailInput") -> None:
        """Handle sending a new email.

        Args:
            input_data: Email input data.
        """
        message_id = input_data.message_id or str(uuid4())
        thread_id = input_data.thread_id or f"thread-{message_id}"

        email = Email(
            message_id=message_id,
            thread_id=thread_id,
            from_address=input_data.from_address,
            to_addresses=input_data.to_addresses,
            cc_addresses=input_data.cc_addresses or [],
            bcc_addresses=input_data.bcc_addresses or [],
            reply_to_address=input_data.reply_to_address,
            subject=input_data.subject,
            body_text=input_data.body_text,
            body_html=input_data.body_html,
            attachments=input_data.attachments or [],
            in_reply_to=input_data.in_reply_to,
            references=input_data.references or [],
            sent_at=input_data.timestamp,
            received_at=input_data.timestamp,
            priority=input_data.priority,
            folder="sent",
            is_read=True,
        )

        self.emails[message_id] = email
        self.folders["sent"].append(message_id)

        if thread_id not in self.threads:
            self._create_thread(email)
        else:
            self._add_to_thread(email, thread_id)

    def _handle_reply(self, input_data: "EmailInput") -> None:
        """Handle replying to an email.

        Args:
            input_data: Email input data.
        """
        if input_data.in_reply_to not in self.emails:
            raise ValueError(f"Cannot reply to non-existent email: {input_data.in_reply_to}")

        original = self.emails[input_data.in_reply_to]
        thread_id = original.thread_id
        references = self._build_thread_references(input_data.in_reply_to)

        message_id = input_data.message_id or str(uuid4())

        email = Email(
            message_id=message_id,
            thread_id=thread_id,
            from_address=input_data.from_address,
            to_addresses=input_data.to_addresses,
            cc_addresses=input_data.cc_addresses or [],
            bcc_addresses=input_data.bcc_addresses or [],
            reply_to_address=input_data.reply_to_address,
            subject=input_data.subject,
            body_text=input_data.body_text,
            body_html=input_data.body_html,
            attachments=input_data.attachments or [],
            in_reply_to=input_data.in_reply_to,
            references=references,
            sent_at=input_data.timestamp,
            received_at=input_data.timestamp,
            priority=input_data.priority,
            folder="sent",
            is_read=True,
        )

        self.emails[message_id] = email
        self.folders["sent"].append(message_id)
        self._add_to_thread(email, thread_id)

    def _handle_reply_all(self, input_data: "EmailInput") -> None:
        """Handle replying to all recipients of an email.

        Args:
            input_data: Email input data.
        """
        self._handle_reply(input_data)

    def _handle_forward(self, input_data: "EmailInput") -> None:
        """Handle forwarding an email.

        Args:
            input_data: Email input data.
        """
        if input_data.in_reply_to not in self.emails:
            raise ValueError(f"Cannot forward non-existent email: {input_data.in_reply_to}")

        original = self.emails[input_data.in_reply_to]
        message_id = input_data.message_id or str(uuid4())
        thread_id = f"thread-{message_id}"

        email = Email(
            message_id=message_id,
            thread_id=thread_id,
            from_address=input_data.from_address,
            to_addresses=input_data.to_addresses,
            cc_addresses=input_data.cc_addresses or [],
            bcc_addresses=input_data.bcc_addresses or [],
            reply_to_address=input_data.reply_to_address,
            subject=input_data.subject,
            body_text=input_data.body_text,
            body_html=input_data.body_html,
            attachments=original.attachments if not input_data.attachments else input_data.attachments,
            in_reply_to=input_data.in_reply_to,
            references=[input_data.in_reply_to],
            sent_at=input_data.timestamp,
            received_at=input_data.timestamp,
            priority=input_data.priority,
            folder="sent",
            is_read=True,
        )

        self.emails[message_id] = email
        self.folders["sent"].append(message_id)
        self._create_thread(email)

    def _handle_save_draft(self, input_data: "EmailInput") -> None:
        """Handle saving an email as draft.

        Args:
            input_data: Email input data.
        """
        message_id = input_data.message_id or str(uuid4())
        thread_id = input_data.thread_id or f"thread-{message_id}"

        email = Email(
            message_id=message_id,
            thread_id=thread_id,
            from_address=input_data.from_address,
            to_addresses=input_data.to_addresses,
            cc_addresses=input_data.cc_addresses or [],
            bcc_addresses=input_data.bcc_addresses or [],
            reply_to_address=input_data.reply_to_address,
            subject=input_data.subject,
            body_text=input_data.body_text,
            body_html=input_data.body_html,
            attachments=input_data.attachments or [],
            in_reply_to=input_data.in_reply_to,
            references=input_data.references or [],
            sent_at=input_data.timestamp,
            received_at=input_data.timestamp,
            priority=input_data.priority,
            folder="drafts",
            is_read=True,
        )

        self.emails[message_id] = email
        self.drafts[message_id] = email
        self.folders["drafts"].append(message_id)

    def _handle_send_draft(self, input_data: "EmailInput") -> None:
        """Handle sending a previously saved draft.

        Args:
            input_data: Email input data.
        """
        if input_data.message_id not in self.drafts:
            raise ValueError(f"Draft not found: {input_data.message_id}")

        draft = self.drafts[input_data.message_id]
        del self.drafts[input_data.message_id]

        if input_data.message_id in self.folders["drafts"]:
            self.folders["drafts"].remove(input_data.message_id)

        draft.folder = "sent"
        draft.sent_at = input_data.timestamp

        self.folders["sent"].append(input_data.message_id)

    def _handle_mark_read(self, input_data: "EmailInput") -> None:
        """Handle marking email(s) as read.

        Args:
            input_data: Email input data.
        """
        message_ids = self._get_message_ids_from_input(input_data)

        for message_id in message_ids:
            if message_id in self.emails:
                email = self.emails[message_id]
                if not email.is_read:
                    email.mark_read()
                    if email.thread_id in self.threads:
                        self.threads[email.thread_id].update_unread_count(-1)

    def _handle_mark_unread(self, input_data: "EmailInput") -> None:
        """Handle marking email(s) as unread.

        Args:
            input_data: Email input data.
        """
        message_ids = self._get_message_ids_from_input(input_data)

        for message_id in message_ids:
            if message_id in self.emails:
                email = self.emails[message_id]
                if email.is_read:
                    email.mark_unread()
                    if email.thread_id in self.threads:
                        self.threads[email.thread_id].update_unread_count(1)

    def _handle_star(self, input_data: "EmailInput") -> None:
        """Handle starring email(s).

        Args:
            input_data: Email input data.
        """
        message_ids = self._get_message_ids_from_input(input_data)

        for message_id in message_ids:
            if message_id in self.emails:
                self.emails[message_id].is_starred = True

    def _handle_unstar(self, input_data: "EmailInput") -> None:
        """Handle unstarring email(s).

        Args:
            input_data: Email input data.
        """
        message_ids = self._get_message_ids_from_input(input_data)

        for message_id in message_ids:
            if message_id in self.emails:
                self.emails[message_id].is_starred = False

    def _handle_move(self, input_data: "EmailInput") -> None:
        """Handle moving email(s) to a folder.

        Args:
            input_data: Email input data.
        """
        message_ids = self._get_message_ids_from_input(input_data)
        target_folder = input_data.folder

        if target_folder not in self.folders:
            self.folders[target_folder] = []

        for message_id in message_ids:
            if message_id in self.emails:
                email = self.emails[message_id]
                old_folder = email.folder

                if old_folder != target_folder:
                    self._move_email(message_id, old_folder, target_folder)

    def _handle_delete(self, input_data: "EmailInput") -> None:
        """Handle deleting email(s) (move to trash).

        Args:
            input_data: Email input data.
        """
        message_ids = self._get_message_ids_from_input(input_data)

        for message_id in message_ids:
            if message_id in self.emails:
                email = self.emails[message_id]
                old_folder = email.folder
                self._move_email(message_id, old_folder, "trash")

    def _handle_archive(self, input_data: "EmailInput") -> None:
        """Handle archiving email(s).

        Args:
            input_data: Email input data.
        """
        message_ids = self._get_message_ids_from_input(input_data)

        for message_id in message_ids:
            if message_id in self.emails:
                email = self.emails[message_id]
                old_folder = email.folder
                self._move_email(message_id, old_folder, "archive")

    def _handle_add_label(self, input_data: "EmailInput") -> None:
        """Handle adding label(s) to email(s).

        Args:
            input_data: Email input data.
        """
        message_ids = self._get_message_ids_from_input(input_data)
        labels_to_add = input_data.labels or []

        for label in labels_to_add:
            if label not in self.labels:
                self.labels[label] = []

            for message_id in message_ids:
                if message_id in self.emails:
                    self.emails[message_id].add_label(label)
                    if message_id not in self.labels[label]:
                        self.labels[label].append(message_id)

    def _handle_remove_label(self, input_data: "EmailInput") -> None:
        """Handle removing label(s) from email(s).

        Args:
            input_data: Email input data.
        """
        message_ids = self._get_message_ids_from_input(input_data)
        labels_to_remove = input_data.labels or []

        for label in labels_to_remove:
            if label in self.labels:
                for message_id in message_ids:
                    if message_id in self.emails:
                        self.emails[message_id].remove_label(label)
                        if message_id in self.labels[label]:
                            self.labels[label].remove(message_id)

    def _handle_mark_spam(self, input_data: "EmailInput") -> None:
        """Handle marking email(s) as spam.

        Args:
            input_data: Email input data.
        """
        message_ids = self._get_message_ids_from_input(input_data)

        for message_id in message_ids:
            if message_id in self.emails:
                email = self.emails[message_id]
                old_folder = email.folder
                self._move_email(message_id, old_folder, "spam")

    def _handle_mark_not_spam(self, input_data: "EmailInput") -> None:
        """Handle marking email(s) as not spam (move to inbox).

        Args:
            input_data: Email input data.
        """
        message_ids = self._get_message_ids_from_input(input_data)

        for message_id in message_ids:
            if message_id in self.emails:
                email = self.emails[message_id]
                old_folder = email.folder
                self._move_email(message_id, old_folder, "inbox")

    def _get_message_ids_from_input(self, input_data: "EmailInput") -> list[str]:
        """Extract message IDs from input (handles both single and bulk).

        Args:
            input_data: Email input data.

        Returns:
            List of message IDs to operate on.
        """
        if input_data.message_ids:
            return input_data.message_ids
        elif input_data.message_id:
            return [input_data.message_id]
        return []

    def _create_thread(self, email: Email) -> None:
        """Create a new thread from an email.

        Args:
            email: Email to create thread from.
        """
        participants = set([email.from_address] + email.to_addresses + email.cc_addresses)

        thread = EmailThread(
            thread_id=email.thread_id,
            subject=email.subject,
            created_at=email.sent_at,
            participant_addresses=participants,
            message_ids=[email.message_id],
            last_message_at=email.sent_at,
            message_count=1,
            unread_count=0 if email.is_read else 1,
        )

        self.threads[email.thread_id] = thread

    def _add_to_thread(self, email: Email, thread_id: str) -> None:
        """Add an email to an existing thread.

        Args:
            email: Email to add.
            thread_id: Thread to add to.
        """
        if thread_id in self.threads:
            thread = self.threads[thread_id]
            thread.add_message(email.message_id, email.sent_at)

            participants = set([email.from_address] + email.to_addresses + email.cc_addresses)
            thread.participant_addresses.update(participants)

            if not email.is_read:
                thread.update_unread_count(1)

    def _move_email(self, message_id: str, from_folder: str, to_folder: str) -> None:
        """Move an email from one folder to another.

        Args:
            message_id: Email to move.
            from_folder: Source folder.
            to_folder: Destination folder.
        """
        if from_folder in self.folders and message_id in self.folders[from_folder]:
            self.folders[from_folder].remove(message_id)

        if to_folder not in self.folders:
            self.folders[to_folder] = []

        if message_id not in self.folders[to_folder]:
            self.folders[to_folder].append(message_id)

        if message_id in self.emails:
            self.emails[message_id].move_to_folder(to_folder)

    def _get_unread_count(self, folder: str) -> int:
        """Count unread emails in a folder.

        Args:
            folder: Folder to count.

        Returns:
            Number of unread emails.
        """
        if folder not in self.folders:
            return 0

        count = 0
        for message_id in self.folders[folder]:
            if message_id in self.emails and not self.emails[message_id].is_read:
                count += 1

        return count

    def _build_thread_references(self, in_reply_to: str) -> list[str]:
        """Build references list for threading.

        Args:
            in_reply_to: Parent message ID.

        Returns:
            List of message IDs in thread chain.
        """
        if in_reply_to not in self.emails:
            return [in_reply_to]

        parent = self.emails[in_reply_to]
        references = list(parent.references) if parent.references else []

        if in_reply_to not in references:
            references.append(in_reply_to)

        return references

    def get_snapshot(self) -> dict[str, Any]:
        """Return a complete snapshot of current state for API responses.

        Returns:
            Dictionary representation of email state.
        """
        folder_summaries = {}
        for folder_name, message_ids in self.folders.items():
            folder_summaries[folder_name] = {
                "message_count": len(message_ids),
                "unread_count": self._get_unread_count(folder_name),
            }

        return {
            "modality_type": self.modality_type,
            "last_updated": self.last_updated.isoformat(),
            "update_count": self.update_count,
            "user_email_address": self.user_email_address,
            "total_emails": len(self.emails),
            "total_threads": len(self.threads),
            "folders": folder_summaries,
            "label_count": len(self.labels),
            "draft_count": len(self.drafts),
        }

    def get_summary_data(self) -> dict[str, Any]:
        """Return a compact summary of email state without full email contents.

        This method provides statistics and email summaries (without full body
        content) for use with the `summary=true` query parameter.

        Returns:
            Dictionary with email summaries and statistics.
        """
        # Calculate folder statistics
        folder_stats = {}
        for folder_name, message_ids in self.folders.items():
            folder_stats[folder_name] = {
                "message_count": len(message_ids),
                "unread_count": self._get_unread_count(folder_name),
            }

        # Calculate overall statistics
        total_unread = sum(1 for e in self.emails.values() if not e.is_read)
        total_starred = sum(1 for e in self.emails.values() if e.is_starred)

        # Create email summaries (compact representation without full body)
        email_summaries = {
            msg_id: EmailSummary.from_email(email).model_dump()
            for msg_id, email in self.emails.items()
        }

        # Create thread summaries
        thread_summaries = {
            thread_id: thread.model_dump()
            for thread_id, thread in self.threads.items()
        }

        return {
            "modality_type": self.modality_type,
            "last_updated": self.last_updated.isoformat(),
            "update_count": self.update_count,
            "user_email_address": self.user_email_address,
            "statistics": {
                "total_emails": len(self.emails),
                "total_threads": len(self.threads),
                "total_unread": total_unread,
                "total_starred": total_starred,
                "total_drafts": len(self.drafts),
                "total_labels": len(self.labels),
            },
            "folders": folder_stats,
            "labels": {label: len(ids) for label, ids in self.labels.items()},
            "emails": email_summaries,
            "threads": thread_summaries,
        }

    def validate_state(self) -> list[str]:
        """Validate internal state consistency and return any issues.

        Returns:
            List of validation error messages (empty list if valid).
        """
        issues = []

        for folder_name, message_ids in self.folders.items():
            for message_id in message_ids:
                if message_id not in self.emails:
                    issues.append(
                        f"Folder '{folder_name}' references non-existent email: {message_id}"
                    )

        for label_name, message_ids in self.labels.items():
            for message_id in message_ids:
                if message_id not in self.emails:
                    issues.append(
                        f"Label '{label_name}' references non-existent email: {message_id}"
                    )

        for thread_id, thread in self.threads.items():
            for message_id in thread.message_ids:
                if message_id not in self.emails:
                    issues.append(
                        f"Thread '{thread_id}' references non-existent email: {message_id}"
                    )

        for message_id, email in self.emails.items():
            folder_count = sum(
                1 for folder_msgs in self.folders.values() if message_id in folder_msgs
            )
            if folder_count == 0:
                issues.append(f"Email '{message_id}' not in any folder")
            elif folder_count > 1:
                issues.append(f"Email '{message_id}' in multiple folders")

        return issues

    def query(self, query_params: dict[str, Any]) -> dict[str, Any]:
        """Execute a query against email state.

        Args:
            query_params: Dictionary of query parameters.

        Returns:
            Dictionary containing query results.
        """
        results = list(self.emails.values())

        if query_params.get("folder") is not None:
            folder = query_params["folder"]
            if folder in self.folders:
                folder_ids = set(self.folders[folder])
                results = [e for e in results if e.message_id in folder_ids]
            else:
                results = []

        if query_params.get("label") is not None:
            label = query_params["label"]
            if label in self.labels:
                label_ids = set(self.labels[label])
                results = [e for e in results if e.message_id in label_ids]
            else:
                results = []

        # Support for labels (plural) - filters emails that have ALL specified labels
        if query_params.get("labels") is not None:
            labels_to_match = query_params["labels"]
            if labels_to_match:
                # Get message IDs that have all specified labels
                for label in labels_to_match:
                    if label in self.labels:
                        label_ids = set(self.labels[label])
                        results = [e for e in results if e.message_id in label_ids]
                    else:
                        # If any label doesn't exist, no results match
                        results = []
                        break

        if query_params.get("is_read") is not None:
            is_read = query_params["is_read"]
            results = [e for e in results if e.is_read == is_read]

        if query_params.get("is_starred") is not None:
            is_starred = query_params["is_starred"]
            results = [e for e in results if e.is_starred == is_starred]

        if query_params.get("has_attachments") is not None:
            has_attachments = query_params["has_attachments"]
            results = [
                e
                for e in results
                if (len(e.attachments) > 0) == has_attachments
            ]

        if query_params.get("from_address") is not None:
            from_address = query_params["from_address"].lower()
            results = [e for e in results if from_address in e.from_address.lower()]

        if query_params.get("to_address") is not None:
            to_address = query_params["to_address"].lower()
            results = [
                e
                for e in results
                if any(to_address in addr.lower() for addr in e.to_addresses)
            ]

        if query_params.get("subject_contains") is not None:
            subject_text = query_params["subject_contains"].lower()
            results = [e for e in results if subject_text in e.subject.lower()]

        if query_params.get("body_contains") is not None:
            body_text = query_params["body_contains"].lower()
            results = [e for e in results if body_text in e.body_text.lower()]

        # Support both date_from/date_to and received_after/received_before
        if query_params.get("date_from") is not None:
            date_from = query_params["date_from"]
            results = [e for e in results if e.received_at >= date_from]

        if query_params.get("received_after") is not None:
            received_after = query_params["received_after"]
            results = [e for e in results if e.received_at >= received_after]

        if query_params.get("date_to") is not None:
            date_to = query_params["date_to"]
            results = [e for e in results if e.received_at <= date_to]

        if query_params.get("received_before") is not None:
            received_before = query_params["received_before"]
            results = [e for e in results if e.received_at <= received_before]

        if query_params.get("thread_id") is not None:
            thread_id = query_params["thread_id"]
            results = [e for e in results if e.thread_id == thread_id]

        sort_by = query_params.get("sort_by", "date")
        sort_order = query_params.get("sort_order", "desc")

        if sort_by == "date":
            results.sort(key=lambda e: e.received_at, reverse=(sort_order == "desc"))
        elif sort_by == "from":
            results.sort(key=lambda e: e.from_address, reverse=(sort_order == "desc"))
        elif sort_by == "subject":
            results.sort(key=lambda e: e.subject, reverse=(sort_order == "desc"))

        total_count = len(results)

        offset = query_params.get("offset", 0)
        limit = query_params.get("limit")

        if limit is not None:
            results = results[offset : offset + limit]
        elif offset > 0:
            results = results[offset:]

        return {
            "emails": [e.model_dump() for e in results],
            "total_count": total_count,
            "returned_count": len(results),
            "query": query_params,
        }

    def clear(self) -> None:
        """Reset email state to empty defaults.

        Clears all emails, threads, folders, labels, and drafts,
        returning the state to a freshly created condition.
        Standard folders are recreated as empty.
        """
        self.emails.clear()
        self.threads.clear()
        self.drafts.clear()
        self.labels.clear()
        # Recreate standard folders as empty
        self.folders = {
            "inbox": [],
            "sent": [],
            "drafts": [],
            "trash": [],
            "spam": [],
            "archive": [],
        }
        self.update_count = 0

    def create_undo_data(self, input_data: "ModalityInput") -> dict[str, Any]:
        """Capture minimal data needed to undo applying an EmailInput.

        Args:
            input_data: The EmailInput that will be applied.

        Returns:
            Dictionary containing minimal data needed to undo the operation.
        """
        from models.modalities.email_input import EmailInput

        if not isinstance(input_data, EmailInput):
            raise ValueError(
                f"EmailState can only create undo data for EmailInput, got {type(input_data)}"
            )

        # Ensure input is validated (auto-generates message_id for add operations)
        input_data.validate_input()

        # Common state-level metadata
        base_undo = {
            "state_previous_update_count": self.update_count,
            "state_previous_last_updated": self.last_updated.isoformat(),
        }

        operation = input_data.operation

        # Additive operations - create new email
        if operation in ("receive", "send", "reply", "reply_all", "forward"):
            # Generate message_id if not present and SET it on input_data
            # so that apply_input uses the same ID
            if not input_data.message_id:
                input_data.message_id = str(uuid4())
            message_id = input_data.message_id
            
            # For reply/reply_all, thread already exists. For others, new thread created.
            if operation in ("reply", "reply_all"):
                # Thread already exists, capture previous thread state
                if input_data.in_reply_to and input_data.in_reply_to in self.emails:
                    original = self.emails[input_data.in_reply_to]
                    thread_id = original.thread_id
                    if thread_id in self.threads:
                        thread = self.threads[thread_id]
                        return {
                            **base_undo,
                            "action": "remove_email_restore_thread",
                            "message_id": message_id,
                            "thread_id": thread_id,
                            "previous_thread": thread.model_dump(mode="json"),
                        }
                # Fallback if original not found (operation will fail anyway)
                return {**base_undo, "action": "noop"}
            else:
                # New thread will be created - generate and set thread_id too
                if not input_data.thread_id:
                    input_data.thread_id = f"thread-{message_id}"
                thread_id = input_data.thread_id
                return {
                    **base_undo,
                    "action": "remove_email_and_thread",
                    "message_id": message_id,
                    "thread_id": thread_id,
                }

        elif operation == "save_draft":
            # Generate message_id if not present and SET it on input_data
            if not input_data.message_id:
                input_data.message_id = str(uuid4())
            message_id = input_data.message_id
            return {
                **base_undo,
                "action": "remove_draft",
                "message_id": message_id,
            }

        elif operation == "send_draft":
            # Draft moves from drafts folder to sent folder
            if input_data.message_id and input_data.message_id in self.drafts:
                draft = self.drafts[input_data.message_id]
                return {
                    **base_undo,
                    "action": "restore_draft",
                    "message_id": input_data.message_id,
                    "previous_folder": draft.folder,
                    "previous_sent_at": draft.sent_at.isoformat() if draft.sent_at else None,
                }
            return {**base_undo, "action": "noop"}

        elif operation in ("mark_read", "mark_unread"):
            # Capture previous read state for all affected emails
            message_ids = self._get_message_ids_from_input(input_data)
            previous_states: dict[str, dict[str, Any]] = {}
            for msg_id in message_ids:
                if msg_id in self.emails:
                    email = self.emails[msg_id]
                    previous_states[msg_id] = {
                        "was_read": email.is_read,
                        "thread_id": email.thread_id,
                    }
            if not previous_states:
                return {**base_undo, "action": "noop"}
            return {
                **base_undo,
                "action": "restore_read_states",
                "previous_states": previous_states,
            }

        elif operation in ("star", "unstar"):
            # Capture previous starred state for all affected emails
            message_ids = self._get_message_ids_from_input(input_data)
            previous_states: dict[str, bool] = {}
            for msg_id in message_ids:
                if msg_id in self.emails:
                    previous_states[msg_id] = self.emails[msg_id].is_starred
            if not previous_states:
                return {**base_undo, "action": "noop"}
            return {
                **base_undo,
                "action": "restore_starred_states",
                "previous_states": previous_states,
            }

        elif operation in ("move", "delete", "archive", "mark_spam", "mark_not_spam"):
            # Capture previous folder for all affected emails
            message_ids = self._get_message_ids_from_input(input_data)
            previous_folders: dict[str, str] = {}
            for msg_id in message_ids:
                if msg_id in self.emails:
                    previous_folders[msg_id] = self.emails[msg_id].folder
            if not previous_folders:
                return {**base_undo, "action": "noop"}
            return {
                **base_undo,
                "action": "restore_folders",
                "previous_folders": previous_folders,
            }

        elif operation == "add_label":
            # Capture which emails didn't have each label before
            message_ids = self._get_message_ids_from_input(input_data)
            labels_to_add = input_data.labels or []
            # Track previous label state for each email
            previous_label_states: dict[str, list[str]] = {}
            for msg_id in message_ids:
                if msg_id in self.emails:
                    previous_label_states[msg_id] = list(self.emails[msg_id].labels)
            # Track which labels existed before (for cleanup of empty labels)
            existing_labels = [lbl for lbl in labels_to_add if lbl in self.labels]
            if not previous_label_states:
                return {**base_undo, "action": "noop"}
            return {
                **base_undo,
                "action": "restore_labels_after_add",
                "previous_label_states": previous_label_states,
                "labels_added": labels_to_add,
                "labels_existed_before": existing_labels,
            }

        elif operation == "remove_label":
            # Capture which labels each email had before
            message_ids = self._get_message_ids_from_input(input_data)
            labels_to_remove = input_data.labels or []
            previous_label_states: dict[str, list[str]] = {}
            for msg_id in message_ids:
                if msg_id in self.emails:
                    previous_label_states[msg_id] = list(self.emails[msg_id].labels)
            if not previous_label_states:
                return {**base_undo, "action": "noop"}
            return {
                **base_undo,
                "action": "restore_labels_after_remove",
                "previous_label_states": previous_label_states,
                "labels_removed": labels_to_remove,
            }

        # Unknown operation - should not happen
        return {**base_undo, "action": "noop"}

    def apply_undo(self, undo_data: dict[str, Any]) -> None:
        """Apply undo data to reverse a previous email input application.

        Args:
            undo_data: Dictionary returned by create_undo_data().
        """
        action = undo_data.get("action")
        if not action:
            raise ValueError("Undo data missing 'action' field")

        # Handle noop first
        if action == "noop":
            self.update_count = undo_data["state_previous_update_count"]
            self.last_updated = datetime.fromisoformat(
                undo_data["state_previous_last_updated"]
            )
            return

        # Remove email and its thread (for receive, send, forward)
        if action == "remove_email_and_thread":
            message_id = undo_data.get("message_id")
            thread_id = undo_data.get("thread_id")
            if not message_id or not thread_id:
                raise ValueError("Undo data missing 'message_id' or 'thread_id'")

            if message_id in self.emails:
                email = self.emails[message_id]
                # Remove from folder
                if email.folder in self.folders:
                    if message_id in self.folders[email.folder]:
                        self.folders[email.folder].remove(message_id)
                # Remove from labels
                for label in list(email.labels):
                    if label in self.labels and message_id in self.labels[label]:
                        self.labels[label].remove(message_id)
                # Remove email
                del self.emails[message_id]

            # Remove thread if it exists
            if thread_id in self.threads:
                del self.threads[thread_id]

        # Remove email and restore thread to previous state (for reply, reply_all)
        elif action == "remove_email_restore_thread":
            message_id = undo_data.get("message_id")
            thread_id = undo_data.get("thread_id")
            previous_thread = undo_data.get("previous_thread")
            if not message_id or not thread_id or not previous_thread:
                raise ValueError(
                    "Undo data missing 'message_id', 'thread_id', or 'previous_thread'"
                )

            if message_id in self.emails:
                email = self.emails[message_id]
                # Remove from folder
                if email.folder in self.folders:
                    if message_id in self.folders[email.folder]:
                        self.folders[email.folder].remove(message_id)
                # Remove from labels
                for label in list(email.labels):
                    if label in self.labels and message_id in self.labels[label]:
                        self.labels[label].remove(message_id)
                # Remove email
                del self.emails[message_id]

            # Restore thread to previous state
            previous_thread["participant_addresses"] = set(
                previous_thread.get("participant_addresses", [])
            )
            self.threads[thread_id] = EmailThread.model_validate(previous_thread)

        # Remove draft (for save_draft)
        elif action == "remove_draft":
            message_id = undo_data.get("message_id")
            if not message_id:
                raise ValueError("Undo data missing 'message_id'")

            if message_id in self.emails:
                # Remove from drafts folder
                if message_id in self.folders["drafts"]:
                    self.folders["drafts"].remove(message_id)
                # Remove from drafts dict
                if message_id in self.drafts:
                    del self.drafts[message_id]
                # Remove email
                del self.emails[message_id]

        # Restore draft (for send_draft)
        elif action == "restore_draft":
            message_id = undo_data.get("message_id")
            previous_folder = undo_data.get("previous_folder")
            previous_sent_at = undo_data.get("previous_sent_at")
            if not message_id:
                raise ValueError("Undo data missing 'message_id'")

            if message_id in self.emails:
                email = self.emails[message_id]
                # Move back to drafts folder
                if email.folder in self.folders:
                    if message_id in self.folders[email.folder]:
                        self.folders[email.folder].remove(message_id)
                email.folder = previous_folder or "drafts"
                if email.folder not in self.folders:
                    self.folders[email.folder] = []
                self.folders[email.folder].append(message_id)
                # Restore sent_at
                if previous_sent_at:
                    email.sent_at = datetime.fromisoformat(previous_sent_at)
                # Re-add to drafts dict
                self.drafts[message_id] = email

        # Restore read states (for mark_read, mark_unread)
        elif action == "restore_read_states":
            previous_states = undo_data.get("previous_states", {})
            for msg_id, state_info in previous_states.items():
                if msg_id in self.emails:
                    email = self.emails[msg_id]
                    old_is_read = email.is_read
                    new_is_read = state_info["was_read"]
                    email.is_read = new_is_read
                    # Update thread unread count
                    thread_id = state_info.get("thread_id")
                    if thread_id and thread_id in self.threads:
                        if old_is_read and not new_is_read:
                            # Was read, now unread - increment
                            self.threads[thread_id].update_unread_count(1)
                        elif not old_is_read and new_is_read:
                            # Was unread, now read - decrement
                            self.threads[thread_id].update_unread_count(-1)

        # Restore starred states (for star, unstar)
        elif action == "restore_starred_states":
            previous_states = undo_data.get("previous_states", {})
            for msg_id, was_starred in previous_states.items():
                if msg_id in self.emails:
                    self.emails[msg_id].is_starred = was_starred

        # Restore folders (for move, delete, archive, mark_spam, mark_not_spam)
        elif action == "restore_folders":
            previous_folders = undo_data.get("previous_folders", {})
            for msg_id, old_folder in previous_folders.items():
                if msg_id in self.emails:
                    email = self.emails[msg_id]
                    current_folder = email.folder
                    if current_folder != old_folder:
                        self._move_email(msg_id, current_folder, old_folder)

        # Restore labels after add_label
        elif action == "restore_labels_after_add":
            previous_label_states = undo_data.get("previous_label_states", {})
            labels_added = undo_data.get("labels_added", [])
            labels_existed_before = undo_data.get("labels_existed_before", [])

            # Restore each email's labels to previous state
            for msg_id, old_labels in previous_label_states.items():
                if msg_id in self.emails:
                    email = self.emails[msg_id]
                    # Remove labels that were added
                    for label in labels_added:
                        if label not in old_labels and label in email.labels:
                            email.remove_label(label)
                            if label in self.labels and msg_id in self.labels[label]:
                                self.labels[label].remove(msg_id)

            # Remove labels that didn't exist before (were created by add_label)
            for label in labels_added:
                if label not in labels_existed_before:
                    # Label was created by this operation, remove if now empty
                    if label in self.labels and len(self.labels[label]) == 0:
                        del self.labels[label]

        # Restore labels after remove_label
        elif action == "restore_labels_after_remove":
            previous_label_states = undo_data.get("previous_label_states", {})
            labels_removed = undo_data.get("labels_removed", [])

            # Restore each email's labels to previous state
            for msg_id, old_labels in previous_label_states.items():
                if msg_id in self.emails:
                    email = self.emails[msg_id]
                    # Re-add labels that were removed
                    for label in labels_removed:
                        if label in old_labels and label not in email.labels:
                            email.add_label(label)
                            if label not in self.labels:
                                self.labels[label] = []
                            if msg_id not in self.labels[label]:
                                self.labels[label].append(msg_id)

        else:
            raise ValueError(f"Unknown undo action: {action}")

        # Restore state-level metadata
        self.update_count = undo_data["state_previous_update_count"]
        self.last_updated = datetime.fromisoformat(
            undo_data["state_previous_last_updated"]
        )
