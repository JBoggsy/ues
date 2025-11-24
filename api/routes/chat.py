"""Chat modality endpoints.

Provides REST API endpoints for chat conversation operations including sending
messages from user or assistant, querying conversation history, and managing
conversation state.
"""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.dependencies import SimulationEngineDep
from api.models import ModalityActionResponse
from api.utils import create_immediate_event
from models.modalities.chat_state import ChatMessage, ConversationMetadata, ChatState

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)


# ============================================================================
# Request Models
# ============================================================================


class SendChatMessageRequest(BaseModel):
    """Request model for sending a chat message.

    Attributes:
        role: Message sender role ("user" or "assistant").
        content: Message content (string for text, or list of content blocks for multimodal).
        conversation_id: Conversation/thread identifier (defaults to "default").
        metadata: Optional additional data (token count, model info, etc.).
    """

    role: Literal["user", "assistant"] = Field(
        description="Message sender role - 'user' or 'assistant'"
    )
    content: str | list[dict] = Field(
        description="Message content (string for text, or list of content blocks for multimodal)"
    )
    conversation_id: str = Field(
        default="default", description="Conversation/thread identifier"
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Optional additional data (token count, model info, etc.)",
    )


class DeleteChatMessageRequest(BaseModel):
    """Request model for deleting a chat message.

    Attributes:
        message_id: Message ID to delete.
    """

    message_id: str = Field(description="Message ID to delete")


class ClearChatRequest(BaseModel):
    """Request model for clearing conversation history.

    Attributes:
        conversation_id: Conversation ID to clear (defaults to "default").
    """

    conversation_id: str = Field(
        default="default", description="Conversation ID to clear"
    )


class ChatQueryRequest(BaseModel):
    """Request model for querying chat messages.

    Attributes:
        conversation_id: Filter by conversation ID.
        role: Filter by role ("user" or "assistant").
        since: Filter messages after this time.
        until: Filter messages before this time.
        search: Search for text in message content (case-insensitive).
        limit: Maximum number of results to return.
        offset: Number of results to skip (for pagination).
        sort_by: Field to sort by.
        sort_order: Sort direction ("asc" or "desc").
    """

    conversation_id: str | None = Field(
        default=None, description="Filter by conversation ID"
    )
    role: Literal["user", "assistant"] | None = Field(
        default=None, description="Filter by role"
    )
    since: datetime | None = Field(
        default=None, description="Filter messages after this time"
    )
    until: datetime | None = Field(
        default=None, description="Filter messages before this time"
    )
    search: str | None = Field(
        default=None, description="Search for text in message content"
    )
    limit: int | None = Field(
        default=None, ge=1, le=1000, description="Maximum results to return"
    )
    offset: int = Field(default=0, ge=0, description="Number of results to skip")
    sort_by: Literal["timestamp", "role", "conversation_id"] | None = Field(
        default="timestamp", description="Field to sort by"
    )
    sort_order: Literal["asc", "desc"] | None = Field(
        default="asc", description="Sort direction"
    )


# ============================================================================
# Response Models
# ============================================================================


class ChatStateResponse(BaseModel):
    """Response model for chat state endpoint.

    Attributes:
        modality_type: Always "chat".
        current_time: Current simulator time.
        conversations: Metadata for each conversation.
        messages: All messages (ordered by timestamp).
        total_message_count: Total number of messages.
        conversation_count: Total number of conversations.
        max_history_size: Maximum messages retained per conversation.
    """

    modality_type: str = Field(default="chat")
    current_time: datetime
    conversations: dict[str, ConversationMetadata]
    messages: list[ChatMessage]
    total_message_count: int
    conversation_count: int
    max_history_size: int


class ChatQueryResponse(BaseModel):
    """Response model for chat query endpoint.

    Attributes:
        modality_type: Always "chat".
        messages: Query results (matching messages).
        total_count: Total number of results matching query.
        returned_count: Number of results returned (after pagination).
        query: Echo of query parameters for debugging.
    """

    modality_type: str = Field(default="chat")
    messages: list[ChatMessage]
    total_count: int
    returned_count: int
    query: dict


# ============================================================================
# Route Handlers
# ============================================================================


@router.get("/state", response_model=ChatStateResponse)
async def get_chat_state(engine: SimulationEngineDep) -> ChatStateResponse:
    """Get current chat state.

    Returns a complete snapshot of all chat conversations and messages.

    Args:
        engine: The simulation engine dependency.

    Returns:
        Complete chat state with metadata.
    """
    chat_state = engine.environment.get_modality_state("chat")

    if not isinstance(chat_state, ChatState):
        raise HTTPException(
            status_code=500,
            detail="Chat state not properly initialized",
        )

    return ChatStateResponse(
        current_time=engine.environment.time_state.current_time,
        conversations=chat_state.conversations,
        messages=chat_state.messages,
        total_message_count=len(chat_state.messages),
        conversation_count=len(chat_state.conversations),
        max_history_size=chat_state.max_history_size,
    )


