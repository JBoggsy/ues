"""Events management sub-client for the UES API.

This module provides EventsClient and AsyncEventsClient for interacting
with the event management endpoints (/events/*).

This is an internal module. Import from `client` instead.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from client._base import AsyncBaseClient, BaseClient

if TYPE_CHECKING:
    from client._http import AsyncHTTPClient, HTTPClient


# Response models for events endpoints


class EventResponse(BaseModel):
    """Response model for event details.
    
    Attributes:
        event_id: Unique event identifier.
        scheduled_time: When the event is/was scheduled to execute.
        modality: Which modality the event affects.
        status: Current execution status.
        priority: Execution priority.
        created_at: When the event was created.
        executed_at: When the event was executed (if applicable).
        error_message: Error details if execution failed.
        data: The event payload (ModalityInput data).
    """

    event_id: str
    scheduled_time: datetime
    modality: str
    status: str
    priority: int
    created_at: datetime
    executed_at: datetime | None = None
    error_message: str | None = None
    data: dict[str, Any] | None = None


class EventListResponse(BaseModel):
    """Response model for event listing.
    
    Attributes:
        events: List of event summaries.
        total: Total number of events matching filters (before pagination).
        pending: Count of pending events in queue.
        executed: Count of executed events in queue.
        failed: Count of failed events in queue.
        skipped: Count of skipped events in queue.
    """

    events: list[EventResponse]
    total: int
    pending: int
    executed: int
    failed: int
    skipped: int


class EventSummaryResponse(BaseModel):
    """Response model for event statistics.
    
    Attributes:
        total: Total number of events.
        pending: Count of pending events.
        executed: Count of executed events.
        failed: Count of failed events.
        skipped: Count of skipped events.
        by_modality: Event counts grouped by modality.
        next_event_time: Scheduled time of next pending event.
    """

    total: int
    pending: int
    executed: int
    failed: int
    skipped: int
    by_modality: dict[str, int]
    next_event_time: datetime | None = None


class CancelEventResponse(BaseModel):
    """Response model for event cancellation.
    
    Attributes:
        cancelled: Whether the event was successfully cancelled.
        event_id: The ID of the cancelled event.
    """

    cancelled: bool
    event_id: str


def _filter_none_params(**params: Any) -> dict[str, Any]:
    """Filter out None values from parameters dict."""
    return {k: v for k, v in params.items() if v is not None}


# Synchronous EventsClient


class EventsClient(BaseClient):
    """Synchronous client for event management endpoints (/events/*).
    
    This client provides methods for creating, querying, and managing
    simulation events.
    
    Example:
        with UESClient() as client:
            # Create a scheduled event
            event = client.events.create(
                scheduled_time=datetime(2024, 3, 15, 10, 0, tzinfo=timezone.utc),
                modality="email",
                data={"action": "receive", "from_address": "sender@example.com", ...},
            )
            
            # List pending events
            events = client.events.list_events(status="pending")
            print(f"Pending events: {events.pending}")
            
            # Get event summary
            summary = client.events.summary()
            print(f"Total events: {summary.total}")
    """

    _BASE_PATH = "/events"

    def list_events(
        self,
        status: str | None = None,
        modality: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> EventListResponse:
        """List events with optional filters.
        
        Query parameters allow filtering by status, time range, and modality.
        
        Args:
            status: Filter by event status ("pending", "executed", "failed", 
                "skipped", "cancelled").
            modality: Filter by modality type (e.g., "email", "sms").
            start_time: Filter by scheduled_time >= start_time.
            end_time: Filter by scheduled_time <= end_time.
            limit: Maximum number of events to return.
            offset: Number of events to skip (for pagination).
        
        Returns:
            List of events matching the filters with status counts.
        
        Raises:
            ValidationError: If status value is invalid.
            APIError: If the request fails.
        """
        params = _filter_none_params(
            status=status,
            modality=modality,
            start_time=start_time.isoformat() if start_time else None,
            end_time=end_time.isoformat() if end_time else None,
            limit=limit,
            offset=offset if offset != 0 else None,
        )
        data = self._get(self._BASE_PATH, params=params)
        return EventListResponse(**data)

    def create(
        self,
        scheduled_time: datetime,
        modality: str,
        data: dict[str, Any],
        priority: int = 50,
        metadata: dict[str, Any] | None = None,
        agent_id: str | None = None,
    ) -> EventResponse:
        """Create a new scheduled event.
        
        The event will be added to the queue and executed when simulator
        time reaches the scheduled_time.
        
        Args:
            scheduled_time: When the event should execute.
            modality: Which modality this event affects (e.g., "email", "sms").
            data: The ModalityInput payload for this event.
            priority: Execution priority (0-100, higher = executed first).
            metadata: Optional custom metadata.
            agent_id: Optional ID of agent creating this event.
        
        Returns:
            The created event details.
        
        Raises:
            ConflictError: If scheduled_time is in the past.
            NotFoundError: If modality is unknown.
            ValidationError: If data is invalid for the modality.
            APIError: If the request fails.
        """
        json_body: dict[str, Any] = {
            "scheduled_time": scheduled_time.isoformat(),
            "modality": modality,
            "data": data,
            "priority": priority,
        }
        if metadata is not None:
            json_body["metadata"] = metadata
        if agent_id is not None:
            json_body["agent_id"] = agent_id
        
        response = self._post(self._BASE_PATH, json=json_body)
        return EventResponse(**response)

    def create_immediate(
        self,
        modality: str,
        data: dict[str, Any],
    ) -> EventResponse:
        """Submit an event for immediate execution.
        
        This is a convenience method that creates an event scheduled
        at the current simulator time with high priority.
        
        Args:
            modality: Which modality this event affects.
            data: The ModalityInput payload for this event.
        
        Returns:
            The created event details.
        
        Raises:
            NotFoundError: If modality is unknown.
            ValidationError: If data is invalid for the modality.
            APIError: If the request fails.
        """
        json_body = {
            "modality": modality,
            "data": data,
        }
        response = self._post(f"{self._BASE_PATH}/immediate", json=json_body)
        return EventResponse(**response)

    def get(self, event_id: str) -> EventResponse:
        """Get details for a specific event.
        
        Args:
            event_id: The unique event identifier.
        
        Returns:
            Full event details including the event data payload.
        
        Raises:
            NotFoundError: If event is not found.
            APIError: If the request fails.
        """
        data = self._get(f"{self._BASE_PATH}/{event_id}")
        return EventResponse(**data)

    def cancel(self, event_id: str) -> CancelEventResponse:
        """Cancel a pending event.
        
        Only pending events can be cancelled. Executed or failed events
        cannot be cancelled.
        
        Args:
            event_id: The unique event identifier.
        
        Returns:
            Confirmation of cancellation.
        
        Raises:
            NotFoundError: If event is not found.
            ValidationError: If event cannot be cancelled (not pending).
            APIError: If the request fails.
        """
        data = self._delete(f"{self._BASE_PATH}/{event_id}")
        return CancelEventResponse(**data)

    def next(self) -> EventResponse | None:
        """Peek at the next pending event without executing it.
        
        Returns the next event that will be executed when time advances.
        
        Returns:
            Next pending event details, or None if no pending events.
        
        Raises:
            APIError: If the request fails (other than 404).
        """
        from client.exceptions import NotFoundError
        
        try:
            data = self._get(f"{self._BASE_PATH}/next")
            return EventResponse(**data)
        except NotFoundError:
            return None

    def summary(self) -> EventSummaryResponse:
        """Get event execution statistics.
        
        Provides counts and statistics about events in the simulation.
        
        Returns:
            Event summary statistics including counts by status and modality.
        
        Raises:
            APIError: If the request fails.
        """
        data = self._get(f"{self._BASE_PATH}/summary")
        return EventSummaryResponse(**data)


# Asynchronous AsyncEventsClient


class AsyncEventsClient(AsyncBaseClient):
    """Asynchronous client for event management endpoints (/events/*).
    
    This client provides async methods for creating, querying, and managing
    simulation events.
    
    Example:
        async with AsyncUESClient() as client:
            # Create a scheduled event
            event = await client.events.create(
                scheduled_time=datetime(2024, 3, 15, 10, 0, tzinfo=timezone.utc),
                modality="email",
                data={"action": "receive", "from_address": "sender@example.com", ...},
            )
            
            # List pending events
            events = await client.events.list_events(status="pending")
            print(f"Pending events: {events.pending}")
            
            # Get event summary
            summary = await client.events.summary()
            print(f"Total events: {summary.total}")
    """

    _BASE_PATH = "/events"

    async def list_events(
        self,
        status: str | None = None,
        modality: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> EventListResponse:
        """List events with optional filters.
        
        Query parameters allow filtering by status, time range, and modality.
        
        Args:
            status: Filter by event status ("pending", "executed", "failed", 
                "skipped", "cancelled").
            modality: Filter by modality type (e.g., "email", "sms").
            start_time: Filter by scheduled_time >= start_time.
            end_time: Filter by scheduled_time <= end_time.
            limit: Maximum number of events to return.
            offset: Number of events to skip (for pagination).
        
        Returns:
            List of events matching the filters with status counts.
        
        Raises:
            ValidationError: If status value is invalid.
            APIError: If the request fails.
        """
        params = _filter_none_params(
            status=status,
            modality=modality,
            start_time=start_time.isoformat() if start_time else None,
            end_time=end_time.isoformat() if end_time else None,
            limit=limit,
            offset=offset if offset != 0 else None,
        )
        data = await self._get(self._BASE_PATH, params=params)
        return EventListResponse(**data)

    async def create(
        self,
        scheduled_time: datetime,
        modality: str,
        data: dict[str, Any],
        priority: int = 50,
        metadata: dict[str, Any] | None = None,
        agent_id: str | None = None,
    ) -> EventResponse:
        """Create a new scheduled event.
        
        The event will be added to the queue and executed when simulator
        time reaches the scheduled_time.
        
        Args:
            scheduled_time: When the event should execute.
            modality: Which modality this event affects (e.g., "email", "sms").
            data: The ModalityInput payload for this event.
            priority: Execution priority (0-100, higher = executed first).
            metadata: Optional custom metadata.
            agent_id: Optional ID of agent creating this event.
        
        Returns:
            The created event details.
        
        Raises:
            ConflictError: If scheduled_time is in the past.
            NotFoundError: If modality is unknown.
            ValidationError: If data is invalid for the modality.
            APIError: If the request fails.
        """
        json_body: dict[str, Any] = {
            "scheduled_time": scheduled_time.isoformat(),
            "modality": modality,
            "data": data,
            "priority": priority,
        }
        if metadata is not None:
            json_body["metadata"] = metadata
        if agent_id is not None:
            json_body["agent_id"] = agent_id
        
        response = await self._post(self._BASE_PATH, json=json_body)
        return EventResponse(**response)

    async def create_immediate(
        self,
        modality: str,
        data: dict[str, Any],
    ) -> EventResponse:
        """Submit an event for immediate execution.
        
        This is a convenience method that creates an event scheduled
        at the current simulator time with high priority.
        
        Args:
            modality: Which modality this event affects.
            data: The ModalityInput payload for this event.
        
        Returns:
            The created event details.
        
        Raises:
            NotFoundError: If modality is unknown.
            ValidationError: If data is invalid for the modality.
            APIError: If the request fails.
        """
        json_body = {
            "modality": modality,
            "data": data,
        }
        response = await self._post(f"{self._BASE_PATH}/immediate", json=json_body)
        return EventResponse(**response)

    async def get(self, event_id: str) -> EventResponse:
        """Get details for a specific event.
        
        Args:
            event_id: The unique event identifier.
        
        Returns:
            Full event details including the event data payload.
        
        Raises:
            NotFoundError: If event is not found.
            APIError: If the request fails.
        """
        data = await self._get(f"{self._BASE_PATH}/{event_id}")
        return EventResponse(**data)

    async def cancel(self, event_id: str) -> CancelEventResponse:
        """Cancel a pending event.
        
        Only pending events can be cancelled. Executed or failed events
        cannot be cancelled.
        
        Args:
            event_id: The unique event identifier.
        
        Returns:
            Confirmation of cancellation.
        
        Raises:
            NotFoundError: If event is not found.
            ValidationError: If event cannot be cancelled (not pending).
            APIError: If the request fails.
        """
        data = await self._delete(f"{self._BASE_PATH}/{event_id}")
        return CancelEventResponse(**data)

    async def next(self) -> EventResponse | None:
        """Peek at the next pending event without executing it.
        
        Returns the next event that will be executed when time advances.
        
        Returns:
            Next pending event details, or None if no pending events.
        
        Raises:
            APIError: If the request fails (other than 404).
        """
        from client.exceptions import NotFoundError
        
        try:
            data = await self._get(f"{self._BASE_PATH}/next")
            return EventResponse(**data)
        except NotFoundError:
            return None

    async def summary(self) -> EventSummaryResponse:
        """Get event execution statistics.
        
        Provides counts and statistics about events in the simulation.
        
        Returns:
            Event summary statistics including counts by status and modality.
        
        Raises:
            APIError: If the request fails.
        """
        data = await self._get(f"{self._BASE_PATH}/summary")
        return EventSummaryResponse(**data)
