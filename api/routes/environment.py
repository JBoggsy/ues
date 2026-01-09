"""Environment state query endpoints.

These endpoints allow clients to query the current state of the simulated environment,
including all modality states.
"""

from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from api.dependencies import SimulationEngineDep
from api.exceptions import ModalityNotFoundError

# Create router for environment-related endpoints
router = APIRouter(
    prefix="/environment",
    tags=["environment"],
)


# Response Models


class ModalitySummary(BaseModel):
    """Summary information about a single modality.
    
    Attributes:
        modality_type: The type/name of the modality.
        state_summary: Brief summary of the current state.
    """

    modality_type: str
    state_summary: str


class EnvironmentStateResponse(BaseModel):
    """Complete environment state snapshot.
    
    Attributes:
        current_time: The current simulator time.
        modalities: Dictionary mapping modality names to their full state.
        summary: List of brief summaries for each modality.
    """

    current_time: str
    modalities: dict[str, Any] = Field(
        description="Full state for each modality (can be large)"
    )
    summary: list[ModalitySummary]


class CompactSnapshotResponse(BaseModel):
    """Compact, LLM-context-optimized environment snapshot.
    
    Attributes:
        snapshot_time: The simulator time when snapshot was taken.
        format: Always "compact" for this response type.
        modalities: Dictionary mapping modality names to their compact snapshots.
        events: Summary of pending events (if available).
    """

    snapshot_time: str
    format: Literal["compact"] = "compact"
    modalities: dict[str, Any] = Field(
        description="Compact state for each modality (LLM-optimized)"
    )
    events: dict[str, Any] | None = Field(
        default=None,
        description="Summary of pending events"
    )


class ModalityListResponse(BaseModel):
    """List of available modalities.
    
    Attributes:
        modalities: List of modality type names.
        count: Total number of modalities.
    """

    modalities: list[str]
    count: int


# Route Handlers


@router.get("/state")
async def get_environment_state(
    engine: SimulationEngineDep,
    compact: bool = Query(
        False,
        description="Return compact LLM-optimized snapshot instead of full state"
    ),
    format: Literal["json", "text"] = Query(
        "json",
        description="Output format: 'json' for structured data, 'text' for LLM-ready plain text"
    ),
):
    """Get a snapshot of the current environment state.
    
    By default, returns the full state of all modalities. Use query parameters
    to get a compact, LLM-optimized representation instead.
    
    Args:
        engine: The SimulationEngine instance (injected by FastAPI).
        compact: If True, return compact LLM-optimized snapshot instead of full state.
        format: Output format - 'json' for structured data, 'text' for plain text.
    
    Returns:
        Full or compact environment state depending on parameters:
        - Default: Full EnvironmentStateResponse with all modality data
        - compact=true, format=json: CompactSnapshotResponse with LLM-optimized data
        - compact=true, format=text: Plain text representation for direct LLM injection
    
    Examples:
        GET /environment/state
            Returns full state (potentially large)
        
        GET /environment/state?compact=true
            Returns compact JSON snapshot (~2KB vs 50KB+)
        
        GET /environment/state?compact=true&format=text
            Returns plain text suitable for LLM prompts
    """
    env = engine.environment
    
    # Handle compact snapshot requests
    if compact:
        if format == "text":
            # Return plain text for LLM injection
            text_content = env.get_compact_snapshot_text()
            return PlainTextResponse(content=text_content)
        else:
            # Return compact JSON
            snapshot = env.get_compact_snapshot()
            
            # Add event queue summary from engine
            event_summary = None
            if hasattr(engine, 'event_queue'):
                pending_events = [
                    e for e in engine.event_queue.events
                    if e.status.value == "pending"
                ]
                if pending_events:
                    next_event = min(pending_events, key=lambda e: e.scheduled_time)
                    event_summary = {
                        "pending_count": len(pending_events),
                        "next_event_time": next_event.scheduled_time.isoformat(),
                        "next_event_modality": next_event.modality,
                    }
                else:
                    event_summary = {
                        "pending_count": 0,
                        "next_event_time": None,
                        "next_event_modality": None,
                    }
            
            snapshot["events"] = event_summary
            return CompactSnapshotResponse(**snapshot)
    
    # Default: Full state response
    modalities_dict = {
        name: state.model_dump() for name, state in env.modality_states.items()
    }
    
    summaries = [
        ModalitySummary(
            modality_type=name,
            state_summary=state.summary,
        )
        for name, state in env.modality_states.items()
    ]
    
    return EnvironmentStateResponse(
        current_time=env.time_state.current_time.isoformat(),
        modalities=modalities_dict,
        summary=summaries,
    )


@router.get("/modalities", response_model=ModalityListResponse)
async def list_modalities(engine: SimulationEngineDep):
    """Get a list of all available modalities in the environment.
    
    This is a lightweight endpoint that just lists what modalities are present
    without returning their full state.
    
    Args:
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        List of modality names and the total count.
    """
    env = engine.environment
    modality_names = list(env.modality_states.keys())
    
    return ModalityListResponse(
        modalities=modality_names,
        count=len(modality_names),
    )


