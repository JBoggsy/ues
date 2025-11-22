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

        if "folder" in query_params:
            folder = query_params["folder"]
            if folder in self.folders:
                folder_ids = set(self.folders[folder])
                results = [e for e in results if e.message_id in folder_ids]
            else:
                results = []

        if "label" in query_params:
            label = query_params["label"]
            if label in self.labels:
                label_ids = set(self.labels[label])
                results = [e for e in results if e.message_id in label_ids]
            else:
                results = []

        if "is_read" in query_params:
            is_read = query_params["is_read"]
            results = [e for e in results if e.is_read == is_read]

        if "is_starred" in query_params:
            is_starred = query_params["is_starred"]
            results = [e for e in results if e.is_starred == is_starred]

        if "has_attachments" in query_params:
            has_attachments = query_params["has_attachments"]
            results = [
                e
                for e in results
                if (len(e.attachments) > 0) == has_attachments
            ]

        if "from_address" in query_params:
            from_address = query_params["from_address"].lower()
            results = [e for e in results if from_address in e.from_address.lower()]

        if "to_address" in query_params:
            to_address = query_params["to_address"].lower()
            results = [
                e
                for e in results
                if any(to_address in addr.lower() for addr in e.to_addresses)
            ]

        if "subject_contains" in query_params:
            subject_text = query_params["subject_contains"].lower()
            results = [e for e in results if subject_text in e.subject.lower()]

        if "body_contains" in query_params:
            body_text = query_params["body_contains"].lower()
            results = [e for e in results if body_text in e.body_text.lower()]

        if "date_from" in query_params:
            date_from = query_params["date_from"]
            results = [e for e in results if e.received_at >= date_from]

        if "date_to" in query_params:
            date_to = query_params["date_to"]
            results = [e for e in results if e.received_at <= date_to]

        if "thread_id" in query_params:
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
