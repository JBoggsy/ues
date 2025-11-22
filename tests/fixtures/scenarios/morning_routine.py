"""Morning routine simulation scenario."""

from datetime import datetime, timezone, timedelta

from models.environment import Environment
from models.event import SimulatorEvent
from models.queue import EventQueue
from models.simulation import SimulationEngine
from models.time import SimulatorTime
from tests.fixtures.modalities import location, weather, email, calendar, chat, sms


def create_morning_routine_scenario() -> dict:
    """Create a complete morning routine simulation scenario.

    Simulates a typical morning: wake up, check weather, receive emails,
    get calendar reminders, commute to work.

    Returns:
        Dictionary with environment, events, simulation engine, and expected outcomes.
    """
    # Start time: 6:00 AM on a Monday
    start_time = datetime(2025, 1, 20, 6, 0, 0, tzinfo=timezone.utc)
    
    # Create initial environment state
    time_state = SimulatorTime(
        current_time=start_time,
        last_wall_time_update=datetime.now(timezone.utc),
        time_scale=1.0,
        is_paused=False,
        auto_advance=False,
    )
    
    environment = Environment(
        modality_states={
            "location": location.create_location_state(
                current_latitude=37.7749,
                current_longitude=-122.4194,
                current_address="Home, San Francisco, CA",
            ),
            "weather": weather.create_weather_state(),
            "email": email.create_email_state(),
            "calendar": calendar.create_calendar_state(),
            "chat": chat.create_chat_state(),
            "sms": sms.create_sms_state(),
        },
        time_state=time_state,
    )
    
    # Create event sequence
    events = [
        # 6:05 AM - Check weather
        SimulatorEvent(
            scheduled_time=start_time + timedelta(minutes=5),
            modality="weather",
            data=weather.CLEAR_WEATHER.model_dump(),
            created_at=start_time,
        ),
        
        # 6:10 AM - Receive morning news email
        SimulatorEvent(
            scheduled_time=start_time + timedelta(minutes=10),
            modality="email",
            data=email.create_email_input(
                from_address="newsletter@news.com",
                to_addresses=["you@example.com"],
                subject="Daily News Digest - January 20",
                body_text="Your morning news summary...",
            ).model_dump(),
            created_at=start_time,
        ),
        
        # 6:30 AM - Calendar reminder for 9am meeting
        SimulatorEvent(
            scheduled_time=start_time + timedelta(minutes=30),
            modality="calendar",
            data=calendar.MEETING_EVENT.model_dump(),
            created_at=start_time,
        ),
        
        # 6:45 AM - Text from friend
        SimulatorEvent(
            scheduled_time=start_time + timedelta(minutes=45),
            modality="sms",
            data=sms.SIMPLE_RECEIVE.model_dump(),
            created_at=start_time,
        ),
        
        # 7:00 AM - Receive work email
        SimulatorEvent(
            scheduled_time=start_time + timedelta(hours=1),
            modality="email",
            data=email.WORK_EMAIL.model_dump(),
            created_at=start_time,
        ),
        
        # 7:30 AM - Leave for work
        SimulatorEvent(
            scheduled_time=start_time + timedelta(hours=1, minutes=30),
            modality="location",
            data=location.create_location_input(
                latitude=37.7849,
                longitude=-122.4094,
                address="Office, San Francisco, CA",
                named_location="Office",
                speed=10.0,  # Walking speed
            ).model_dump(),
            created_at=start_time,
        ),
        
        # 8:00 AM - Arrive at office
        SimulatorEvent(
            scheduled_time=start_time + timedelta(hours=2),
            modality="location",
            data=location.OFFICE_LOCATION.model_dump(),
            created_at=start_time,
        ),
    ]
    
    # Create event queue
    event_queue = EventQueue(events=events)
    
    # Create simulation engine
    simulation_engine = SimulationEngine(
        environment=environment,
        event_queue=event_queue,
    )
    
    return {
        "name": "Morning Routine",
        "description": "Typical morning: wake up, check weather, emails, commute to work",
        "start_time": start_time,
        "end_time": start_time + timedelta(hours=2),
        "duration_hours": 2,
        "environment": environment,
        "event_queue": event_queue,
        "simulation_engine": simulation_engine,
        "expected_state": {
            "location": {
                "address": "Office, San Francisco, CA",
                "named_location": "Office",
            },
            "email": {
                "inbox_count": 2,  # News digest + work email
            },
            "calendar": {
                "upcoming_events": 1,  # Team meeting at 9am
            },
            "sms": {
                "unread_count": 1,  # Friend's message
            },
        },
        "event_count": 7,
    }
