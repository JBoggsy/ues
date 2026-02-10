"""SMS/RCS modality endpoints.

Provides REST API endpoints for SMS and RCS messaging operations including sending,
receiving, reading, reacting to messages, and managing group conversations.

All endpoints require authentication via X-API-Key header.
"""

from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ues.api.auth import Permissions, require_permission
from ues.api.broadcast import broadcast_event
from ues.api.dependencies import SimulationEngineDep
from ues.api.models import ModalityActionResponse
from ues.api.utils import create_immediate_event
from ues.api.websocket import WSEventType
from ues.models.api_key import APIKey
from ues.models.modalities.sms_input import SMSInput
from ues.models.modalities.sms_state import (
    GroupParticipant,
    MessageAttachment,
    MessageReaction,
    SMSConversation,
    SMSMessage,
    SMSState,
)

router = APIRouter(
    prefix="/sms",
    tags=["sms"],
)


# ============================================================================
# Request Models
# ============================================================================


class MessageAttachmentRequest(BaseModel):
    """Request model for message attachments.

    Attributes:
        filename: Original filename.
        size: File size in bytes.
        mime_type: MIME type (e.g., "image/jpeg", "video/mp4").
        thumbnail_url: Optional thumbnail for images/videos.
        duration: Optional duration in seconds for audio/video.
    """

    filename: str = Field(description="Original filename")
    size: int = Field(gt=0, description="File size in bytes")
    mime_type: str = Field(description="MIME type")
    thumbnail_url: str | None = Field(
        default=None, description="Thumbnail URL for images/videos"
    )
    duration: int | None = Field(
        default=None, ge=0, description="Duration in seconds for audio/video"
    )


class SendSMSRequest(BaseModel):
    """Request model for sending an SMS/RCS message.

    Attributes:
        from_number: Sender phone number.
        to_numbers: Recipient phone number(s).
        body: Message text content.
        message_type: "sms" or "rcs".
        attachments: Optional media/file attachments (RCS only).
        replied_to_message_id: Optional ID of message being replied to.
    """

    from_number: str = Field(description="Sender phone number")
    to_numbers: list[str] = Field(min_length=1, description="Recipient phone number(s)")
    body: str = Field(description="Message text content")
    message_type: Literal["sms", "rcs"] = Field(default="sms", description="Message type")
    attachments: list[MessageAttachmentRequest] = Field(
        default_factory=list, description="Media/file attachments"
    )
    replied_to_message_id: str | None = Field(
        default=None, description="ID of message being replied to"
    )


class ReceiveSMSRequest(BaseModel):
    """Request model for simulating receiving an SMS/RCS message.

    Attributes:
        from_number: Sender phone number.
        to_numbers: Recipient phone number(s).
        body: Message text content.
        message_type: "sms" or "rcs".
        attachments: Optional media/file attachments (RCS only).
        replied_to_message_id: Optional ID of message being replied to.
        sent_at: When message was originally sent (defaults to current time).
    """

    from_number: str = Field(description="Sender phone number")
    to_numbers: list[str] = Field(min_length=1, description="Recipient phone number(s)")
    body: str = Field(description="Message text content")
    message_type: Literal["sms", "rcs"] = Field(default="sms", description="Message type")
    attachments: list[MessageAttachmentRequest] = Field(
        default_factory=list, description="Media/file attachments"
    )
    replied_to_message_id: str | None = Field(
        default=None, description="ID of message being replied to"
    )
    sent_at: datetime | None = Field(
        default=None, description="When message was originally sent"
    )


class SMSMarkRequest(BaseModel):
    """Request model for marking messages as read/unread.

    Attributes:
        message_ids: Message IDs to mark.
    """

    message_ids: list[str] = Field(min_length=1, description="Message IDs to mark")


class SMSReactRequest(BaseModel):
    """Request model for adding a reaction to a message.

    Attributes:
        message_id: Message ID to react to.
        phone_number: Phone number of person reacting.
        emoji: Emoji character(s) for the reaction.
    """

    message_id: str = Field(description="Message ID to react to")
    phone_number: str = Field(description="Phone number of person reacting")
    emoji: str = Field(description="Emoji character(s) for the reaction")


