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


# ===== Scenario Export/Import Models =====
# These models are used by the scenario save/load API endpoints

class HistoricEventHandling(str):
    """Valid options for handling historic events during environment load.
    
    - ignore: Leave events in queue (they will never execute)
    - delete: Remove historic events from queue
    - apply: Execute historic events immediately against loaded state
    """
    IGNORE = "ignore"
    DELETE = "delete"
    APPLY = "apply"


# --- Exported Data Structure Models ---
# These model the structure of exported environment/event data

class ExportedTimeState(BaseModel):
    """Serialized simulator time state.
    
    Represents the time_state portion of an exported environment.
    This model captures the structure from SimulatorTime.model_dump(mode="json").
    """
    current_time: datetime = Field(description="Current simulator time")
    time_scale: float = Field(description="Time multiplier for auto-advance")
    is_paused: bool = Field(description="Whether simulation is paused")
    auto_advance: bool = Field(description="Whether auto-advance is enabled")
    last_wall_time_update: datetime = Field(description="Last wall-clock update time")


class ExportedEnvironmentData(BaseModel):
    """Structure of exported environment data.
    
    This matches the output of Environment.to_scenario_dict().
    """
    time_state: ExportedTimeState = Field(
        description="Serialized SimulatorTime state"
    )
    modality_states: dict[str, dict[str, Any]] = Field(
        description="Dict mapping modality_type to serialized state data"
    )


class ExportedEventQueueData(BaseModel):
    """Structure of exported event queue data.
    
    This matches the output of EventQueue.to_scenario_dict().
    """
    events: list[dict[str, Any]] = Field(
        description="List of serialized SimulatorEvent dictionaries"
    )


class ScenarioMetadataModel(BaseModel):
    """Metadata for a saved scenario (API representation).
    
    This mirrors models.scenario.ScenarioMetadata for API responses.
    """
    ues_version: str = Field(description="UES version that created this scenario")
    scenario_version: str = Field(description="Schema version for file format")
    created_at: datetime = Field(description="When scenario was created (UTC)")
    author: str | None = Field(default=None, description="Author name or identifier")
    description: str | None = Field(default=None, description="Human-readable description")


class ExportedScenarioData(BaseModel):
    """Complete scenario structure for export.
    
    This matches the structure of models.scenario.Scenario.
    """
    metadata: ScenarioMetadataModel = Field(description="Scenario metadata")
    environment: ExportedEnvironmentData = Field(description="Serialized environment")
    events: ExportedEventQueueData = Field(description="Serialized event queue")


# --- Export Response Models ---


class ExportEnvironmentResponse(BaseModel):
    """Response for environment export endpoint.
    
    Returns the exported environment data along with summary information
    about what was exported.
    """
    environment: ExportedEnvironmentData = Field(
        description="Serialized environment data"
    )
    modalities_exported: list[str] = Field(
        description="List of modality types included in export"
    )


class ExportEventsResponse(BaseModel):
    """Response for event queue export endpoint.
    
    Returns the exported event queue along with summary statistics.
    """
    events: ExportedEventQueueData = Field(
        description="Serialized event queue data"
    )
    total_events: int = Field(
        ge=0,
        description="Total number of events exported"
    )
    pending_events: int = Field(
        ge=0,
        description="Number of pending events"
    )
    executed_events: int = Field(
        ge=0,
        description="Number of executed events"
    )


class ExportScenarioResponse(BaseModel):
    """Response for full scenario export endpoint.
    
    Returns the complete scenario with metadata, environment, and events.
    """
    scenario: ExportedScenarioData = Field(
        description="Complete serialized scenario with metadata"
    )


# --- Import Request Models ---


class LoadEnvironmentRequest(BaseModel):
    """Request body for importing an environment.
    
    The data field should contain the output from export_environment()
    or Environment.to_scenario_dict().
    """
    data: ExportedEnvironmentData = Field(
        description="Environment data to load (from export)"
    )
    historic_event_handling: str = Field(
        default="ignore",
        pattern="^(ignore|delete|apply)$",
        description=(
            "How to handle existing events scheduled before the loaded environment's time: "
            "'ignore' (leave in queue, will never execute), "
            "'delete' (remove from queue), "
            "'apply' (execute immediately against loaded state)"
        )
    )
    strict_modalities: bool = Field(
        default=False,
        description=(
            "If True, raise error on unknown modality types. "
            "If False, skip unknown modalities and include in warnings."
        )
    )


