"""Travel day simulation scenario."""

from datetime import datetime, timezone, timedelta

from models.environment import Environment
from models.event import SimulatorEvent
from models.queue import EventQueue
from models.simulation import SimulationEngine
from models.time import SimulatorTime
from tests.fixtures.modalities import location, weather, email, calendar, chat, sms


def create_travel_day_scenario() -> dict:
    """Create a travel day simulation scenario.

    Simulates a business trip: morning preparation, travel to airport,
    flight, arrival at destination, hotel check-in. Tests location tracking,
    timezone changes, and communication during travel.

    Returns:
        Dictionary with environment, events, simulation engine, and expected outcomes.
    """
    # Start time: 5:00 AM on a Wednesday (early morning for flight)
    start_time = datetime(2025, 1, 22, 5, 0, 0, tzinfo=timezone.utc)
    
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
    
    # Create travel event sequence
    events = [
        # 5:00 AM - Check weather at home
        SimulatorEvent(
            scheduled_time=start_time,
            modality="weather",
            data=weather.CLEAR_WEATHER.model_dump(),
            created_at=start_time - timedelta(hours=1),
        ),
        
        # 5:15 AM - Flight confirmation email
        SimulatorEvent(
            scheduled_time=start_time + timedelta(minutes=15),
            modality="email",
            data=email.create_email_input(
                from_address="airline@flights.com",
                subject="Flight Confirmation - SFO to JFK",
                body_text="Your flight departs at 8:00 AM from Gate 42.",
            ).model_dump(),
            created_at=start_time,
        ),
        
        # 5:30 AM - Calendar reminder for flight
        SimulatorEvent(
            scheduled_time=start_time + timedelta(minutes=30),
            modality="calendar",
            data=calendar.create_calendar_input(
                title="Flight to NYC - SFO to JFK",
                start=start_time + timedelta(hours=3),
                end=start_time + timedelta(hours=9),
                location="San Francisco International Airport",
            ).model_dump(),
            created_at=start_time,
        ),
        
        # 6:00 AM - Leave home for airport
        SimulatorEvent(
            scheduled_time=start_time + timedelta(hours=1),
            modality="location",
            data=location.create_location_input(
                latitude=37.6213,
                longitude=-122.3790,
                address="San Francisco International Airport (SFO)",
                speed=25.0,  # Driving
            ).model_dump(),
            created_at=start_time,
        ),
        
        # 6:45 AM - Text update to family
        SimulatorEvent(
            scheduled_time=start_time + timedelta(hours=1, minutes=45),
            modality="sms",
            data=sms.create_sms_input(
                action="send_message",
                message_data={
                    "from_number": "+15559876543",
                    "to_number": "+15551234567",
                    "body": "At the airport, boarding soon!",
                    "message_type": "sms",
                },
            ).model_dump(),
            created_at=start_time,
        ),
        
        # 7:30 AM - Pre-flight work email
        SimulatorEvent(
            scheduled_time=start_time + timedelta(hours=2, minutes=30),
            modality="email",
            data=email.create_email_input(
                from_address="colleague@company.com",
                subject="Documents for NYC meeting",
                body_text="Attached are the files you'll need.",
            ).model_dump(),
            created_at=start_time,
        ),
        
        # 8:00 AM - Takeoff (location update disabled during flight)
        # 11:00 AM - In-flight (3 hours into 6-hour flight, midpoint check)
        SimulatorEvent(
            scheduled_time=start_time + timedelta(hours=6),
            modality="location",
            data=location.create_location_input(
                latitude=39.8283,  # Over midwest
                longitude=-98.5795,
                address="In flight",
                altitude=10000.0,  # 10km altitude
                speed=250.0,  # Cruising speed in m/s (~560 mph)
            ).model_dump(),
            created_at=start_time,
        ),
        
        # 2:00 PM EST (6:00 PM UTC) - Land in NYC
        SimulatorEvent(
            scheduled_time=start_time + timedelta(hours=9),
            modality="location",
            data=location.create_location_input(
                latitude=40.6413,
                longitude=-73.7781,
                address="John F. Kennedy International Airport (JFK), New York",
                speed=0.0,
            ).model_dump(),
            created_at=start_time,
        ),
        
        # 2:15 PM EST - Check NYC weather
        SimulatorEvent(
            scheduled_time=start_time + timedelta(hours=9, minutes=15),
            modality="weather",
            data=weather.create_weather_input(
                latitude=40.7128,
                longitude=-74.0060,
            ).model_dump(),
            created_at=start_time,
        ),
        
        # 2:30 PM EST - Text arrival notification
        SimulatorEvent(
            scheduled_time=start_time + timedelta(hours=9, minutes=30),
            modality="sms",
            data=sms.create_sms_input(
                action="send_message",
                message_data={
                    "from_number": "+15559876543",
                    "to_number": "+15551234567",
                    "body": "Landed safely in NYC!",
                    "message_type": "sms",
                },
            ).model_dump(),
            created_at=start_time,
        ),
        
        # 3:00 PM EST - Travel to hotel
        SimulatorEvent(
            scheduled_time=start_time + timedelta(hours=10),
            modality="location",
            data=location.create_location_input(
                latitude=40.7589,
                longitude=-73.9851,
                address="Hotel, Times Square, New York, NY",
                speed=15.0,  # Taxi
            ).model_dump(),
            created_at=start_time,
        ),
        
        # 3:30 PM EST - Hotel confirmation email
        SimulatorEvent(
            scheduled_time=start_time + timedelta(hours=10, minutes=30),
            modality="email",
            data=email.create_email_input(
                from_address="hotel@accommodations.com",
                subject="Check-in Confirmation",
                body_text="Welcome! Your room is ready. Room 1542.",
            ).model_dump(),
            created_at=start_time,
        ),
        
        # 4:00 PM EST - Calendar entry for tomorrow's meetings
        SimulatorEvent(
            scheduled_time=start_time + timedelta(hours=11),
            modality="calendar",
            data=calendar.create_calendar_input(
                title="Client Meeting - NYC Office",
                start=start_time + timedelta(hours=28),  # Next day 9am EST
                end=start_time + timedelta(hours=29),
                location="Client Office, Manhattan",
            ).model_dump(),
            created_at=start_time,
        ),
        
        # 4:30 PM EST - Work chat check-in
        SimulatorEvent(
            scheduled_time=start_time + timedelta(hours=11, minutes=30),
            modality="chat",
            data=chat.create_chat_input(
                role="assistant",
                content="Travel summary: Successfully arrived in NYC. Tomorrow's meeting at 9am is confirmed.",
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
        "name": "Travel Day",
        "description": "Business trip from SF to NYC with flight, location changes, and timezone adjustments",
        "start_time": start_time,
        "end_time": start_time + timedelta(hours=11, minutes=30),
        "duration_hours": 11.5,
        "environment": environment,
        "event_queue": event_queue,
        "simulation_engine": simulation_engine,
        "expected_state": {
            "location": {
                "address": "Hotel, Times Square, New York, NY",
                "latitude": 40.7589,
                "longitude": -73.9851,
            },
            "email": {
                "inbox_count": 3,  # Flight confirmation, work docs, hotel
            },
            "calendar": {
                "upcoming_events": 1,  # Tomorrow's meeting
            },
            "sms": {
                "sent_count": 2,  # Airport + landed messages
            },
            "weather": {
                "locations_tracked": 2,  # SF and NYC
            },
        },
        "event_count": 14,
        "locations_visited": 4,  # Home, SFO, In-flight, JFK, Hotel
    }