class SMSDeleteRequest(BaseModel):
    """Request model for deleting messages.

    Attributes:
        message_ids: Message IDs to delete.
    """

    message_ids: list[str] = Field(min_length=1, description="Message IDs to delete")


class SMSConversationUpdateRequest(BaseModel):
    """Request model for updating conversation settings.

    Attributes:
        thread_id: Conversation ID to update.
        pin: Set pinned status (true to pin, false to unpin).
        mute: Set muted status (true to mute, false to unmute).
        archive: Set archived status (true to archive, false to unarchive).
        mark_all_read: Mark all messages in conversation as read.
        draft_message: Save or clear draft message (null to clear).
    """

    thread_id: str = Field(description="Conversation ID to update")
    pin: bool | None = Field(default=None, description="Set pinned status")
    mute: bool | None = Field(default=None, description="Set muted status")
    archive: bool | None = Field(default=None, description="Set archived status")
    mark_all_read: bool | None = Field(
        default=None, description="Mark all messages as read"
    )
    draft_message: str | None = Field(
        default=None, description="Save draft message (null to clear)"
    )


class SMSQueryRequest(BaseModel):
    """Request model for querying SMS/RCS messages.

    Attributes:
        thread_id: Filter by conversation/thread ID.
        from_number: Filter by sender phone number.
        to_number: Filter by recipient phone number.
        body_contains: Filter by message text (case-insensitive).
        message_type: Filter by message type ("sms" or "rcs").
        direction: Filter by direction ("incoming" or "outgoing").
        is_read: Filter by read status.
        has_attachments: Filter by attachment presence.
        delivery_status: Filter by delivery status.
        is_deleted: Filter by deleted status.
        is_spam: Filter by spam status.
        sent_after: Filter by sent date (inclusive).
        sent_before: Filter by sent date (inclusive).
        limit: Maximum number of results to return.
        offset: Number of results to skip (for pagination).
        sort_by: Field to sort by.
        sort_order: Sort direction ("asc" or "desc").
    """

    thread_id: str | None = Field(default=None, description="Filter by thread ID")
    from_number: str | None = Field(default=None, description="Filter by sender")
    to_number: str | None = Field(default=None, description="Filter by recipient")
    body_contains: str | None = Field(
        default=None, description="Filter by message text"
    )
    message_type: Literal["sms", "rcs"] | None = Field(
        default=None, description="Filter by message type"
    )
    direction: Literal["incoming", "outgoing"] | None = Field(
        default=None, description="Filter by direction"
    )
    is_read: bool | None = Field(default=None, description="Filter by read status")
    has_attachments: bool | None = Field(
        default=None, description="Filter by attachment presence"
    )
    delivery_status: Literal["sending", "sent", "delivered", "failed", "read"] | None = Field(
        default=None, description="Filter by delivery status"
    )
    is_deleted: bool | None = Field(default=None, description="Filter by deleted status")
    is_spam: bool | None = Field(default=None, description="Filter by spam status")
    sent_after: datetime | None = Field(
        default=None, description="Filter by sent date (inclusive)"
    )
    sent_before: datetime | None = Field(
        default=None, description="Filter by sent date (inclusive)"
    )
    limit: int | None = Field(
        default=None, ge=1, le=1000, description="Maximum results to return"
    )
    offset: int = Field(default=0, ge=0, description="Number of results to skip")
    sort_by: str | None = Field(
        default=None,
        description="Field to sort by (e.g., 'sent_at', 'from_number')",
    )
    sort_order: Literal["asc", "desc"] | None = Field(
        default="desc", description="Sort direction"
    )


# ============================================================================
# Response Models
# ============================================================================


class SMSStateResponse(BaseModel):
    """Response model for SMS state endpoint.

    Attributes:
        modality_type: Always "sms".
        current_time: Current simulator time.
        user_phone_number: The simulated user's phone number.
        messages: All messages indexed by message_id.
        conversations: All conversations indexed by thread_id.
        total_message_count: Total number of messages.
        unread_count: Total number of unread messages.
        total_conversation_count: Total number of conversations.
    """

    modality_type: str = Field(default="sms")
    current_time: datetime
    user_phone_number: str
    messages: dict[str, SMSMessage]
    conversations: dict[str, SMSConversation]
    total_message_count: int
    unread_count: int
    total_conversation_count: int


