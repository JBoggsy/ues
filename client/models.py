"""Client response models for the UES API client.

This module re-exports commonly used models from the API layer and defines
client-specific response models that don't exist in the API layer.
"""

from typing import Any, TypeVar

from pydantic import BaseModel, Field

# Re-export common models from API layer for client convenience
from api.models import (
    DateRangeParams,
    DeleteItemsRequest,
    ErrorResponse,
    MarkItemsRequest,
    ModalityActionResponse,
    ModalityQueryResponse,
    ModalityStateResponse,
    PaginationParams,
    SortParams,
    TextSearchParams,
)

# Type variable for generic response types
StateT = TypeVar("StateT")

__all__ = [
    # Re-exported from api.models
    "DateRangeParams",
    "DeleteItemsRequest",
    "ErrorResponse",
    "MarkItemsRequest",
    "ModalityActionResponse",
    "ModalityQueryResponse",
    "ModalityStateResponse",
    "PaginationParams",
    "SortParams",
    "TextSearchParams",
    # Client-specific models
    "CancelEventResponse",
    "EventSummaryResponse",
    "HealthResponse",
    "SimulationStatusResponse",
]


# Client-specific response models


class CancelEventResponse(BaseModel):
    """Response model for event cancellation.
    
    Attributes:
        cancelled: Whether the event was successfully cancelled.
        event_id: The ID of the cancelled event.
    """

    cancelled: bool = Field(..., description="Whether the event was cancelled")
    event_id: str = Field(..., description="ID of the cancelled event")


class EventSummaryResponse(BaseModel):
    """Response model for event queue summary.
    
    Attributes:
        total_events: Total number of events in the queue.
        pending_count: Number of pending events.
        executed_count: Number of executed events.
        failed_count: Number of failed events.
        cancelled_count: Number of cancelled events.
        skipped_count: Number of skipped events.
        next_event_time: Timestamp of the next pending event, if any.
    """

    total_events: int = Field(..., description="Total number of events")
    pending_count: int = Field(..., description="Number of pending events")
    executed_count: int = Field(..., description="Number of executed events")
    failed_count: int = Field(..., description="Number of failed events")
    cancelled_count: int = Field(..., description="Number of cancelled events")
    skipped_count: int = Field(..., description="Number of skipped events")
    next_event_time: str | None = Field(None, description="Next pending event time")


class HealthResponse(BaseModel):
    """Response model for API health check.
    
    Attributes:
        status: Health status ("healthy", "degraded", "unhealthy").
        version: API version string.
        uptime_seconds: Server uptime in seconds, if available.
    """

    status: str = Field(..., description="Health status")
    version: str | None = Field(None, description="API version")
    uptime_seconds: float | None = Field(None, description="Server uptime")


class SimulationStatusResponse(BaseModel):
    """Response model for simulation status.
    
    Attributes:
        running: Whether the simulation is currently running.
        paused: Whether the simulation is paused.
        current_time: Current simulator time as ISO string.
        time_scale: Current time scale factor.
        events_processed: Number of events processed so far.
    """

    running: bool = Field(..., description="Whether simulation is running")
    paused: bool = Field(False, description="Whether simulation is paused")
    current_time: str = Field(..., description="Current simulator time")
    time_scale: float = Field(1.0, description="Time scale factor")
    events_processed: int = Field(0, description="Events processed count")
