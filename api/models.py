"""Shared request and response models for API endpoints.

This module contains base classes and common models used across multiple
modality route handlers to reduce code duplication while maintaining type safety.
"""

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field


# Generic type variable for state data
StateT = TypeVar("StateT")


class ModalityStateResponse(BaseModel, Generic[StateT]):
    """Base response model for modality state endpoints.
    
    This generic model provides a consistent structure for all modality
    state responses while allowing type-safe state data.
    
    Attributes:
        modality_type: The type of modality (e.g., "email", "sms", "chat").
        current_time: The current simulator time when state was retrieved.
        state: The modality-specific state data.
    """

    modality_type: str
    current_time: datetime
    state: StateT


class ModalityActionResponse(BaseModel):
    """Base response model for modality action endpoints.
    
    This model provides a consistent structure for all modality action
    responses (send, receive, update, delete, etc.).
    
    Attributes:
        event_id: The ID of the event created by this action.
        scheduled_time: When the event was/will be executed.
        status: The current status of the event.
        message: Human-readable message describing the result.
        modality: The modality type that was acted upon.
    """

    event_id: str
    scheduled_time: datetime
    status: str
    message: str
    modality: str


class ModalityQueryResponse(BaseModel, Generic[StateT]):
    """Base response model for modality query endpoints.
    
    This generic model provides a consistent structure for all modality
    query responses while allowing type-safe result data.
    
    Attributes:
        modality_type: The type of modality queried.
        query: Echo of the query parameters sent (for debugging).
        results: The query results (type varies by modality).
        total_count: Total number of results matching the query.
        returned_count: Number of results returned (after pagination).
    """

    modality_type: str
    query: dict[str, Any]
    results: StateT
    total_count: int
    returned_count: int


# Common query filter models


class PaginationParams(BaseModel):
    """Common pagination parameters for query endpoints.
    
    Attributes:
        limit: Maximum number of results to return.
        offset: Number of results to skip (for pagination).
    """

    limit: int | None = Field(None, ge=1, le=1000, description="Maximum results to return")
    offset: int = Field(0, ge=0, description="Number of results to skip")


class SortParams(BaseModel):
    """Common sorting parameters for query endpoints.
    
    Attributes:
        sort_by: Field name to sort by.
        sort_order: Sort direction ("asc" or "desc").
    """

    sort_by: str | None = None
    sort_order: str | None = Field(None, pattern="^(asc|desc)$")


class DateRangeParams(BaseModel):
    """Common date range filter parameters.
    
    Attributes:
        start_date: Start of date range (inclusive).
        end_date: End of date range (inclusive).
    """

    start_date: datetime | None = None
    end_date: datetime | None = None


class TextSearchParams(BaseModel):
    """Common text search parameters.
    
    Attributes:
        search_text: Text to search for (case-insensitive).
        search_fields: Optional list of fields to search in.
    """

    search_text: str | None = None
    search_fields: list[str] | None = None


# Common request models for marking/flagging


class MarkItemsRequest(BaseModel):
    """Request model for marking items (read/unread, starred, etc.).
    
    This is a common pattern across email, SMS, and other modalities.
    
    Attributes:
        item_ids: List of item IDs to mark.
        mark_value: The value to set (True to mark, False to unmark).
    """

    item_ids: list[str] = Field(..., min_length=1, description="IDs of items to mark")
    mark_value: bool = Field(..., description="True to mark, False to unmark")


class DeleteItemsRequest(BaseModel):
    """Request model for deleting items.
    
    This is a common pattern across email, SMS, calendar, and other modalities.
    
    Attributes:
        item_ids: List of item IDs to delete.
        permanent: Whether to permanently delete (true) or move to trash (false).
    """

    item_ids: list[str] = Field(..., min_length=1, description="IDs of items to delete")
    permanent: bool = Field(False, description="True for permanent deletion")


# Error response models


class ErrorResponse(BaseModel):
    """Standard error response model.
    
    Attributes:
        error: Error type or code.
        message: Human-readable error message.
        details: Optional additional error details.
    """

    error: str
    message: str
    details: dict[str, Any] | None = None
