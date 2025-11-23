"""Dependency injection providers for the FastAPI application.

This module defines dependencies that can be injected into route handlers,
providing access to shared resources like the SimulationEngine.
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends

from models.simulation import SimulationEngine
from models.time import SimulatorTime
from models.environment import Environment
from models.queue import EventQueue
from models.modalities.weather_state import WeatherState


# Global state
# In a production app, this might be stored in a database or external service
# For now, we'll create a single shared instance when the app starts
_simulation_engine: SimulationEngine | None = None


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
    
    # Create initial weather state (empty - will be populated via API)
    initial_weather = WeatherState(
        last_updated=now,
    )
    
    # Create initial environment with weather modality
    initial_environment = Environment(
        modality_states={
            "weather": initial_weather,  # Add weather to the environment
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