class SMSCompactStateResponse(BaseModel):
    """Compact response model for SMS state endpoint.

    Used when compact=true query parameter is set. Optimized for LLM context.
    Returns conversation metadata without full message content.

    Attributes:
        modality_type: Always "sms".
        last_updated: ISO timestamp of last update.
        update_count: Number of SMS state changes.
        user_phone_number: The simulated user's phone number.
        conversations: Conversation metadata (without full message content).
        total_conversations: Number of conversations.
        total_messages: Total message count.
        unread_total: Total unread message count.
    """

    modality_type: str = Field(default="sms")
    last_updated: str
    update_count: int
    user_phone_number: str
    conversations: dict[str, Any]
    total_conversations: int
    total_messages: int
    unread_total: int


class SMSQueryResponse(BaseModel):
    """Response model for SMS query endpoint.

    Attributes:
        modality_type: Always "sms".
        messages: Query results (matching messages).
        total_count: Total number of results matching query.
        returned_count: Number of results returned (after pagination).
        query: Echo of query parameters for debugging.
    """

    modality_type: str = Field(default="sms")
    messages: list[SMSMessage]
    total_count: int
    returned_count: int
    query: dict


# ============================================================================
# Route Handlers
# ============================================================================


@router.get("/state")
async def get_sms_state(
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.SMS_STATE))],
    compact: bool = False,
) -> SMSStateResponse | SMSCompactStateResponse:
    """Get current SMS state.

    Returns a snapshot of the SMS system including messages
    and conversations.

    Args:
        engine: The simulation engine dependency.
        compact: If True, return compact state with conversation metadata only.
            Optimized for LLM context and quick status checks.

    Returns:
        SMSStateResponse: Full state with all messages (default).
        SMSCompactStateResponse: Compact state with conversation metadata (if compact=True).
    
    Requires:
        Permission: sms:state
    """
    sms_state = engine.environment.get_state("sms")

    if not isinstance(sms_state, SMSState):
        raise HTTPException(
            status_code=500,
            detail="SMS state not properly initialized",
        )

    # Return compact snapshot if requested
    if compact:
        snapshot = sms_state.get_snapshot()
        return SMSCompactStateResponse(**snapshot)

    # Calculate total counts
    unread_count = sum(1 for msg in sms_state.messages.values() if not msg.is_read)

    return SMSStateResponse(
        current_time=engine.environment.time_state.current_time,
        user_phone_number=sms_state.user_phone_number,
        messages=sms_state.messages,
        conversations=sms_state.conversations,
        total_message_count=len(sms_state.messages),
        unread_count=unread_count,
        total_conversation_count=len(sms_state.conversations),
    )


@router.post("/query", response_model=SMSQueryResponse)
async def query_sms(
    request: SMSQueryRequest,
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.SMS_QUERY))],
) -> SMSQueryResponse:
    """Query SMS messages with filters.

    Allows filtering and searching through message data with various criteria
    including thread, sender, recipient, text content, date ranges, etc.

    Args:
        request: Query filters and pagination parameters.
        engine: The simulation engine dependency.

    Returns:
        Filtered message results with counts.
    
    Requires:
        Permission: sms:query
    """
    sms_state = engine.environment.get_state("sms")

    if not isinstance(sms_state, SMSState):
        raise HTTPException(
            status_code=500,
            detail="SMS state not properly initialized",
        )

    query_params = {
        "thread_id": request.thread_id,
        "from_number": request.from_number,
        "to_number": request.to_number,
        "body_contains": request.body_contains,
        "message_type": request.message_type,
        "direction": request.direction,
        "is_read": request.is_read,
        "has_attachments": request.has_attachments,
        "delivery_status": request.delivery_status,
        "is_deleted": request.is_deleted,
        "is_spam": request.is_spam,
        "sent_after": request.sent_after,
        "sent_before": request.sent_before,
        "limit": request.limit,
        "offset": request.offset,
        "sort_by": request.sort_by,
        "sort_order": request.sort_order,
    }

    result = sms_state.query(query_params)

    return SMSQueryResponse(
        messages=result["messages"],
        total_count=result["total_count"],
        returned_count=result["count"],
        query=request.model_dump(exclude_none=True),
    )


