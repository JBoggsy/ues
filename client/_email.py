"""Email modality sub-client for the UES API.

This module provides EmailClient and AsyncEmailClient for interacting with
the email modality endpoints (/email/*).

This is an internal module. Import from `client` instead.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field

from client._base import AsyncBaseClient, BaseClient
from client.models import ModalityActionResponse

if TYPE_CHECKING:
    from client._http import AsyncHTTPClient, HTTPClient


# Response models for email endpoints


class EmailAttachment(BaseModel):
    """Represents an email attachment.
    
    Attributes:
        filename: Name of the attached file.
        size: File size in bytes.
        mime_type: MIME type of the attachment.
        content_id: Optional content ID for inline images.
    """

    filename: str
    size: int
    mime_type: str
    content_id: str | None = None


class Email(BaseModel):
    """Represents a complete email message with all metadata.
    
    Attributes:
        message_id: Unique message identifier.
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

    message_id: str
    thread_id: str
    from_address: str
    to_addresses: list[str]
    cc_addresses: list[str] = Field(default_factory=list)
    bcc_addresses: list[str] = Field(default_factory=list)
    reply_to_address: str | None = None
    subject: str
    body_text: str
    body_html: str | None = None
    attachments: list[EmailAttachment] = Field(default_factory=list)
    in_reply_to: str | None = None
    references: list[str] = Field(default_factory=list)
    sent_at: datetime
    received_at: datetime
    is_read: bool = False
    is_starred: bool = False
    priority: str = "normal"
    folder: str = "inbox"
    labels: list[str] = Field(default_factory=list)


class EmailThread(BaseModel):
    """Represents a conversation thread grouping related emails.
    
    Attributes:
        thread_id: Unique thread identifier.
        subject: Thread subject (from first email).
        participant_addresses: All email addresses involved.
        message_ids: Ordered list of message IDs in thread.
        created_at: When thread started.
        last_message_at: When last email was added.
        message_count: Number of emails in thread.
        unread_count: Number of unread emails in thread.
    """

    thread_id: str
    subject: str
    participant_addresses: list[str] = Field(default_factory=list)
    message_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    last_message_at: datetime
    message_count: int = 0
    unread_count: int = 0


