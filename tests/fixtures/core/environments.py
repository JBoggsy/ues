"""Fixtures for Environment."""

from datetime import datetime, timezone

from models.environment import Environment
from models.time import SimulatorTime
from tests.fixtures.modalities import location, time, weather, chat, email, calendar, sms
from tests.fixtures.core.times import create_simulator_time


def create_environment(
    modality_states: dict | None = None,
    time_state: SimulatorTime | None = None,
) -> Environment:
    """Create an Environment with sensible defaults.

    Args:
        modality_states: Dictionary of modality states (defaults to minimal set).
        time_state: SimulatorTime instance (defaults to current UTC time).

    Returns:
        Environment instance ready for testing.
    """
    if modality_states is None:
        modality_states = {
            "location": location.create_location_state(),
        }
    
    if time_state is None:
        time_state = create_simulator_time()
    
    return Environment(
        modality_states=modality_states,
        time_state=time_state,
    )


# Pre-built example constants
MINIMAL_ENVIRONMENT = create_environment(
    modality_states={
        "location": location.create_location_state(),
    }
)

FULL_ENVIRONMENT = create_environment(
    modality_states={
        "location": location.create_location_state(),
        "time": time.create_time_state(),
        "weather": weather.create_weather_state(),
        "chat": chat.create_chat_state(),
        "email": email.create_email_state(),
        "calendar": calendar.create_calendar_state(),
        "sms": sms.create_sms_state(),
    }
)

TEST_ENVIRONMENT = create_environment(
    modality_states={
        "location": location.create_location_state(
            current_latitude=37.7749,
            current_longitude=-122.4194,
            current_address="San Francisco, CA",
        ),
        "email": email.create_email_state(),
        "chat": chat.create_chat_state(),
    },
    time_state=create_simulator_time(
        current_time=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
    ),
)