@router.post("/send", response_model=ModalityActionResponse)
async def send_sms(
    request: SendSMSRequest,
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.SMS_SEND))],
) -> ModalityActionResponse:
    """Send a new SMS/RCS message.

    Creates an immediate event to send a message from the user to specified
    recipient(s) with text content and optional attachments.

    Args:
        request: Message content and recipients.
        engine: The simulation engine dependency.

    Returns:
        Action response with event details.
    
    Requires:
        Permission: sms:send
    """
    try:
        # Build message data
        message_data = {
            "from_number": request.from_number,
            "to_numbers": request.to_numbers,
            "body": request.body,
            "message_type": request.message_type,
        }

        # Add optional fields
        if request.attachments:
            message_data["attachments"] = [
                att.model_dump() for att in request.attachments
            ]
        if request.replied_to_message_id:
            message_data["replied_to_message_id"] = request.replied_to_message_id

        # Convert request to SMSInput
        sms_input = SMSInput(
            timestamp=engine.environment.time_state.current_time,
            action="send_message",
            message_data=message_data,
        )

        # Create and add event
        event = create_immediate_event(
            engine=engine,
            modality="sms",
            data=sms_input,
            priority=100,
        )

        # Broadcast SMS sent event
        await broadcast_event(WSEventType.SMS_SENT, {
            "message_id": event.event_id,
            "to": request.to_numbers,
            "preview": request.body[:50] + "..." if len(request.body) > 50 else request.body,
        })

        return ModalityActionResponse(
            event_id=event.event_id,
            scheduled_time=event.scheduled_time,
            status=event.status.value,
            message=(
                "SMS message sent successfully"
                if not event.error_message
                else f"Failed to send SMS: {event.error_message}"
            ),
            modality="sms",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send SMS: {str(e)}",
        )


@router.post("/receive", response_model=ModalityActionResponse)
async def receive_sms(
    request: ReceiveSMSRequest,
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.SMS_RECEIVE))],
) -> ModalityActionResponse:
    """Simulate receiving an SMS/RCS message.

    Creates an immediate event to receive a message from an external sender
    into the user's message inbox.

    Args:
        request: Message content and metadata.
        engine: The simulation engine dependency.

    Returns:
        Action response with event details.
    
    Requires:
        Permission: sms:receive
    """
    try:
        # Build message data
        message_data = {
            "from_number": request.from_number,
            "to_numbers": request.to_numbers,
            "body": request.body,
            "message_type": request.message_type,
        }

        # Add optional fields
        if request.attachments:
            message_data["attachments"] = [
                att.model_dump() for att in request.attachments
            ]
        if request.replied_to_message_id:
            message_data["replied_to_message_id"] = request.replied_to_message_id
        if request.sent_at:
            message_data["sent_at"] = request.sent_at.isoformat()

        # Convert request to SMSInput
        sms_input = SMSInput(
            timestamp=engine.environment.time_state.current_time,
            action="receive_message",
            message_data=message_data,
        )

        # Create and add event
        event = create_immediate_event(
            engine=engine,
            modality="sms",
            data=sms_input,
            priority=100,
        )

        # Broadcast SMS received event
        await broadcast_event(WSEventType.SMS_RECEIVED, {
            "message_id": event.event_id,
            "from": request.from_number,
            "preview": request.body[:50] + "..." if len(request.body) > 50 else request.body,
        })

        return ModalityActionResponse(
            event_id=event.event_id,
            scheduled_time=event.scheduled_time,
            status=event.status.value,
            message=(
                "SMS message received successfully"
                if not event.error_message
                else f"Failed to receive SMS: {event.error_message}"
            ),
            modality="sms",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to receive SMS: {str(e)}",
        )


