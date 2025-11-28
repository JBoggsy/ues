"""Email modality endpoints.

Provides REST API endpoints for email operations including sending, receiving,
reading, organizing, and querying email messages. Supports full email lifecycle
from composition to archival/deletion.
"""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from api.dependencies import SimulationEngineDep
from api.models import ModalityActionResponse, ModalityStateResponse
from api.utils import create_immediate_event
from models.modalities.email_input import EmailInput
from models.modalities.email_state import Email, EmailState, EmailThread

router = APIRouter(
    prefix="/email",
    tags=["email"],
)


# ============================================================================
# Request Models
# ============================================================================


class EmailAttachmentRequest(BaseModel):
    """Request model for email attachments.

    Attributes:
        filename: Name of the attached file.
        size: File size in bytes.
        mime_type: MIME type (e.g., "application/pdf", "image/jpeg").
        content_id: Optional content ID for inline images.
    """

    filename: str = Field(description="Name of the attached file")
    size: int = Field(gt=0, description="File size in bytes")
    mime_type: str = Field(description="MIME type")
    content_id: str | None = Field(
        default=None, description="Content ID for inline images"
    )


class SendEmailRequest(BaseModel):
    """Request model for simulating sending a new email.

    Attributes:
        from_address: Sender email address.
        to_addresses: Primary recipient addresses.
        cc_addresses: CC recipient addresses.
        bcc_addresses: BCC recipient addresses.
        reply_to_address: Reply-to address if different from sender.
        subject: Email subject line.
        body_text: Plain text body content.
        body_html: HTML body content.
        attachments: File attachments.
        priority: Priority level ("high", "normal", "low").
    """

    from_address: str = Field(description="Sender email address")
    to_addresses: list[str] = Field(min_length=1, description="Primary recipient addresses")
    cc_addresses: list[str] = Field(default_factory=list, description="CC recipient addresses")
    bcc_addresses: list[str] = Field(default_factory=list, description="BCC recipient addresses")
    reply_to_address: str | None = Field(default=None, description="Reply-to address")
    subject: str = Field(description="Email subject line")
    body_text: str = Field(description="Plain text body content")
    body_html: str | None = Field(default=None, description="HTML body content")
    attachments: list[EmailAttachmentRequest] = Field(
        default_factory=list, description="File attachments"
    )
    priority: Literal["high", "normal", "low"] = Field(
        default="normal", description="Priority level"
    )


class ReceiveEmailRequest(BaseModel):
    """Request model for simulating receiving an email.

    Attributes:
        from_address: Sender email address.
        to_addresses: Primary recipient addresses.
        cc_addresses: CC recipient addresses.
        bcc_addresses: BCC recipient addresses.
        reply_to_address: Reply-to address if different from sender.
        subject: Email subject line.
        body_text: Plain text body content.
        body_html: HTML body content.
        attachments: File attachments.
        thread_id: Thread identifier for conversation grouping.
        in_reply_to: Message ID this email replies to.
        references: List of message IDs in thread chain.
        priority: Priority level ("high", "normal", "low").
        sent_at: When email was originally sent (defaults to current time).
    """

    from_address: str = Field(description="Sender email address")
    to_addresses: list[str] = Field(min_length=1, description="Primary recipient addresses")
    cc_addresses: list[str] = Field(default_factory=list, description="CC recipient addresses")
    bcc_addresses: list[str] = Field(default_factory=list, description="BCC recipient addresses")
    reply_to_address: str | None = Field(default=None, description="Reply-to address")
    subject: str = Field(description="Email subject line")
    body_text: str = Field(description="Plain text body content")
    body_html: str | None = Field(default=None, description="HTML body content")
    attachments: list[EmailAttachmentRequest] = Field(
        default_factory=list, description="File attachments"
    )
    thread_id: str | None = Field(default=None, description="Thread identifier")
    in_reply_to: str | None = Field(default=None, description="Message ID this replies to")
    references: list[str] = Field(
        default_factory=list, description="Message IDs in thread chain"
    )
    priority: Literal["high", "normal", "low"] = Field(
        default="normal", description="Priority level"
    )
    sent_at: datetime | None = Field(
        default=None, description="When email was originally sent"
    )


class EmailMarkRequest(BaseModel):
    """Request model for marking emails (read/unread/star/unstar).

    Attributes:
        message_ids: Message IDs to mark (single or multiple).
    """

    message_ids: list[str] = Field(min_length=1, description="Message IDs to mark")


