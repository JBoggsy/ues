"""Modality-specific convenience endpoints.

These high-level endpoints provide simplified submission interfaces for each modality,
making it easier for AI agents to interact with the simulation.
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.dependencies import SimulationEngineDep
from api.exceptions import ModalityNotFoundError
from models.event import SimulatorEvent

# Create router for modality convenience endpoints
router = APIRouter(
    prefix="/modalities",
    tags=["modalities"],
)


# Response Models


class ModalitySubmitResponse(BaseModel):
    """Response model for modality submission.
    
    Attributes:
        event_id: ID of the created event.
        scheduled_time: When the event will/did execute.
        status: Current event status.
        modality_state: Updated state of the modality.
    """

    event_id: str
    scheduled_time: datetime
    status: str
    modality_state: dict[str, Any]


# Route Handlers


@router.post("/{modality_name}/submit", response_model=ModalitySubmitResponse)
async def submit_to_modality(
    modality_name: str,
    data: dict[str, Any],
    engine: SimulationEngineDep,
):
    """Submit an action to a specific modality for immediate execution.
    
    This is the highest-level convenience endpoint for modality interactions.
    Just provide the modality name and action-specific data, and the endpoint
    will create and execute an immediate event.
    
    Args:
        modality_name: The name of the modality to interact with.
        data: The action-specific data (varies by modality).
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        Event details and updated modality state.
    
    Raises:
        HTTPException: If modality not found or submission fails.
    
    Examples:
        Chat submission:
        {
            "role": "assistant",
            "content": "Hello! How can I help you?"
        }
        
        Email submission:
        {
            "operation": "send",
            "to_addresses": ["user@example.com"],
            "subject": "Test",
            "body_text": "Hello"
        }
        
        SMS submission:
        {
            "action": "send_message",
            "message_data": {
                "to_numbers": ["+15551234567"],
                "body": "Hello!"
            }
        }
    """
    # Verify modality exists
    if modality_name not in engine.environment.modality_states:
        raise ModalityNotFoundError(
            modality_name=modality_name,
            available_modalities=list(engine.environment.modality_states.keys()),
        )
    
    try:
        current_time = engine.environment.time_state.current_time
        
        # Create immediate event with high priority
        event = SimulatorEvent(
            scheduled_time=current_time,
            modality=modality_name,
            data=data,
            priority=100,
            created_at=current_time,
        )
        
        # Add to simulation
        engine.add_event(event)
        
        # Get updated modality state
        state = engine.environment.modality_states[modality_name]
        
        return ModalitySubmitResponse(
            event_id=event.event_id,
            scheduled_time=event.scheduled_time,
            status=event.status.value,
            modality_state=state.model_dump(),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid data for {modality_name}: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit to {modality_name}: {str(e)}",
        )


# Modality-specific typed endpoints can be added here for better validation
# For example:


@router.post("/chat/submit", response_model=ModalitySubmitResponse)
async def submit_chat_message(
    role: str,
    content: str | dict[str, Any],
    conversation_id: str = "default",
    engine: SimulationEngineDep = None,
):
    """Submit a chat message for immediate execution.
    
    This is a typed convenience endpoint specifically for chat interactions.
    
    Args:
        role: Message role ("user", "assistant", or "system").
        content: Message content (text string or multimodal dict).
        conversation_id: ID of the conversation (default: "default").
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        Event details and updated chat state.
    """
    data = {
        "role": role,
        "content": content,
        "conversation_id": conversation_id,
    }
    
    return await submit_to_modality("chat", data, engine)


@router.post("/email/submit", response_model=ModalitySubmitResponse)
async def submit_email_action(
    operation: str,
    data: dict[str, Any],
    engine: SimulationEngineDep = None,
):
    """Submit an email action for immediate execution.
    
    This is a typed convenience endpoint specifically for email operations.
    
    Args:
        operation: Email operation ("receive", "send", "mark_read", etc.).
        data: Operation-specific data.
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        Event details and updated email state.
    
    Examples:
        Send email:
        {
            "operation": "send",
            "data": {
                "to_addresses": ["user@example.com"],
                "subject": "Test",
                "body_text": "Hello"
            }
        }
    """
    email_data = {"operation": operation, **data}
    return await submit_to_modality("email", email_data, engine)


@router.post("/sms/submit", response_model=ModalitySubmitResponse)
async def submit_sms_action(
    action: str,
    message_data: dict[str, Any],
    engine: SimulationEngineDep = None,
):
    """Submit an SMS action for immediate execution.
    
    This is a typed convenience endpoint specifically for SMS operations.
    
    Args:
        action: SMS action ("send_message", "mark_read", etc.).
        message_data: Action-specific data.
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        Event details and updated SMS state.
    
    Examples:
        Send message:
        {
            "action": "send_message",
            "message_data": {
                "to_numbers": ["+15551234567"],
                "body": "Hello!"
            }
        }
    """
    sms_data = {"action": action, "message_data": message_data}
    return await submit_to_modality("sms", sms_data, engine)


@router.post("/location/submit", response_model=ModalitySubmitResponse)
async def submit_location_update(
    latitude: float,
    longitude: float,
    altitude: float | None = None,
    accuracy: float | None = None,
    engine: SimulationEngineDep = None,
):
    """Submit a location update for immediate execution.
    
    This is a typed convenience endpoint specifically for location updates.
    
    Args:
        latitude: Latitude in degrees (-90 to 90).
        longitude: Longitude in degrees (-180 to 180).
        altitude: Altitude in meters (optional).
        accuracy: Accuracy in meters (optional).
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        Event details and updated location state.
    """
    data = {
        "latitude": latitude,
        "longitude": longitude,
    }
    if altitude is not None:
        data["altitude"] = altitude
    if accuracy is not None:
        data["accuracy"] = accuracy
    
    return await submit_to_modality("location", data, engine)


@router.post("/calendar/submit", response_model=ModalitySubmitResponse)
async def submit_calendar_action(
    action: str,
    event_data: dict[str, Any],
    engine: SimulationEngineDep = None,
):
    """Submit a calendar action for immediate execution.
    
    This is a typed convenience endpoint specifically for calendar operations.
    
    Args:
        action: Calendar action ("create_event", "update_event", "delete_event").
        event_data: Action-specific event data.
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        Event details and updated calendar state.
    
    Examples:
        Create event:
        {
            "action": "create_event",
            "event_data": {
                "title": "Team Meeting",
                "start": "2024-03-15T14:00:00Z",
                "end": "2024-03-15T15:00:00Z"
            }
        }
    """
    calendar_data = {"action": action, "event_data": event_data}
    return await submit_to_modality("calendar", calendar_data, engine)