@router.post("/read", response_model=ModalityActionResponse)
async def mark_sms_read(
    request: SMSMarkRequest,
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.SMS_READ))],
) -> ModalityActionResponse:
    """Mark messages as read.

    Creates an immediate event to mark one or more messages as read.

    Args:
        request: Message IDs to mark.
        engine: The simulation engine dependency.

    Returns:
        Action response with event details.
    
    Requires:
        Permission: sms:read
    """
    try:
        sms_state = engine.environment.get_state("sms")

        if not isinstance(sms_state, SMSState):
            raise HTTPException(
                status_code=500,
                detail="SMS state not properly initialized",
            )

        current_time = engine.environment.time_state.current_time
        marked_count = 0

        for message_id in request.message_ids:
            if message_id in sms_state.messages:
                sms_state.messages[message_id].mark_read(current_time)
                marked_count += 1

        # Create an event record for auditing
        sms_input = SMSInput(
            timestamp=current_time,
            action="update_delivery_status",
            delivery_update_data={
                "message_id": request.message_ids[0] if request.message_ids else "",
                "new_status": "read",
            },
        )

        event = create_immediate_event(
            engine=engine,
            modality="sms",
            data=sms_input,
            priority=100,
        )

        return ModalityActionResponse(
            event_id=event.event_id,
            scheduled_time=event.scheduled_time,
            status=event.status.value,
            message=(
                f"Marked {marked_count} message(s) as read"
                if not event.error_message
                else f"Failed to mark messages as read: {event.error_message}"
            ),
            modality="sms",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to mark messages as read: {str(e)}",
        )


@router.post("/unread", response_model=ModalityActionResponse)
async def mark_sms_unread(
    request: SMSMarkRequest,
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.SMS_UNREAD))],
) -> ModalityActionResponse:
    """Mark messages as unread.

    Creates an immediate event to mark one or more messages as unread.

    Args:
        request: Message IDs to mark.
        engine: The simulation engine dependency.

    Returns:
        Action response with event details.
    
    Requires:
        Permission: sms:unread
    """
    try:
        sms_state = engine.environment.get_state("sms")

        if not isinstance(sms_state, SMSState):
            raise HTTPException(
                status_code=500,
                detail="SMS state not properly initialized",
            )

        marked_count = 0

        for message_id in request.message_ids:
            if message_id in sms_state.messages:
                sms_state.messages[message_id].mark_unread()
                marked_count += 1

        # Create an event record for auditing
        sms_input = SMSInput(
            timestamp=engine.environment.time_state.current_time,
            action="update_delivery_status",
            delivery_update_data={
                "message_id": request.message_ids[0] if request.message_ids else "",
                "new_status": "delivered",  # unread doesn't have a delivery status
            },
        )

        event = create_immediate_event(
            engine=engine,
            modality="sms",
            data=sms_input,
            priority=100,
        )

        return ModalityActionResponse(
            event_id=event.event_id,
            scheduled_time=event.scheduled_time,
            status=event.status.value,
            message=(
                f"Marked {marked_count} message(s) as unread"
                if not event.error_message
                else f"Failed to mark messages as unread: {event.error_message}"
            ),
            modality="sms",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to mark messages as unread: {str(e)}",
        )


@router.post("/delete", response_model=ModalityActionResponse)
async def delete_sms(
    request: SMSDeleteRequest,
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.SMS_DELETE))],
) -> ModalityActionResponse:
    """Delete messages.

    Creates an immediate event to delete one or more messages.

    Args:
        request: Message IDs to delete.
        engine: The simulation engine dependency.

    Returns:
        Action response with event details.
    
    Requires:
        Permission: sms:delete
    """
    try:
        sms_state = engine.environment.get_state("sms")

        if not isinstance(sms_state, SMSState):
            raise HTTPException(
                status_code=500,
                detail="SMS state not properly initialized",
            )

        deleted_count = 0
        current_time = engine.environment.time_state.current_time

        for message_id in request.message_ids:
            if message_id in sms_state.messages:
                # Use the input to properly process the deletion
                sms_input = SMSInput(
                    timestamp=current_time,
                    action="delete_message",
                    delete_data={
                        "message_id": message_id,
                    },
                )
                sms_state.apply_input(sms_input)
                deleted_count += 1

        # Create an event record for auditing (use last message_id processed)
        event_input = SMSInput(
            timestamp=current_time,
            action="delete_message",
            delete_data={
                "message_id": request.message_ids[0] if request.message_ids else "",
            },
        )

        event = create_immediate_event(
            engine=engine,
            modality="sms",
            data=event_input,
            priority=100,
        )

        return ModalityActionResponse(
            event_id=event.event_id,
            scheduled_time=event.scheduled_time,
            status=event.status.value,
            message=(
                f"Deleted {deleted_count} message(s)"
                if not event.error_message
                else f"Failed to delete messages: {event.error_message}"
            ),
            modality="sms",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete messages: {str(e)}",
        )