@router.get("/modalities/{modality_name}")
async def get_modality_state(modality_name: str, engine: SimulationEngineDep):
    """Get the current state of a specific modality.
    
    This returns just the state for one modality, which is more efficient
    than fetching the entire environment state.
    
    Args:
        modality_name: The name of the modality to query (e.g., "email", "sms").
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        The current state of the requested modality.
    
    Raises:
        ModalityNotFoundError: If the modality doesn't exist.
    """
    
    env = engine.environment
    
    if modality_name not in env.modality_states:
        raise ModalityNotFoundError(
            modality_name=modality_name,
            available_modalities=list(env.modality_states.keys()),
        )
    
    state = env.modality_states[modality_name]
    
    return {
        "modality_type": modality_name,
        "current_time": env.time_state.current_time.isoformat(),
        "state": state.model_dump(),
    }


class ValidationResponse(BaseModel):
    """Response model for environment validation.
    
    Attributes:
        valid: Whether the environment is in a valid state.
        errors: List of validation error messages (empty if valid).
        checked_at: Timestamp when validation was performed.
    """

    valid: bool
    errors: list[str] = Field(default_factory=list)
    checked_at: datetime


@router.post("/validate", response_model=ValidationResponse)
async def validate_environment(engine: SimulationEngineDep):
    """Validate the current environment state for consistency.
    
    Checks all modalities for internal consistency and cross-modality
    integrity issues.
    
    Args:
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        Validation results with any errors found.
    """
    errors = engine.validate()
    
    return ValidationResponse(
        valid=len(errors) == 0,
        errors=errors,
        checked_at=engine.environment.time_state.current_time,
    )


@router.post("/modalities/{modality_name}/query")
async def query_modality(modality_name: str, query_params: dict[str, Any], engine: SimulationEngineDep):
    """Query a modality's state with filters.
    
    This endpoint allows modality-specific queries with custom filter parameters.
    The query format varies by modality type - see REST API documentation for details.
    
    Args:
        modality_name: The name of the modality to query.
        query_params: Dictionary of query parameters (modality-specific).
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        Filtered query results from the modality.
    
    Raises:
        ModalityNotFoundError: If the modality doesn't exist.
    
    Query Parameters by Modality:
    
    Email:
        - folder: Filter by folder name
        - label: Filter by label
        - is_read: Filter by read status (bool)
        - is_starred: Filter by starred status (bool)
        - has_attachments: Filter by attachment presence (bool)
        - from_address: Filter by sender
        - to_address: Filter by recipient
        - subject_contains: Search subject
        - body_contains: Search body
        - date_from: Start of date range (datetime)
        - date_to: End of date range (datetime)
        - thread_id: Get specific thread
        - limit: Max results
        - offset: Pagination offset
        - sort_by: Sort field ("date", "from", "subject")
        - sort_order: Sort order ("asc", "desc")
    
    Calendar:
        - calendar_ids: List of calendar IDs to filter
        - start: Start date/datetime for range
        - end: End date/datetime for range
        - expand_recurring: Generate individual occurrences (bool)
        - status: Filter by status ("confirmed", "tentative", "cancelled")
        - has_attendees: Filter by attendee presence (bool)
        - recurring: Filter by recurring vs one-time (bool)
        - search: Search title/description/location
        - color: Filter by event color
        - limit: Max results
    
    SMS:
        - thread_id: Filter messages by conversation thread
        - phone_number: Filter messages involving this phone number
        - direction: Filter by "incoming" or "outgoing"
        - message_type: Filter by "sms" or "rcs"
        - is_read: Filter by read status (bool)
        - has_attachments: Filter messages with attachments (bool)
        - search_text: Search message body text (case-insensitive)
        - since: Filter messages sent after this time (datetime)
        - until: Filter messages sent before this time (datetime)
        - limit: Maximum number of messages to return
    
    Chat:
        - conversation_id: Filter by conversation
        - role: Filter by role ("user", "assistant")
        - since: Messages after this time (datetime)
        - until: Messages before this time (datetime)
        - search: Search message content
        - limit: Max results
    
    Weather:
        - lat: Latitude (required)
        - lon: Longitude (required)
        - exclude: Comma-delimited list of parts to exclude
        - units: "standard", "metric", or "imperial"
        - from: Unix timestamp - return all reports since this time
        - to: Unix timestamp - return reports until this time
        - real: Query OpenWeather API for real data (bool)
    
    Location:
        - since: Start of time range (datetime)
        - until: End of time range (datetime)
        - named_location: Filter by location name
        - limit: Max results
    
    Time:
        - since: Start of time range (datetime)
        - until: End of time range (datetime)
        - timezone: Filter by specific timezone
        - limit: Max results
    """
    env = engine.environment
    
    if modality_name not in env.modality_states:
        raise ModalityNotFoundError(
            modality_name=modality_name,
            available_modalities=list(env.modality_states.keys()),
        )
    
    state = env.modality_states[modality_name]
    
    # Call the state's query method if it exists
    if hasattr(state, 'query'):
        try:
            results = state.query(query_params)
            
            # All modality query methods now return dict[str, Any]
            return {
                "modality_type": modality_name,
                "query": query_params,
                "results": results,
            }
        except Exception as e:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail=f"Query failed for {modality_name}: {str(e)}",
            )
    else:
        # Fallback for modalities without query methods
        return {
            "modality_type": modality_name,
            "query": query_params,
            "results": state.model_dump(),
            "message": f"{modality_name} modality does not support custom queries - full state returned",
        }