class LoadEventsRequest(BaseModel):
    """Request body for importing events.
    
    The data field should contain the output from export_event_queue()
    or EventQueue.to_scenario_dict().
    """
    data: ExportedEventQueueData = Field(
        description="Event queue data to load (from export)"
    )
    merge: bool = Field(
        default=False,
        description=(
            "If True, add loaded events to existing queue. "
            "If False, replace all events."
        )
    )


class LoadScenarioRequest(BaseModel):
    """Request body for importing a full scenario.
    
    The scenario field should contain the output from export_scenario()
    or Scenario.to_dict().
    """
    scenario: ExportedScenarioData = Field(
        description="Complete scenario data to load"
    )
    strict_modalities: bool = Field(
        default=False,
        description=(
            "If True, raise error on unknown modality types. "
            "If False, skip unknown modalities and include in warnings."
        )
    )


# --- Import Response Models ---


class LoadEnvironmentResponse(BaseModel):
    """Response for environment import endpoint.
    
    Returns detailed information about what was loaded and any issues.
    """
    success: bool = Field(
        description="Whether the load operation succeeded"
    )
    modalities_loaded: list[str] = Field(
        description="List of modality types that were successfully loaded"
    )
    modalities_skipped: list[str] = Field(
        description="List of modality types that were skipped (unknown types)"
    )
    warnings: list[str] = Field(
        description="Warning messages about the load operation"
    )
    historic_events_count: int = Field(
        ge=0,
        description="Number of existing events scheduled before loaded environment time"
    )
    historic_events_action: str = Field(
        description="How historic events were handled ('ignore', 'delete', or 'apply')"
    )


class LoadEventsResponse(BaseModel):
    """Response for event queue import endpoint.
    
    Returns detailed information about what was loaded.
    """
    success: bool = Field(
        description="Whether the load operation succeeded"
    )
    events_loaded: int = Field(
        ge=0,
        description="Total number of events in the loaded data"
    )
    events_merged: int = Field(
        ge=0,
        description="Number of events actually added (when merge=True)"
    )
    previous_events: int = Field(
        ge=0,
        description="Number of events in queue before load"
    )
    historic_events_warning: bool = Field(
        description="True if any loaded events are scheduled before current time"
    )
    historic_event_count: int = Field(
        ge=0,
        description="Number of events scheduled before current simulator time"
    )


class LoadedScenarioMetadata(BaseModel):
    """Summary of loaded scenario metadata.
    
    Returned as part of LoadScenarioResponse to confirm what was loaded.
    """
    ues_version: str = Field(description="UES version from loaded scenario")
    scenario_version: str = Field(description="Schema version from loaded scenario")
    created_at: str = Field(description="When scenario was created (ISO format)")
    author: str | None = Field(default=None, description="Author from loaded scenario")
    description: str | None = Field(default=None, description="Description from loaded scenario")


class LoadScenarioResponse(BaseModel):
    """Response for full scenario import endpoint.
    
    Returns comprehensive information about the loaded scenario.
    """
    success: bool = Field(
        description="Whether the load operation succeeded"
    )
    environment_loaded: bool = Field(
        description="Whether environment was successfully loaded"
    )
    events_loaded: int = Field(
        ge=0,
        description="Number of events loaded from scenario"
    )
    modalities_loaded: list[str] = Field(
        description="List of modality types that were successfully loaded"
    )
    modalities_skipped: list[str] = Field(
        description="List of modality types that were skipped (unknown types)"
    )
    warnings: list[str] = Field(
        description="Warning messages about the load operation"
    )
    scenario_metadata: LoadedScenarioMetadata = Field(
        description="Metadata from the loaded scenario"
    )