class EmailSummary(BaseModel):
    """Summary representation of an email for compact API responses.
    
    Contains only essential metadata without full body content.
    
    Attributes:
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

    message_id: str
    thread_id: str
    from_address: str
    to_addresses: list[str]
    subject: str
    sent_at: datetime
    received_at: datetime
    is_read: bool
    is_starred: bool
    folder: str
    has_attachments: bool
    attachment_count: int
    body_preview: str


class EmailStateResponse(BaseModel):
    """Response model for full email state endpoint.
    
    Attributes:
        modality_type: Always "email".
        current_time: Current simulator time.
        user_email_address: The simulated user's email address.
        emails: All emails indexed by message_id.
        threads: All threads indexed by thread_id.
        folders: Folder names and their message counts.
        labels: Label names and their message counts.
        total_email_count: Total number of emails.
        unread_count: Total number of unread emails.
        starred_count: Total number of starred emails.
    """

    modality_type: str = "email"
    current_time: datetime
    user_email_address: str
    emails: dict[str, Email]
    threads: dict[str, EmailThread]
    folders: dict[str, int]
    labels: dict[str, int]
    total_email_count: int
    unread_count: int
    starred_count: int


class EmailSummaryStateResponse(BaseModel):
    """Response model for email state endpoint with summary=true.
    
    Returns compact email summaries (without full body content) and statistics.
    
    Attributes:
        modality_type: Always "email".
        current_time: Current simulator time.
        user_email_address: The simulated user's email address.
        statistics: Overall email statistics.
        folders: Folder names with message and unread counts.
        labels: Label names with message counts.
        emails: Email summaries (without full body content).
        threads: Thread information.
    """

    modality_type: str = "email"
    current_time: datetime
    user_email_address: str
    statistics: dict[str, Any]
    folders: dict[str, dict[str, Any]]
    labels: dict[str, int]
    emails: dict[str, EmailSummary]
    threads: dict[str, EmailThread]


class EmailQueryResponse(BaseModel):
    """Response model for email query endpoint.
    
    Attributes:
        modality_type: Always "email".
        emails: Query results (matching emails).
        total_count: Total number of results matching query.
        returned_count: Number of results returned (after pagination).
        query: Echo of query parameters for debugging.
    """

    modality_type: str = "email"
    emails: list[Email]
    total_count: int
    returned_count: int
    query: dict[str, Any]


# Synchronous EmailClient


class EmailClient(BaseClient):
    """Synchronous client for email modality endpoints (/email/*).
    
    This client provides methods for sending, receiving, organizing, and 
    querying email messages. Supports full email lifecycle from composition 
    to archival/deletion.
    
    Example:
        with UESClient() as client:
            # Send an email
            client.email.send(
                from_address="me@example.com",
                to_addresses=["user@example.com"],
                subject="Hello",
                body_text="This is a test email.",
            )
            
            # Get email state
            state = client.email.get_state()
            print(f"Total emails: {state.total_email_count}")
            
            # Query unread emails
            unread = client.email.query(is_read=False)
            print(f"Found {unread.total_count} unread emails")
    """

    _BASE_PATH = "/email"

    def get_state(
        self,
        summary: bool = False,
    ) -> EmailStateResponse | EmailSummaryStateResponse:
        """Get the current email state.
        
        Returns a complete snapshot of the email system including all messages,
        threads, folders, and labels.
        
        Args:
            summary: If True, return compact summaries without full email body
                content. Useful for getting an overview without large payloads.
        
        Returns:
            Complete email state with all messages, or summary if summary=True.
        
        Raises:
            APIError: If the request fails.
        """
        params = {"summary": summary} if summary else None
        data = self._get(f"{self._BASE_PATH}/state", params=params)
        
        if summary:
            return EmailSummaryStateResponse(**data)
        return EmailStateResponse(**data)

    def query(
        self,
        folder: str | None = None,
        is_read: bool | None = None,
        is_starred: bool | None = None,
        from_address: str | None = None,
        to_address: str | None = None,
        subject_contains: str | None = None,
        body_contains: str | None = None,
        has_attachments: bool | None = None,
        labels: list[str] | None = None,
        thread_id: str | None = None,
        priority: Literal["high", "normal", "low"] | None = None,
        sent_after: datetime | None = None,
        sent_before: datetime | None = None,
        received_after: datetime | None = None,
        received_before: datetime | None = None,
        limit: int | None = None,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> EmailQueryResponse:
        """Query emails with filters.
        
        Allows filtering and searching through email data with various criteria
        including folder, read status, sender, subject, date ranges, etc.
        
        Args:
            folder: Filter by folder name.
            is_read: Filter by read status.
            is_starred: Filter by starred status.
            from_address: Filter by sender address.
            to_address: Filter by recipient address (in to/cc/bcc).
            subject_contains: Filter by subject text (case-insensitive).
            body_contains: Filter by body text (case-insensitive).
            has_attachments: Filter by attachment presence.
            labels: Filter by labels (messages must have ALL specified labels).
            thread_id: Filter by thread ID.
            priority: Filter by priority level.
            sent_after: Filter by sent date (inclusive).
            sent_before: Filter by sent date (inclusive).
            received_after: Filter by received date (inclusive).
            received_before: Filter by received date (inclusive).
            limit: Maximum number of results to return.
            offset: Number of results to skip (for pagination).
            sort_by: Field to sort by (e.g., 'sent_at', 'received_at', 'subject').
            sort_order: Sort direction ("asc" or "desc").
        
        Returns:
            Filtered email results with counts.
        
        Raises:
            ValidationError: If query parameters are invalid.
            APIError: If the request fails.
        """
        # Build the request body, excluding None values
        request_data: dict[str, Any] = {}
        
        if folder is not None:
            request_data["folder"] = folder
        if is_read is not None:
            request_data["is_read"] = is_read
        if is_starred is not None:
            request_data["is_starred"] = is_starred
        if from_address is not None:
            request_data["from_address"] = from_address
        if to_address is not None:
            request_data["to_address"] = to_address
        if subject_contains is not None:
            request_data["subject_contains"] = subject_contains
        if body_contains is not None:
            request_data["body_contains"] = body_contains
        if has_attachments is not None:
            request_data["has_attachments"] = has_attachments
        if labels is not None:
            request_data["labels"] = labels
        if thread_id is not None:
            request_data["thread_id"] = thread_id
        if priority is not None:
            request_data["priority"] = priority
        if sent_after is not None:
            request_data["sent_after"] = sent_after.isoformat()
        if sent_before is not None:
            request_data["sent_before"] = sent_before.isoformat()
        if received_after is not None:
            request_data["received_after"] = received_after.isoformat()
        if received_before is not None:
            request_data["received_before"] = received_before.isoformat()
        if limit is not None:
            request_data["limit"] = limit
        if offset != 0:
            request_data["offset"] = offset
        if sort_by is not None:
            request_data["sort_by"] = sort_by
        if sort_order != "desc":
            request_data["sort_order"] = sort_order
        
        data = self._post(f"{self._BASE_PATH}/query", json=request_data)
        return EmailQueryResponse(**data)

    def send(
        self,
        from_address: str,
        to_addresses: list[str],
        subject: str,
        body_text: str,
        cc_addresses: list[str] | None = None,
        bcc_addresses: list[str] | None = None,
        reply_to_address: str | None = None,
        body_html: str | None = None,
        attachments: list[dict[str, Any]] | None = None,
        priority: Literal["high", "normal", "low"] = "normal",
    ) -> ModalityActionResponse:
        """Send a new email.
        
        Creates an immediate event to send an email from the user to specified
        recipients with subject, body, and optional attachments.
        
        Args:
            from_address: Sender email address.
            to_addresses: Primary recipient addresses.
            subject: Email subject line.
            body_text: Plain text body content.
            cc_addresses: CC recipient addresses.
            bcc_addresses: BCC recipient addresses.
            reply_to_address: Reply-to address if different from sender.
            body_html: HTML body content.
            attachments: File attachments. Each attachment should be a dict with
                'filename', 'size', 'mime_type', and optional 'content_id' keys.
            priority: Priority level ("high", "normal", "low").
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If request parameters are invalid.
            APIError: If the request fails.
        """
        request_data: dict[str, Any] = {
            "from_address": from_address,
            "to_addresses": to_addresses,
            "subject": subject,
            "body_text": body_text,
            "priority": priority,
        }
        
        if cc_addresses is not None:
            request_data["cc_addresses"] = cc_addresses
        if bcc_addresses is not None:
            request_data["bcc_addresses"] = bcc_addresses
        if reply_to_address is not None:
            request_data["reply_to_address"] = reply_to_address
        if body_html is not None:
            request_data["body_html"] = body_html
        if attachments is not None:
            request_data["attachments"] = attachments
        
        data = self._post(f"{self._BASE_PATH}/send", json=request_data)
        return ModalityActionResponse(**data)

    def receive(
        self,
        from_address: str,
        to_addresses: list[str],
        subject: str,
        body_text: str,
        cc_addresses: list[str] | None = None,
        bcc_addresses: list[str] | None = None,
        reply_to_address: str | None = None,
        body_html: str | None = None,
        attachments: list[dict[str, Any]] | None = None,
        priority: Literal["high", "normal", "low"] = "normal",
        thread_id: str | None = None,
        in_reply_to: str | None = None,
        references: list[str] | None = None,
        sent_at: datetime | None = None,
    ) -> ModalityActionResponse:
        """Simulate receiving an email.
        
        Creates an immediate event to receive an email from an external sender
        into the user's inbox.
        
        Args:
            from_address: Sender email address.
            to_addresses: Primary recipient addresses.
            subject: Email subject line.
            body_text: Plain text body content.
            cc_addresses: CC recipient addresses.
            bcc_addresses: BCC recipient addresses.
            reply_to_address: Reply-to address if different from sender.
            body_html: HTML body content.
            attachments: File attachments. Each attachment should be a dict with
                'filename', 'size', 'mime_type', and optional 'content_id' keys.
            priority: Priority level ("high", "normal", "low").
            thread_id: Thread identifier for conversation grouping.
            in_reply_to: Message ID this email replies to.
            references: List of message IDs in thread chain.
            sent_at: When email was originally sent (defaults to current time).
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If request parameters are invalid.
            APIError: If the request fails.
        """
        request_data: dict[str, Any] = {
            "from_address": from_address,
            "to_addresses": to_addresses,
            "subject": subject,
            "body_text": body_text,
            "priority": priority,
        }
        
        if cc_addresses is not None:
            request_data["cc_addresses"] = cc_addresses
        if bcc_addresses is not None:
            request_data["bcc_addresses"] = bcc_addresses
        if reply_to_address is not None:
            request_data["reply_to_address"] = reply_to_address
        if body_html is not None:
            request_data["body_html"] = body_html
        if attachments is not None:
            request_data["attachments"] = attachments
        if thread_id is not None:
            request_data["thread_id"] = thread_id
        if in_reply_to is not None:
            request_data["in_reply_to"] = in_reply_to
        if references is not None:
            request_data["references"] = references
        if sent_at is not None:
            request_data["sent_at"] = sent_at.isoformat()
        
        data = self._post(f"{self._BASE_PATH}/receive", json=request_data)
        return ModalityActionResponse(**data)

    def read(self, message_ids: list[str]) -> ModalityActionResponse:
        """Mark emails as read.
        
        Creates an immediate event to mark one or more emails as read.
        
        Args:
            message_ids: Message IDs to mark as read.
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If message_ids is empty.
            APIError: If the request fails.
        """
        data = self._post(
            f"{self._BASE_PATH}/read",
            json={"message_ids": message_ids},
        )
        return ModalityActionResponse(**data)

    def unread(self, message_ids: list[str]) -> ModalityActionResponse:
        """Mark emails as unread.
        
        Creates an immediate event to mark one or more emails as unread.
        
        Args:
            message_ids: Message IDs to mark as unread.
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If message_ids is empty.
            APIError: If the request fails.
        """
        data = self._post(
            f"{self._BASE_PATH}/unread",
            json={"message_ids": message_ids},
        )
        return ModalityActionResponse(**data)

    def star(self, message_ids: list[str]) -> ModalityActionResponse:
        """Star/favorite emails.
        
        Creates an immediate event to star one or more emails.
        
        Args:
            message_ids: Message IDs to star.
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If message_ids is empty.
            APIError: If the request fails.
        """
        data = self._post(
            f"{self._BASE_PATH}/star",
            json={"message_ids": message_ids},
        )
        return ModalityActionResponse(**data)

    def unstar(self, message_ids: list[str]) -> ModalityActionResponse:
        """Unstar emails.
        
        Creates an immediate event to unstar one or more emails.
        
        Args:
            message_ids: Message IDs to unstar.
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If message_ids is empty.
            APIError: If the request fails.
        """
        data = self._post(
            f"{self._BASE_PATH}/unstar",
            json={"message_ids": message_ids},
        )
        return ModalityActionResponse(**data)

    def archive(self, message_ids: list[str]) -> ModalityActionResponse:
        """Archive emails.
        
        Creates an immediate event to move one or more emails to the archive folder.
        
        Args:
            message_ids: Message IDs to archive.
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If message_ids is empty.
            APIError: If the request fails.
        """
        data = self._post(
            f"{self._BASE_PATH}/archive",
            json={"message_ids": message_ids},
        )
        return ModalityActionResponse(**data)

    def delete(self, message_ids: list[str]) -> ModalityActionResponse:
        """Delete emails.
        
        Creates an immediate event to move one or more emails to the trash folder.
        
        Args:
            message_ids: Message IDs to delete.
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If message_ids is empty.
            APIError: If the request fails.
        """
        data = self._post(
            f"{self._BASE_PATH}/delete",
            json={"message_ids": message_ids},
        )
        return ModalityActionResponse(**data)

    def label(
        self,
        message_ids: list[str],
        labels: list[str],
    ) -> ModalityActionResponse:
        """Add labels to emails.
        
        Creates an immediate event to add one or more labels to specified emails.
        
        Args:
            message_ids: Message IDs to label.
            labels: Labels to add.
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If message_ids or labels is empty.
            APIError: If the request fails.
        """
        data = self._post(
            f"{self._BASE_PATH}/label",
            json={"message_ids": message_ids, "labels": labels},
        )
        return ModalityActionResponse(**data)

    def unlabel(
        self,
        message_ids: list[str],
        labels: list[str],
    ) -> ModalityActionResponse:
        """Remove labels from emails.
        
        Creates an immediate event to remove one or more labels from specified emails.
        
        Args:
            message_ids: Message IDs to unlabel.
            labels: Labels to remove.
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If message_ids or labels is empty.
            APIError: If the request fails.
        """
        data = self._post(
            f"{self._BASE_PATH}/unlabel",
            json={"message_ids": message_ids, "labels": labels},
        )
        return ModalityActionResponse(**data)

    def move(
        self,
        message_ids: list[str],
        folder: str,
    ) -> ModalityActionResponse:
        """Move emails to a different folder.
        
        Creates an immediate event to move one or more emails to the specified folder.
        
        Args:
            message_ids: Message IDs to move.
            folder: Target folder name.
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If message_ids is empty or folder is invalid.
            APIError: If the request fails.
        """
        data = self._post(
            f"{self._BASE_PATH}/move",
            json={"message_ids": message_ids, "folder": folder},
        )
        return ModalityActionResponse(**data)


# Asynchronous AsyncEmailClient


class AsyncEmailClient(AsyncBaseClient):
    """Asynchronous client for email modality endpoints (/email/*).
    
    This client provides async methods for sending, receiving, organizing, and 
    querying email messages. Supports full email lifecycle from composition 
    to archival/deletion.
    
    Example:
        async with AsyncUESClient() as client:
            # Send an email
            await client.email.send(
                from_address="me@example.com",
                to_addresses=["user@example.com"],
                subject="Hello",
                body_text="This is a test email.",
            )
            
            # Get email state
            state = await client.email.get_state()
            print(f"Total emails: {state.total_email_count}")
            
            # Query unread emails
            unread = await client.email.query(is_read=False)
            print(f"Found {unread.total_count} unread emails")
    """

    _BASE_PATH = "/email"

    async def get_state(
        self,
        summary: bool = False,
    ) -> EmailStateResponse | EmailSummaryStateResponse:
        """Get the current email state.
        
        Returns a complete snapshot of the email system including all messages,
        threads, folders, and labels.
        
        Args:
            summary: If True, return compact summaries without full email body
                content. Useful for getting an overview without large payloads.
        
        Returns:
            Complete email state with all messages, or summary if summary=True.
        
        Raises:
            APIError: If the request fails.
        """
        params = {"summary": summary} if summary else None
        data = await self._get(f"{self._BASE_PATH}/state", params=params)
        
        if summary:
            return EmailSummaryStateResponse(**data)
        return EmailStateResponse(**data)

    async def query(
        self,
        folder: str | None = None,
        is_read: bool | None = None,
        is_starred: bool | None = None,
        from_address: str | None = None,
        to_address: str | None = None,
        subject_contains: str | None = None,
        body_contains: str | None = None,
        has_attachments: bool | None = None,
        labels: list[str] | None = None,
        thread_id: str | None = None,
        priority: Literal["high", "normal", "low"] | None = None,
        sent_after: datetime | None = None,
        sent_before: datetime | None = None,
        received_after: datetime | None = None,
        received_before: datetime | None = None,
        limit: int | None = None,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> EmailQueryResponse:
        """Query emails with filters.
        
        Allows filtering and searching through email data with various criteria
        including folder, read status, sender, subject, date ranges, etc.
        
        Args:
            folder: Filter by folder name.
            is_read: Filter by read status.
            is_starred: Filter by starred status.
            from_address: Filter by sender address.
            to_address: Filter by recipient address (in to/cc/bcc).
            subject_contains: Filter by subject text (case-insensitive).
            body_contains: Filter by body text (case-insensitive).
            has_attachments: Filter by attachment presence.
            labels: Filter by labels (messages must have ALL specified labels).
            thread_id: Filter by thread ID.
            priority: Filter by priority level.
            sent_after: Filter by sent date (inclusive).
            sent_before: Filter by sent date (inclusive).
            received_after: Filter by received date (inclusive).
            received_before: Filter by received date (inclusive).
            limit: Maximum number of results to return.
            offset: Number of results to skip (for pagination).
            sort_by: Field to sort by (e.g., 'sent_at', 'received_at', 'subject').
            sort_order: Sort direction ("asc" or "desc").
        
        Returns:
            Filtered email results with counts.
        
        Raises:
            ValidationError: If query parameters are invalid.
            APIError: If the request fails.
        """
        # Build the request body, excluding None values
        request_data: dict[str, Any] = {}
        
        if folder is not None:
            request_data["folder"] = folder
        if is_read is not None:
            request_data["is_read"] = is_read
        if is_starred is not None:
            request_data["is_starred"] = is_starred
        if from_address is not None:
            request_data["from_address"] = from_address
        if to_address is not None:
            request_data["to_address"] = to_address
        if subject_contains is not None:
            request_data["subject_contains"] = subject_contains
        if body_contains is not None:
            request_data["body_contains"] = body_contains
        if has_attachments is not None:
            request_data["has_attachments"] = has_attachments
        if labels is not None:
            request_data["labels"] = labels
        if thread_id is not None:
            request_data["thread_id"] = thread_id
        if priority is not None:
            request_data["priority"] = priority
        if sent_after is not None:
            request_data["sent_after"] = sent_after.isoformat()
        if sent_before is not None:
            request_data["sent_before"] = sent_before.isoformat()
        if received_after is not None:
            request_data["received_after"] = received_after.isoformat()
        if received_before is not None:
            request_data["received_before"] = received_before.isoformat()
        if limit is not None:
            request_data["limit"] = limit
        if offset != 0:
            request_data["offset"] = offset
        if sort_by is not None:
            request_data["sort_by"] = sort_by
        if sort_order != "desc":
            request_data["sort_order"] = sort_order
        
        data = await self._post(f"{self._BASE_PATH}/query", json=request_data)
        return EmailQueryResponse(**data)

    async def send(
        self,
        from_address: str,
        to_addresses: list[str],
        subject: str,
        body_text: str,
        cc_addresses: list[str] | None = None,
        bcc_addresses: list[str] | None = None,
        reply_to_address: str | None = None,
        body_html: str | None = None,
        attachments: list[dict[str, Any]] | None = None,
        priority: Literal["high", "normal", "low"] = "normal",
    ) -> ModalityActionResponse:
        """Send a new email.
        
        Creates an immediate event to send an email from the user to specified
        recipients with subject, body, and optional attachments.
        
        Args:
            from_address: Sender email address.
            to_addresses: Primary recipient addresses.
            subject: Email subject line.
            body_text: Plain text body content.
            cc_addresses: CC recipient addresses.
            bcc_addresses: BCC recipient addresses.
            reply_to_address: Reply-to address if different from sender.
            body_html: HTML body content.
            attachments: File attachments. Each attachment should be a dict with
                'filename', 'size', 'mime_type', and optional 'content_id' keys.
            priority: Priority level ("high", "normal", "low").
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If request parameters are invalid.
            APIError: If the request fails.
        """
        request_data: dict[str, Any] = {
            "from_address": from_address,
            "to_addresses": to_addresses,
            "subject": subject,
            "body_text": body_text,
            "priority": priority,
        }
        
        if cc_addresses is not None:
            request_data["cc_addresses"] = cc_addresses
        if bcc_addresses is not None:
            request_data["bcc_addresses"] = bcc_addresses
        if reply_to_address is not None:
            request_data["reply_to_address"] = reply_to_address
        if body_html is not None:
            request_data["body_html"] = body_html
        if attachments is not None:
            request_data["attachments"] = attachments
        
        data = await self._post(f"{self._BASE_PATH}/send", json=request_data)
        return ModalityActionResponse(**data)

    async def receive(
        self,
        from_address: str,
        to_addresses: list[str],
        subject: str,
        body_text: str,
        cc_addresses: list[str] | None = None,
        bcc_addresses: list[str] | None = None,
        reply_to_address: str | None = None,
        body_html: str | None = None,
        attachments: list[dict[str, Any]] | None = None,
        priority: Literal["high", "normal", "low"] = "normal",
        thread_id: str | None = None,
        in_reply_to: str | None = None,
        references: list[str] | None = None,
        sent_at: datetime | None = None,
    ) -> ModalityActionResponse:
        """Simulate receiving an email.
        
        Creates an immediate event to receive an email from an external sender
        into the user's inbox.
        
        Args:
            from_address: Sender email address.
            to_addresses: Primary recipient addresses.
            subject: Email subject line.
            body_text: Plain text body content.
            cc_addresses: CC recipient addresses.
            bcc_addresses: BCC recipient addresses.
            reply_to_address: Reply-to address if different from sender.
            body_html: HTML body content.
            attachments: File attachments. Each attachment should be a dict with
                'filename', 'size', 'mime_type', and optional 'content_id' keys.
            priority: Priority level ("high", "normal", "low").
            thread_id: Thread identifier for conversation grouping.
            in_reply_to: Message ID this email replies to.
            references: List of message IDs in thread chain.
            sent_at: When email was originally sent (defaults to current time).
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If request parameters are invalid.
            APIError: If the request fails.
        """
        request_data: dict[str, Any] = {
            "from_address": from_address,
            "to_addresses": to_addresses,
            "subject": subject,
            "body_text": body_text,
            "priority": priority,
        }
        
        if cc_addresses is not None:
            request_data["cc_addresses"] = cc_addresses
        if bcc_addresses is not None:
            request_data["bcc_addresses"] = bcc_addresses
        if reply_to_address is not None:
            request_data["reply_to_address"] = reply_to_address
        if body_html is not None:
            request_data["body_html"] = body_html
        if attachments is not None:
            request_data["attachments"] = attachments
        if thread_id is not None:
            request_data["thread_id"] = thread_id
        if in_reply_to is not None:
            request_data["in_reply_to"] = in_reply_to
        if references is not None:
            request_data["references"] = references
        if sent_at is not None:
            request_data["sent_at"] = sent_at.isoformat()
        
        data = await self._post(f"{self._BASE_PATH}/receive", json=request_data)
        return ModalityActionResponse(**data)

    async def read(self, message_ids: list[str]) -> ModalityActionResponse:
        """Mark emails as read.
        
        Creates an immediate event to mark one or more emails as read.
        
        Args:
            message_ids: Message IDs to mark as read.
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If message_ids is empty.
            APIError: If the request fails.
        """
        data = await self._post(
            f"{self._BASE_PATH}/read",
            json={"message_ids": message_ids},
        )
        return ModalityActionResponse(**data)

    async def unread(self, message_ids: list[str]) -> ModalityActionResponse:
        """Mark emails as unread.
        
        Creates an immediate event to mark one or more emails as unread.
        
        Args:
            message_ids: Message IDs to mark as unread.
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If message_ids is empty.
            APIError: If the request fails.
        """
        data = await self._post(
            f"{self._BASE_PATH}/unread",
            json={"message_ids": message_ids},
        )
        return ModalityActionResponse(**data)

    async def star(self, message_ids: list[str]) -> ModalityActionResponse:
        """Star/favorite emails.
        
        Creates an immediate event to star one or more emails.
        
        Args:
            message_ids: Message IDs to star.
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If message_ids is empty.
            APIError: If the request fails.
        """
        data = await self._post(
            f"{self._BASE_PATH}/star",
            json={"message_ids": message_ids},
        )
        return ModalityActionResponse(**data)

    async def unstar(self, message_ids: list[str]) -> ModalityActionResponse:
        """Unstar emails.
        
        Creates an immediate event to unstar one or more emails.
        
        Args:
            message_ids: Message IDs to unstar.
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If message_ids is empty.
            APIError: If the request fails.
        """
        data = await self._post(
            f"{self._BASE_PATH}/unstar",
            json={"message_ids": message_ids},
        )
        return ModalityActionResponse(**data)

    async def archive(self, message_ids: list[str]) -> ModalityActionResponse:
        """Archive emails.
        
        Creates an immediate event to move one or more emails to the archive folder.
        
        Args:
            message_ids: Message IDs to archive.
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If message_ids is empty.
            APIError: If the request fails.
        """
        data = await self._post(
            f"{self._BASE_PATH}/archive",
            json={"message_ids": message_ids},
        )
        return ModalityActionResponse(**data)

    async def delete(self, message_ids: list[str]) -> ModalityActionResponse:
        """Delete emails.
        
        Creates an immediate event to move one or more emails to the trash folder.
        
        Args:
            message_ids: Message IDs to delete.
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If message_ids is empty.
            APIError: If the request fails.
        """
        data = await self._post(
            f"{self._BASE_PATH}/delete",
            json={"message_ids": message_ids},
        )
        return ModalityActionResponse(**data)

    async def label(
        self,
        message_ids: list[str],
        labels: list[str],
    ) -> ModalityActionResponse:
        """Add labels to emails.
        
        Creates an immediate event to add one or more labels to specified emails.
        
        Args:
            message_ids: Message IDs to label.
            labels: Labels to add.
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If message_ids or labels is empty.
            APIError: If the request fails.
        """
        data = await self._post(
            f"{self._BASE_PATH}/label",
            json={"message_ids": message_ids, "labels": labels},
        )
        return ModalityActionResponse(**data)

    async def unlabel(
        self,
        message_ids: list[str],
        labels: list[str],
    ) -> ModalityActionResponse:
        """Remove labels from emails.
        
        Creates an immediate event to remove one or more labels from specified emails.
        
        Args:
            message_ids: Message IDs to unlabel.
            labels: Labels to remove.
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If message_ids or labels is empty.
            APIError: If the request fails.
        """
        data = await self._post(
            f"{self._BASE_PATH}/unlabel",
            json={"message_ids": message_ids, "labels": labels},
        )
        return ModalityActionResponse(**data)

    async def move(
        self,
        message_ids: list[str],
        folder: str,
    ) -> ModalityActionResponse:
        """Move emails to a different folder.
        
        Creates an immediate event to move one or more emails to the specified folder.
        
        Args:
            message_ids: Message IDs to move.
            folder: Target folder name.
        
        Returns:
            Action response with event details.
        
        Raises:
            ValidationError: If message_ids is empty or folder is invalid.
            APIError: If the request fails.
        """
        data = await self._post(
            f"{self._BASE_PATH}/move",
            json={"message_ids": message_ids, "folder": folder},
        )
        return ModalityActionResponse(**data)