class EmailLabelRequest(BaseModel):
    """Request model for adding/removing labels to emails.

    Attributes:
        message_ids: Message IDs to label.
        labels: Labels to add/remove.
    """

    message_ids: list[str] = Field(min_length=1, description="Message IDs to label")
    labels: list[str] = Field(min_length=1, description="Labels to add/remove")


class EmailMoveRequest(BaseModel):
    """Request model for moving emails to a different folder.

    Attributes:
        message_ids: Message IDs to move.
        folder: Target folder name.
    """

    message_ids: list[str] = Field(min_length=1, description="Message IDs to move")
    folder: str = Field(description="Target folder name")


class EmailQueryRequest(BaseModel):
    """Request model for querying email state.

    Attributes:
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
        sort_by: Field to sort by.
        sort_order: Sort direction ("asc" or "desc").
    """

    folder: str | None = Field(default=None, description="Filter by folder name")
    is_read: bool | None = Field(default=None, description="Filter by read status")
    is_starred: bool | None = Field(default=None, description="Filter by starred status")
    from_address: str | None = Field(default=None, description="Filter by sender address")
    to_address: str | None = Field(
        default=None, description="Filter by recipient address"
    )
    subject_contains: str | None = Field(
        default=None, description="Filter by subject text"
    )
    body_contains: str | None = Field(default=None, description="Filter by body text")
    has_attachments: bool | None = Field(
        default=None, description="Filter by attachment presence"
    )
    labels: list[str] | None = Field(
        default=None, description="Filter by labels (AND logic)"
    )
    thread_id: str | None = Field(default=None, description="Filter by thread ID")
    priority: Literal["high", "normal", "low"] | None = Field(
        default=None, description="Filter by priority level"
    )
    sent_after: datetime | None = Field(
        default=None, description="Filter by sent date (inclusive)"
    )
    sent_before: datetime | None = Field(
        default=None, description="Filter by sent date (inclusive)"
    )
    received_after: datetime | None = Field(
        default=None, description="Filter by received date (inclusive)"
    )
    received_before: datetime | None = Field(
        default=None, description="Filter by received date (inclusive)"
    )
    limit: int | None = Field(
        default=None, ge=1, le=1000, description="Maximum results to return"
    )
    offset: int = Field(default=0, ge=0, description="Number of results to skip")
    sort_by: str | None = Field(
        default=None,
        description="Field to sort by (e.g., 'sent_at', 'received_at', 'subject')",
    )
    sort_order: Literal["asc", "desc"] | None = Field(
        default="desc", description="Sort direction"
    )


# ============================================================================
# Response Models
# ============================================================================


