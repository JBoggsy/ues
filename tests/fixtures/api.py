"""Shared fixtures for API testing.

These fixtures provide a TestClient and fresh SimulationEngine instance
for each test, ensuring test isolation.
"""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from main import app
from models.simulation import SimulationEngine
from tests.fixtures.core.environments import create_environment
from tests.fixtures.core.queues import create_event_queue
from tests.fixtures.core.times import create_simulator_time


@pytest.fixture
def test_client():
    """Provide a FastAPI TestClient for making API requests.
    
    The TestClient allows you to make HTTP requests to your FastAPI app
    without actually running a server. It's perfect for testing.
    
    Returns:
        A FastAPI TestClient instance.
    """
    return TestClient(app)


@pytest.fixture
def fresh_engine():
    """Provide a fresh SimulationEngine instance for each test.
    
    This fixture creates a new engine with a known initial state,
    ensuring tests don't interfere with each other.
    
    The engine includes all implemented modalities:
    - location, time, weather, chat, email, calendar, sms
    
    Returns:
        A newly initialized SimulationEngine.
    """
    # Create engine with a fixed initial time for predictable tests
    initial_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    # Create time state with fixed initial time
    time_state = create_simulator_time(current_time=initial_time)
    
    # Create environment with all implemented modality states
    from tests.fixtures.modalities import location, time as time_mod, weather, chat, email, calendar, sms
    
    environment = create_environment(
        modality_states={
            "location": location.create_location_state(),
            "time": time_mod.create_time_state(),
            "weather": weather.create_weather_state(),
            "chat": chat.create_chat_state(),
            "email": email.create_email_state(),
            "calendar": calendar.create_calendar_state(),
            "sms": sms.create_sms_state(),
        },
        time_state=time_state,
    )
    
    # Create empty event queue
    event_queue = create_event_queue()
    
    # Create engine
    engine = SimulationEngine(
        environment=environment,
        event_queue=event_queue,
    )
    
    return engine