@router.post("/react", response_model=ModalityActionResponse)
async def react_to_sms(
    request: SMSReactRequest,
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.SMS_REACT))],
) -> ModalityActionResponse:
    """Add a reaction to a message.

    Creates an immediate event to add an emoji reaction to a message (RCS only).

    Args:
        request: Message ID, phone number, and emoji.
        engine: The simulation engine dependency.

    Returns:
        Action response with event details.
    
    Requires:
        Permission: sms:react
    """
    try:
        # Convert request to SMSInput
        sms_input = SMSInput(
            timestamp=engine.environment.time_state.current_time,
            action="add_reaction",
            reaction_data={
                "message_id": request.message_id,
                "phone_number": request.phone_number,
                "emoji": request.emoji,
            },
        )

        event = create_immediate_event(
            engine=engine,
            modality="sms",
            data=sms_input,
            priority=100,
        )

        return ModalityActionResponse(
            event_id=event.event_id,
            scheduled_time=event.scheduled_time,
            status=event.status.value,
            message=(
                f"Added reaction '{request.emoji}' to message"
                if not event.error_message
                else f"Failed to add reaction: {event.error_message}"
            ),
            modality="sms",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add reaction: {str(e)}",
        )


@router.post("/conversation", response_model=ModalityActionResponse)
async def update_conversation(
    request: SMSConversationUpdateRequest,
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.SMS_CONVERSATION))],
) -> ModalityActionResponse:
    """Update conversation settings.

    Updates conversation metadata such as pinned, muted, or archived status.
    Can also mark all messages as read or save/clear a draft message.

    Args:
        request: Conversation ID and settings to update.
        engine: The simulation engine dependency.

    Returns:
        Action response with event details.
    
    Requires:
        Permission: sms:conversation
    """
    try:
        # Build conversation_update_data from request
        update_data: dict = {"thread_id": request.thread_id}
        
        if request.pin is not None:
            update_data["pin"] = request.pin
        if request.mute is not None:
            update_data["mute"] = request.mute
        if request.archive is not None:
            update_data["archive"] = request.archive
        if request.mark_all_read is not None:
            update_data["mark_all_read"] = request.mark_all_read
        if request.draft_message is not None:
            update_data["draft_message"] = request.draft_message

        # Validate that at least one update is specified
        if len(update_data) == 1:  # Only thread_id
            raise HTTPException(
                status_code=400,
                detail="At least one update field (pin, mute, archive, mark_all_read, draft_message) must be specified",
            )

        # Create SMSInput
        sms_input = SMSInput(
            timestamp=engine.environment.time_state.current_time,
            action="update_conversation",
            conversation_update_data=update_data,
        )

        event = create_immediate_event(
            engine=engine,
            modality="sms",
            data=sms_input,
            priority=100,
        )

        # Build descriptive message
        updates = []
        if request.pin is not None:
            updates.append("pinned" if request.pin else "unpinned")
        if request.mute is not None:
            updates.append("muted" if request.mute else "unmuted")
        if request.archive is not None:
            updates.append("archived" if request.archive else "unarchived")
        if request.mark_all_read:
            updates.append("marked all read")
        if request.draft_message is not None:
            updates.append("draft saved" if request.draft_message else "draft cleared")

        return ModalityActionResponse(
            event_id=event.event_id,
            scheduled_time=event.scheduled_time,
            status=event.status.value,
            message=(
                f"Conversation {', '.join(updates)}"
                if not event.error_message
                else f"Failed to update conversation: {event.error_message}"
            ),
            modality="sms",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update conversation: {str(e)}",
        )