class EmailStateResponse(BaseModel):
    """Response model for email state endpoint.

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

    modality_type: str = Field(default="email")
    current_time: datetime
    user_email_address: str
    emails: dict[str, Email]
    threads: dict[str, EmailThread]
    folders: dict[str, int]
    labels: dict[str, int]
    total_email_count: int
    unread_count: int
    starred_count: int


class EmailQueryResponse(BaseModel):
    """Response model for email query endpoint.

    Attributes:
        modality_type: Always "email".
        emails: Query results (matching emails).
        total_count: Total number of results matching query.
        returned_count: Number of results returned (after pagination).
        query: Echo of query parameters for debugging.
    """

    modality_type: str = Field(default="email")
    emails: list[Email]
    total_count: int
    returned_count: int
    query: dict


# ============================================================================
# Route Handlers
# ============================================================================


@router.get("/state", response_model=EmailStateResponse)
async def get_email_state(engine: SimulationEngineDep) -> EmailStateResponse:
    """Get current email state.

    Returns a complete snapshot of the email system including all messages,
    threads, folders, and labels.

    Args:
        engine: The simulation engine dependency.

    Returns:
        Complete email state with all messages.
    """
    email_state = engine.environment.get_state("email")

    if not isinstance(email_state, EmailState):
        raise HTTPException(
            status_code=500,
            detail="Email state not properly initialized",
        )

    # Calculate folder and label counts
    folder_counts = {
        folder: len(message_ids) for folder, message_ids in email_state.folders.items()
    }
    label_counts = {
        label: len(message_ids) for label, message_ids in email_state.labels.items()
    }

    # Calculate total counts
    unread_count = sum(1 for email in email_state.emails.values() if not email.is_read)
    starred_count = sum(1 for email in email_state.emails.values() if email.is_starred)

    return EmailStateResponse(
        current_time=engine.environment.time_state.current_time,
        user_email_address=email_state.user_email_address,
        emails=email_state.emails,
        threads=email_state.threads,
        folders=folder_counts,
        labels=label_counts,
        total_email_count=len(email_state.emails),
        unread_count=unread_count,
        starred_count=starred_count,
    )


@router.post("/query", response_model=EmailQueryResponse)
async def query_emails(
    request: EmailQueryRequest, engine: SimulationEngineDep
) -> EmailQueryResponse:
    """Query emails with filters.

    Allows filtering and searching through email data with various criteria
    including folder, read status, sender, subject, date ranges, etc.

    Args:
        request: Query filters and pagination parameters.
        engine: The simulation engine dependency.

    Returns:
        Filtered email results with counts.
    """
    email_state = engine.environment.get_state("email")

    if not isinstance(email_state, EmailState):
        raise HTTPException(
            status_code=500,
            detail="Email state not properly initialized",
        )

    query_params = {
        "folder": request.folder,
        "is_read": request.is_read,
        "is_starred": request.is_starred,
        "from_address": request.from_address,
        "to_address": request.to_address,
        "subject_contains": request.subject_contains,
        "body_contains": request.body_contains,
        "has_attachments": request.has_attachments,
        "labels": request.labels,
        "thread_id": request.thread_id,
        "priority": request.priority,
        "sent_after": request.sent_after,
        "sent_before": request.sent_before,
        "received_after": request.received_after,
        "received_before": request.received_before,
        "limit": request.limit,
        "offset": request.offset,
        "sort_by": request.sort_by,
        "sort_order": request.sort_order,
    }

    result = email_state.query(query_params)

    return EmailQueryResponse(
        emails=result["emails"],
        total_count=result["total_count"],
        returned_count=result["returned_count"],
        query=request.model_dump(exclude_none=True),
    )


@router.post("/send", response_model=ModalityActionResponse)
async def send_email(
    request: SendEmailRequest, engine: SimulationEngineDep
) -> ModalityActionResponse:
    """Send a new email.

    Creates an immediate event to send an email from the user to specified
    recipients with subject, body, and optional attachments.

    Args:
        request: Email content and recipients.
        engine: The simulation engine dependency.

    Returns:
        Action response with event details.
    """
    try:
        # Convert request to EmailInput
        email_input = EmailInput(
            timestamp=engine.environment.time_state.current_time,
            operation="send",
            from_address=request.from_address,
            to_addresses=request.to_addresses,
            cc_addresses=request.cc_addresses if request.cc_addresses else [],
            bcc_addresses=request.bcc_addresses if request.bcc_addresses else [],
            subject=request.subject,
            body_text=request.body_text,
            body_html=request.body_html,
            reply_to_address=request.reply_to_address,
            priority=request.priority,
            attachments=[att.model_dump() for att in request.attachments] if request.attachments else [],
        )

        # Create and add event
        event = create_immediate_event(
            engine=engine,
            modality="email",
            data=email_input,
            priority=100,
        )

        return ModalityActionResponse(
            event_id=event.event_id,
            scheduled_time=event.scheduled_time,
            status="executed",
            message="Email sent successfully",
            modality="email",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send email: {str(e)}",
        )


@router.post("/receive", response_model=ModalityActionResponse)
async def receive_email(
    request: ReceiveEmailRequest, engine: SimulationEngineDep
) -> ModalityActionResponse:
    """Simulate receiving an email.

    Creates an immediate event to receive an email from an external sender
    into the user's inbox.

    Args:
        request: Email content and metadata.
        engine: The simulation engine dependency.

    Returns:
        Action response with event details.
    """
    try:
        # Convert request to EmailInput
        email_input = EmailInput(
            timestamp=engine.environment.time_state.current_time,
            operation="receive",
            from_address=request.from_address,
            to_addresses=request.to_addresses,
            cc_addresses=request.cc_addresses if request.cc_addresses else [],
            bcc_addresses=request.bcc_addresses if request.bcc_addresses else [],
            subject=request.subject,
            body_text=request.body_text,
            body_html=request.body_html,
            reply_to_address=request.reply_to_address,
            priority=request.priority,
            attachments=[att.model_dump() for att in request.attachments] if request.attachments else [],
            thread_id=request.thread_id,
            in_reply_to=request.in_reply_to,
            references=request.references if request.references else [],
            sent_at=request.sent_at,
        )

        # Create and add event
        event = create_immediate_event(
            engine=engine,
            modality="email",
            data=email_input,
            priority=100,
        )

        return ModalityActionResponse(
            event_id=event.event_id,
            scheduled_time=event.scheduled_time,
            status="executed",
            message="Email received successfully",
            modality="email",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to receive email: {str(e)}",
        )


@router.post("/read", response_model=ModalityActionResponse)
async def mark_emails_read(
    request: EmailMarkRequest, engine: SimulationEngineDep
) -> ModalityActionResponse:
    """Mark emails as read.

    Creates an immediate event to mark one or more emails as read.

    Args:
        request: Message IDs to mark.
        engine: The simulation engine dependency.

    Returns:
        Action response with event details.
    """
    try:
        # Convert request to EmailInput
        email_input = EmailInput(
            timestamp=engine.environment.time_state.current_time,
            operation="mark_read",
            message_ids=request.message_ids,
        )

        event = create_immediate_event(
            engine=engine,
            modality="email",
            data=email_input,
            priority=100,
        )

        return ModalityActionResponse(
            event_id=event.event_id,
            scheduled_time=event.scheduled_time,
            status="executed",
            message=f"Marked {len(request.message_ids)} email(s) as read",
            modality="email",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to mark emails as read: {str(e)}",
        )


@router.post("/unread", response_model=ModalityActionResponse)
async def mark_emails_unread(
    request: EmailMarkRequest, engine: SimulationEngineDep
) -> ModalityActionResponse:
    """Mark emails as unread.

    Creates an immediate event to mark one or more emails as unread.

    Args:
        request: Message IDs to mark.
        engine: The simulation engine dependency.

    Returns:
        Action response with event details.
    """
    try:
        # Convert request to EmailInput
        email_input = EmailInput(
            timestamp=engine.environment.time_state.current_time,
            operation="mark_unread",
            message_ids=request.message_ids,
        )

        event = create_immediate_event(
            engine=engine,
            modality="email",
            data=email_input,
            priority=100,
        )

        return ModalityActionResponse(
            event_id=event.event_id,
            scheduled_time=event.scheduled_time,
            status="executed",
            message=f"Marked {len(request.message_ids)} email(s) as unread",
            modality="email",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to mark emails as unread: {str(e)}",
        )


@router.post("/star", response_model=ModalityActionResponse)
async def star_emails(
    request: EmailMarkRequest, engine: SimulationEngineDep
) -> ModalityActionResponse:
    """Star/favorite emails.

    Creates an immediate event to star one or more emails.

    Args:
        request: Message IDs to star.
        engine: The simulation engine dependency.

    Returns:
        Action response with event details.
    """
    try:
        # Convert request to EmailInput
        email_input = EmailInput(
            timestamp=engine.environment.time_state.current_time,
            operation="star",
            message_ids=request.message_ids,
        )

        event = create_immediate_event(
            engine=engine,
            modality="email",
            data=email_input,
            priority=100,
        )

        return ModalityActionResponse(
            event_id=event.event_id,
            scheduled_time=event.scheduled_time,
            status="executed",
            message=f"Starred {len(request.message_ids)} email(s)",
            modality="email",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to star emails: {str(e)}",
        )


@router.post("/unstar", response_model=ModalityActionResponse)
async def unstar_emails(
    request: EmailMarkRequest, engine: SimulationEngineDep
) -> ModalityActionResponse:
    """Unstar emails.

    Creates an immediate event to unstar one or more emails.

    Args:
        request: Message IDs to unstar.
        engine: The simulation engine dependency.

    Returns:
        Action response with event details.
    """
    try:
        # Convert request to EmailInput
        email_input = EmailInput(
            timestamp=engine.environment.time_state.current_time,
            operation="unstar",
            message_ids=request.message_ids,
        )

        event = create_immediate_event(
            engine=engine,
            modality="email",
            data=email_input,
            priority=100,
        )

        return ModalityActionResponse(
            event_id=event.event_id,
            scheduled_time=event.scheduled_time,
            status="executed",
            message=f"Unstarred {len(request.message_ids)} email(s)",
            modality="email",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to unstar emails: {str(e)}",
        )


@router.post("/archive", response_model=ModalityActionResponse)
async def archive_emails(
    request: EmailMarkRequest, engine: SimulationEngineDep
) -> ModalityActionResponse:
    """Archive emails.

    Creates an immediate event to move one or more emails to the archive folder.

    Args:
        request: Message IDs to archive.
        engine: The simulation engine dependency.

    Returns:
        Action response with event details.
    """
    try:
        # Convert request to EmailInput
        email_input = EmailInput(
            timestamp=engine.environment.time_state.current_time,
            operation="archive",
            message_ids=request.message_ids,
        )

        event = create_immediate_event(
            engine=engine,
            modality="email",
            data=email_input,
            priority=100,
        )

        return ModalityActionResponse(
            event_id=event.event_id,
            scheduled_time=event.scheduled_time,
            status="executed",
            message=f"Archived {len(request.message_ids)} email(s)",
            modality="email",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to archive emails: {str(e)}",
        )


@router.post("/delete", response_model=ModalityActionResponse)
async def delete_emails(
    request: EmailMarkRequest, engine: SimulationEngineDep
) -> ModalityActionResponse:
    """Delete emails.

    Creates an immediate event to move one or more emails to the trash folder.

    Args:
        request: Message IDs to delete.
        engine: The simulation engine dependency.

    Returns:
        Action response with event details.
    """
    try:
        # Convert request to EmailInput
        email_input = EmailInput(
            timestamp=engine.environment.time_state.current_time,
            operation="delete",
            message_ids=request.message_ids,
        )

        event = create_immediate_event(
            engine=engine,
            modality="email",
            data=email_input,
            priority=100,
        )

        return ModalityActionResponse(
            event_id=event.event_id,
            scheduled_time=event.scheduled_time,
            status="executed",
            message=f"Deleted {len(request.message_ids)} email(s)",
            modality="email",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete emails: {str(e)}",
        )


@router.post("/label", response_model=ModalityActionResponse)
async def add_labels_to_emails(
    request: EmailLabelRequest, engine: SimulationEngineDep
) -> ModalityActionResponse:
    """Add labels to emails.

    Creates an immediate event to add one or more labels to specified emails.

    Args:
        request: Message IDs and labels to add.
        engine: The simulation engine dependency.

    Returns:
        Action response with event details.
    """
    try:
        # Convert request to EmailInput
        email_input = EmailInput(
            timestamp=engine.environment.time_state.current_time,
            operation="add_label",
            message_ids=request.message_ids,
            labels=request.labels,
        )

        event = create_immediate_event(
            engine=engine,
            modality="email",
            data=email_input,
            priority=100,
        )

        return ModalityActionResponse(
            event_id=event.event_id,
            scheduled_time=event.scheduled_time,
            status="executed",
            message=f"Added {len(request.labels)} label(s) to {len(request.message_ids)} email(s)",
            modality="email",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add labels: {str(e)}",
        )


@router.post("/unlabel", response_model=ModalityActionResponse)
async def remove_labels_from_emails(
    request: EmailLabelRequest, engine: SimulationEngineDep
) -> ModalityActionResponse:
    """Remove labels from emails.

    Creates an immediate event to remove one or more labels from specified emails.

    Args:
        request: Message IDs and labels to remove.
        engine: The simulation engine dependency.

    Returns:
        Action response with event details.
    """
    try:
        # Convert request to EmailInput
        email_input = EmailInput(
            timestamp=engine.environment.time_state.current_time,
            operation="remove_label",
            message_ids=request.message_ids,
            labels=request.labels,
        )

        event = create_immediate_event(
            engine=engine,
            modality="email",
            data=email_input,
            priority=100,
        )

        return ModalityActionResponse(
            event_id=event.event_id,
            scheduled_time=event.scheduled_time,
            status="executed",
            message=f"Removed {len(request.labels)} label(s) from {len(request.message_ids)} email(s)",
            modality="email",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to remove labels: {str(e)}",
        )


@router.post("/move", response_model=ModalityActionResponse)
async def move_emails(
    request: EmailMoveRequest, engine: SimulationEngineDep
) -> ModalityActionResponse:
    """Move emails to a different folder.

    Creates an immediate event to move one or more emails to the specified folder.

    Args:
        request: Message IDs and target folder.
        engine: The simulation engine dependency.

    Returns:
        Action response with event details.
    """
    try:
        # Convert request to EmailInput
        email_input = EmailInput(
            timestamp=engine.environment.time_state.current_time,
            operation="move",
            message_ids=request.message_ids,
            folder=request.folder,
        )

        event = create_immediate_event(
            engine=engine,
            modality="email",
            data=email_input,
            priority=100,
        )

        return ModalityActionResponse(
            event_id=event.event_id,
            scheduled_time=event.scheduled_time,
            status="executed",
            message=f"Moved {len(request.message_ids)} email(s) to {request.folder}",
            modality="email",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to move emails: {str(e)}",
        )
