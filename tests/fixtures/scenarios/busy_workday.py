"""Busy workday simulation scenario."""

from datetime import datetime, timezone, timedelta

from models.environment import Environment
from models.event import SimulatorEvent
from models.queue import EventQueue
from models.simulation import SimulationEngine
from models.time import SimulatorTime
from tests.fixtures.modalities import location, weather, email, calendar, chat, sms


def create_busy_workday_scenario() -> dict:
    """Create a busy workday simulation scenario.

    Simulates a hectic work day with multiple meetings, emails, messages,
    and tasks. Tests the system's ability to handle high event volume
    and complex interactions.

    Returns:
        Dictionary with environment, events, simulation engine, and expected outcomes.
    """
    # Start time: 9:00 AM on a Tuesday
    start_time = datetime(2025, 1, 21, 9, 0, 0, tzinfo=timezone.utc)
    
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
                current_latitude=37.7849,
                current_longitude=-122.4094,
                current_address="Office, San Francisco, CA",
            ),
            "weather": weather.create_weather_state(),
            "email": email.create_email_state(),
            "calendar": calendar.create_calendar_state(),
            "chat": chat.create_chat_state(),
            "sms": sms.create_sms_state(),
        },
        time_state=time_state,
    )
    
    # Create busy event sequence
    events = [
        # 9:00 AM - Start of workday, check calendar
        SimulatorEvent(
            scheduled_time=start_time,
            modality="calendar",
            data=calendar.MEETING_EVENT.model_dump(),
            created_at=start_time - timedelta(hours=1),
        ),
        
        # 9:15 AM - Urgent email from boss
        SimulatorEvent(
            scheduled_time=start_time + timedelta(minutes=15),
            modality="email",
            data=email.HIGH_PRIORITY_EMAIL.model_dump(),
            created_at=start_time,
        ),
        
        # 9:30 AM - Client meeting starts
        SimulatorEvent(
            scheduled_time=start_time + timedelta(minutes=30),
            modality="calendar",
            data=calendar.create_calendar_input(
                title="Client Presentation",
                start=start_time + timedelta(minutes=30),
                end=start_time + timedelta(hours=1, minutes=30),
                attendees=[
                    calendar.Attendee(email="client@external.com", display_name="Client"),
                ],
            ).model_dump(),
            created_at=start_time,
        ),
        
        # 10:00 AM - Email with attachment
        SimulatorEvent(
            scheduled_time=start_time + timedelta(hours=1),
            modality="email",
            data=email.EMAIL_WITH_ATTACHMENT.model_dump(),
            created_at=start_time,
        ),
        
        # 10:30 AM - Text about lunch plans
        SimulatorEvent(
            scheduled_time=start_time + timedelta(hours=1, minutes=30),
            modality="sms",
            data=sms.create_sms_input(
                action="receive_message",
                message_data={
                    "from_number": "+15551234567",
                    "to_number": "+15559876543",
                    "body": "Lunch at 12:30?",
                    "message_type": "sms",
                },
            ).model_dump(),
            created_at=start_time,
        ),
        
        # 11:00 AM - Second meeting
        SimulatorEvent(
            scheduled_time=start_time + timedelta(hours=2),
            modality="calendar",
            data=calendar.ONE_ON_ONE.model_dump(),
            created_at=start_time,
        ),
        
        # 11:30 AM - Multiple emails arrive
        SimulatorEvent(
            scheduled_time=start_time + timedelta(hours=2, minutes=30),
            modality="email",
            data=email.create_email_input(
                from_address="team@company.com",
                subject="Project Update #1",
            ).model_dump(),
            created_at=start_time,
        ),
        SimulatorEvent(
            scheduled_time=start_time + timedelta(hours=2, minutes=32),
            modality="email",
            data=email.create_email_input(
                from_address="finance@company.com",
                subject="Budget Review",
            ).model_dump(),
            created_at=start_time,
        ),
        SimulatorEvent(
            scheduled_time=start_time + timedelta(hours=2, minutes=35),
            modality="email",
            data=email.EMAIL_WITH_MULTIPLE_ATTACHMENTS.model_dump(),
            created_at=start_time,
        ),
        
        # 12:00 PM - Chat message from colleague
        SimulatorEvent(
            scheduled_time=start_time + timedelta(hours=3),
            modality="chat",
            data=chat.USER_QUESTION.model_dump(),
            created_at=start_time,
        ),
        
        # 12:30 PM - Leave for lunch
        SimulatorEvent(
            scheduled_time=start_time + timedelta(hours=3, minutes=30),
            modality="location",
            data=location.create_location_input(
                latitude=37.7700,
                longitude=-122.4150,
                address="Restaurant, San Francisco, CA",
            ).model_dump(),
            created_at=start_time,
        ),
        
        # 1:30 PM - Return to office
        SimulatorEvent(
            scheduled_time=start_time + timedelta(hours=4, minutes=30),
            modality="location",
            data=location.OFFICE_LOCATION.model_dump(),
            created_at=start_time,
        ),
        
        # 2:00 PM - Afternoon meeting
        SimulatorEvent(
            scheduled_time=start_time + timedelta(hours=5),
            modality="calendar",
            data=calendar.create_calendar_input(
                title="Team Brainstorm",
                start=start_time + timedelta(hours=5),
                end=start_time + timedelta(hours=6),
            ).model_dump(),
            created_at=start_time,
        ),
        
        # 3:00 PM - More emails
        SimulatorEvent(
            scheduled_time=start_time + timedelta(hours=6),
            modality="email",
            data=email.MEETING_INVITE.model_dump(),
            created_at=start_time,
        ),
        
        # 4:00 PM - Emergency text
        SimulatorEvent(
            scheduled_time=start_time + timedelta(hours=7),
            modality="sms",
            data=sms.create_sms_input(
                action="receive_message",
                message_data={
                    "from_number": "+15551234567",
                    "to_number": "+15559876543",
                    "body": "Can you review the document ASAP?",
                    "message_type": "sms",
                },
            ).model_dump(),
            created_at=start_time,
        ),
        
        # 5:00 PM - End of day
        SimulatorEvent(
            scheduled_time=start_time + timedelta(hours=8),
            modality="chat",
            data=chat.create_chat_input(
                role="assistant",
                content="Summary of today's tasks and reminders for tomorrow.",
            ).model_dump(),
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
        "name": "Busy Workday",
        "description": "Hectic work day with meetings, emails, messages, and location changes",
        "start_time": start_time,
        "end_time": start_time + timedelta(hours=8),
        "duration_hours": 8,
        "environment": environment,
        "event_queue": event_queue,
        "simulation_engine": simulation_engine,
        "expected_state": {
            "location": {
                "address": "Office, San Francisco, CA",
            },
            "email": {
                "inbox_count": 7,  # Multiple emails throughout day
            },
            "calendar": {
                "meetings_attended": 4,
            },
            "sms": {
                "unread_count": 2,  # Lunch plans + emergency text
            },
            "chat": {
                "message_count": 2,  # Question + summary
            },
        },
        "event_count": 16,
    }