@router.post("/query", response_model=ChatQueryResponse)
async def query_chat(
    request: ChatQueryRequest, engine: SimulationEngineDep
) -> ChatQueryResponse:
    """Query chat messages with filters.

    Allows filtering and searching through chat history with various criteria
    including conversation, role, time range, and text search.

    Args:
        request: Query filters and pagination parameters.
        engine: The simulation engine dependency.

    Returns:
        Filtered message results with counts.
    """
    chat_state = engine.environment.get_modality_state("chat")

    if not isinstance(chat_state, ChatState):
        raise HTTPException(
            status_code=500,
            detail="Chat state not properly initialized",
        )

    # Build query parameters from request
    query_params = {}
    if request.conversation_id is not None:
        query_params["conversation_id"] = request.conversation_id
    if request.role is not None:
        query_params["role"] = request.role
    if request.since is not None:
        query_params["since"] = request.since
    if request.until is not None:
        query_params["until"] = request.until
    if request.search is not None:
        query_params["search"] = request.search
    if request.limit is not None:
        query_params["limit"] = request.limit
    if request.offset:
        query_params["offset"] = request.offset
    if request.sort_by:
        query_params["sort_by"] = request.sort_by
    if request.sort_order:
        query_params["sort_order"] = request.sort_order

    # Execute query using ChatState's built-in query method
    result = chat_state.query(query_params)

    # Convert message dicts back to ChatMessage objects for response
    messages = [
        ChatMessage(
            message_id=msg["message_id"],
            conversation_id=msg["conversation_id"],
            role=msg["role"],
            content=msg["content"],
            timestamp=datetime.fromisoformat(msg["timestamp"]),
            metadata=msg.get("metadata", {}),
        )
        for msg in result["messages"]
    ]

    return ChatQueryResponse(
        messages=messages,
        total_count=result["total_count"],
        returned_count=result["count"],
        query=request.model_dump(exclude_none=True),
    )


@router.post("/send", response_model=ModalityActionResponse)
async def send_chat_message(
    request: SendChatMessageRequest, engine: SimulationEngineDep
) -> ModalityActionResponse:
    """Send a chat message.

    Creates an immediate event to send a message from either the user or
    assistant to the conversation history.

    Args:
        request: Message content and metadata.
        engine: The simulation engine dependency.

    Returns:
        Action response with event details.
    """
    try:
        # Convert request to event data
        event_data = {
            "operation": "send_message",
            "role": request.role,
            "content": request.content,
            "conversation_id": request.conversation_id,
            "metadata": request.metadata,
        }

        # Create and add event
        event = create_immediate_event(
            engine=engine,
            modality="chat",
            data=event_data,
            priority=100,
        )

        return ModalityActionResponse(
            event_id=event.event_id,
            scheduled_time=event.scheduled_time,
            status="executed",
            message=f"Chat message sent from {request.role}",
            modality="chat",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send chat message: {str(e)}",
        )


@router.post("/delete", response_model=ModalityActionResponse)
async def delete_chat_message(
    request: DeleteChatMessageRequest, engine: SimulationEngineDep
) -> ModalityActionResponse:
    """Delete a chat message.

    Creates an immediate event to remove a specific message from the conversation history.

    Args:
        request: Message ID to delete.
        engine: The simulation engine dependency.

    Returns:
        Action response with event details.
    """
    try:
        # Convert request to event data
        event_data = {
            "operation": "delete_message",
            "message_id": request.message_id,
        }

        # Create and add event
        event = create_immediate_event(
            engine=engine,
            modality="chat",
            data=event_data,
            priority=100,
        )

        return ModalityActionResponse(
            event_id=event.event_id,
            scheduled_time=event.scheduled_time,
            status="executed",
            message=f"Deleted message {request.message_id}",
            modality="chat",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete message: {str(e)}",
        )


@router.post("/clear", response_model=ModalityActionResponse)
async def clear_conversation(
    request: ClearChatRequest, engine: SimulationEngineDep
) -> ModalityActionResponse:
    """Clear conversation history.

    Creates an immediate event to remove all messages from a specific conversation.

    Args:
        request: Conversation ID to clear.
        engine: The simulation engine dependency.

    Returns:
        Action response with event details.
    """
    try:
        # Convert request to event data
        event_data = {
            "operation": "clear_conversation",
            "conversation_id": request.conversation_id,
        }

        # Create and add event
        event = create_immediate_event(
            engine=engine,
            modality="chat",
            data=event_data,
            priority=100,
        )

        return ModalityActionResponse(
            event_id=event.event_id,
            scheduled_time=event.scheduled_time,
            status="executed",
            message=f"Cleared conversation {request.conversation_id}",
            modality="chat",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear conversation: {str(e)}",
        )
