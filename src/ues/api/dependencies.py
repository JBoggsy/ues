"""Dependency injection providers for the FastAPI application.

This module defines dependencies that can be injected into route handlers,
providing access to shared resources like the SimulationEngine.
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends

from ues.api.websocket import ws_manager, WSEventType
from ues.models.event import SimulatorEvent
from ues.models.simulation import SimulationEngine
from ues.models.time import SimulatorTime
from ues.models.environment import Environment
from ues.models.queue import EventQueue
from ues.models.modalities.weather_state import WeatherState
from ues.models.modalities.email_state import EmailState
from ues.models.modalities.sms_state import SMSState
from ues.models.modalities.chat_state import ChatState
from ues.models.modalities.calendar_state import CalendarState
from ues.models.modalities.location_state import LocationState
from ues.models.modalities.time_state import TimeState


# Global state
# In a production app, this might be stored in a database or external service
# For now, we'll create a single shared instance when the app starts
_simulation_engine: SimulationEngine | None = None


def _on_event_executed(event: SimulatorEvent) -> None:
    """Callback for event execution notifications.
    
    Called by SimulationEngine after each event is executed. Broadcasts
    the appropriate WebSocket event type based on the event status.
    
    Args:
        event: The executed simulator event.
    """
    from ues.models.event import EventStatus
    
    if event.status == EventStatus.EXECUTED:
        event_type = WSEventType.EVENT_EXECUTED
    else:
        event_type = WSEventType.EVENT_FAILED
    
    ws_manager.schedule_broadcast(
        event_type,
        {
            "event_id": event.event_id,
            "modality": event.modality,
            "status": event.status.value,
            "scheduled_time": event.scheduled_time.isoformat(),
            "executed_time": (
                event.executed_time.isoformat() if event.executed_time else None
            ),
        },
    )


def get_simulation_engine() -> SimulationEngine:
    """Get the shared SimulationEngine instance.
    
    This function is a FastAPI dependency. When you add it to a route handler's
    parameters, FastAPI will automatically call this function and inject the result.
    
    Returns:
        The shared SimulationEngine instance.
    
    Raises:
        RuntimeError: If the engine hasn't been initialized yet.
    
    Example:
        @router.get("/some-endpoint")
        async def my_handler(engine: Annotated[SimulationEngine, Depends(get_simulation_engine)]):
            # 'engine' is automatically provided by FastAPI
            current_time = engine.get_current_time()
            return {"time": current_time}
    """
    global _simulation_engine
    
    if _simulation_engine is None:
        raise RuntimeError(
            "SimulationEngine not initialized. Call initialize_simulation_engine() first."
        )
    
    return _simulation_engine


def initialize_simulation_engine() -> SimulationEngine:
    """Initialize the shared SimulationEngine instance.
    
    This should be called once when the FastAPI app starts up.
    Creates a new SimulationEngine with default initial state.
    
    Returns:
        The newly created SimulationEngine instance.
    """
    global _simulation_engine
    
    # Create initial simulator time (starting now)
    now = datetime.now(timezone.utc)
    initial_time = SimulatorTime(
        current_time=now,
        last_wall_time_update=now,
    )
    
    # Create initial modality states (all empty - will be populated via API)
    initial_weather = WeatherState(last_updated=now)
    initial_email = EmailState(last_updated=now)
    initial_sms = SMSState(last_updated=now, user_phone_number="+15550000000")
    initial_chat = ChatState(last_updated=now)
    initial_calendar = CalendarState(last_updated=now)
    initial_location = LocationState(last_updated=now)
    initial_time_prefs = TimeState(last_updated=now)
    
    # Create initial environment with all modalities registered
    initial_environment = Environment(
        modality_states={
            "weather": initial_weather,
            "email": initial_email,
            "sms": initial_sms,
            "chat": initial_chat,
            "calendar": initial_calendar,
            "location": initial_location,
            "time": initial_time_prefs,
        },
        time_state=initial_time,
    )
    
    # Create empty event queue
    initial_queue = EventQueue()
    
    # Create the simulation engine
    _simulation_engine = SimulationEngine(
        environment=initial_environment,
        event_queue=initial_queue,
    )
    
    # Register callback for WebSocket event execution notifications
    _simulation_engine.set_event_callback(_on_event_executed)
    
    return _simulation_engine


def shutdown_simulation_engine():
    """Shut down the SimulationEngine gracefully.
    
    This should be called when the FastAPI app shuts down.
    Stops any running simulation loops and cleans up resources.
    """
    global _simulation_engine
    
    if _simulation_engine is not None and _simulation_engine.is_running:
        _simulation_engine.stop()
    
    _simulation_engine = None


# Type alias for dependency injection
# This makes the type annotation cleaner in route handlers
SimulationEngineDep = Annotated[SimulationEngine, Depends(get_simulation_engine)]
