"""Environment state query endpoints.

These endpoints allow clients to query the current state of the simulated environment,
including all modality states.
"""

from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from ues.api.dependencies import SimulationEngineDep
from ues.api.exceptions import ModalityNotFoundError

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
    # Use model_dump() for complete, unabridged state
    modalities_dict = {
        name: state.model_dump(mode="json") for name, state in env.modality_states.items()
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
