"""
Scenario 2: Multi-Modality Morning Simulation

This scenario simulates a realistic 2-hour morning (8:00 AM - 10:00 AM) 
where multiple modalities interact. It tests the system's ability to:

- Handle events across 6 different modalities simultaneously
- Maintain consistent state as events execute across modalities
- Use skip-to-next navigation for efficient event-driven progression
- Accumulate state correctly over multiple event executions
- Reset the simulation and verify clean state restoration

See SCENARIO_2_MULTIMODALITY_MORNING.md for detailed documentation.
"""

from datetime import datetime

from .base import WorkflowScenario, WorkflowStep, StepType
from ..builders import email, sms, chat, calendar, location, weather
from ..validators import (
    StateValidator,
    EventSummaryValidator,
    ResponseValidator,
)


# =============================================================================
# Scenario Constants
# =============================================================================

# Base simulation time: 8:00 AM, November 28, 2025
BASE_TIME = datetime(2025, 11, 28, 8, 0, 0)

# User profile constants
USER_PHONE = "+1-555-0100"
SPOUSE_PHONE = "+1-555-0199"
USER_EMAIL = "alex@example.com"

# Location constants
HOME_LAT = 40.7128
HOME_LON = -74.0060
WORK_LAT = 40.7580
WORK_LON = -73.9855


# =============================================================================
# Event Definitions
# =============================================================================

# Event 1: SMS from Spouse (8:05 AM, +5 minutes)
EVENT_1_SMS_SPOUSE = (
    sms()
    .receive()
    .from_number(SPOUSE_PHONE)
    .to(USER_PHONE)
    .body(
        "Hey! Running late this morning. Can you pick up groceries on your "
        "way home? We need milk, bread, and eggs. Thanks! ❤️"
    )
    .with_priority(50)
    .at_offset(minutes=5)
    .with_metadata(sender_name="Jordan (Spouse)", relationship="spouse")
)

# Event 2: Calendar Reminder (8:15 AM, +15 minutes)
EVENT_2_CALENDAR_STANDUP = (
    calendar()
    .create()
    .title("Team Standup")
    .description(
        "Daily engineering team standup meeting.\n\n"
        "Agenda:\n"
        "- Yesterday's progress\n"
        "- Today's plans\n"
        "- Blockers\n\n"
        "Video call link: https://meet.company.com/standup"
    )
    .start("2025-11-28T09:00:00")
    .end("2025-11-28T09:30:00")
    .location("Conference Room B / Virtual")
    .attendees(
        USER_EMAIL,
        "alice@company.com",
        "bob@company.com",
        "carol@company.com",
    )
    .reminder(15, "notification")
    .reminder(5, "notification")
    .on_calendar("work")
    .with_priority(60)
    .at_offset(minutes=15)
    .with_metadata(event_type="recurring_meeting", recurrence="daily_weekdays")
)

# Event 3: Work Email with Meeting Agenda (8:20 AM, +20 minutes)
EVENT_3_EMAIL_AGENDA = (
    email()
    .receive()
    .from_address("alice@company.com")
    .to(USER_EMAIL)
    .cc("bob@company.com", "carol@company.com")
    .subject("Standup Agenda - Nov 28")
    .body(
        "Hi team,\n\n"
        "Here's the agenda for today's standup:\n\n"
        "1. Sprint Progress Review\n"
        "   - We're at 75% completion for Sprint 23\n"
        "   - 3 stories remaining\n\n"
        "2. API Documentation Status\n"
        "   - Alex: Can you give an update on the REST API docs?\n\n"
        "3. Blockers\n"
        "   - CI/CD pipeline issues from yesterday\n"
        "   - Waiting on design review for the new dashboard\n\n"
        "4. Upcoming\n"
        "   - Sprint review Friday at 2 PM\n"
        "   - Holiday schedule reminder\n\n"
        "See you at 9!\n\n"
        "Alice"
    )
    .with_priority(50)
    .at_offset(minutes=20)
    .with_metadata(thread_id="thread-standup-001", category="work")
)

# Event 4: Location Update - Leaving Home (8:30 AM, +30 minutes)
EVENT_4_LOCATION_LEAVING = (
    location()
    .at(40.7135, -74.0046)
    .altitude(10.0)
    .accuracy(15.0)
    .speed(1.2)
    .heading(45.0)
    .named("Outside Home")
    .address("123 Main St, New York, NY 10001")
    .with_priority(40)
    .at_offset(minutes=30)
    .with_metadata(
        activity="walking",
        destination="work",
        transport_mode="transit",
    )
)

# Event 5: Location Update - Subway Station (8:35 AM, +35 minutes)
EVENT_5_LOCATION_SUBWAY = (
    location()
    .at(40.7200, -74.0010)
    .altitude(-5.0)  # Underground
    .accuracy(50.0)
    .speed(0.0)
    .named("Canal Street Station")
    .address("Canal St & Lafayette St, New York, NY 10013")
    .with_priority(40)
    .at_offset(minutes=35)
    .with_metadata(
        activity="stationary",
        venue_type="transit_station",
        transport_mode="subway",
    )
)

# Event 6: Weather Update - Rain Starting (8:45 AM, +45 minutes)
# Temperature 43°F = 6.1°C, feels_like 38°F = 3.3°C
EVENT_6_WEATHER_RAIN = (
    weather()
    .at(WORK_LAT, WORK_LON)
    .temperature(6.1, 3.3)  # Celsius (temp, feels_like)
    .humidity(85)
    .pressure(1008)
    .conditions("Light Rain", "Light rain expected to continue through the morning. Temperature dropping slightly.")
    .wind(12.0, 225)
    .visibility(5000)
    .cloud_cover(90)
    .precipitation_probability(80)
    .with_priority(30)
    .at_offset(minutes=45)
    .with_metadata(
        source="weather_service",
        forecast_type="current",
        alert_level="advisory",
    )
)

# Event 7: Location Update - Arrived at Work (8:55 AM, +55 minutes)
EVENT_7_LOCATION_WORK = (
    location()
    .at(WORK_LAT, WORK_LON)
    .altitude(15.0)
    .accuracy(10.0)
    .speed(0.0)
    .named("TechCorp Office")
    .address("350 5th Avenue, New York, NY 10118")
    .with_priority(40)
    .at_offset(minutes=55)
    .with_metadata(
        activity="stationary",
        venue_type="workplace",
        arrival_event=True,
    )
)

# Event 8: Chat Assistant Reminder (9:00 AM, +60 minutes)
EVENT_8_CHAT_REMINDER = (
    chat()
    .assistant_message(
        "Good morning! 🌧️ Just a heads up:\n\n"
        "📅 Your Team Standup is starting now in Conference Room B.\n\n"
        "☔ It's raining outside (43°F), so don't forget your umbrella "
        "if you need to step out later.\n\n"
        "📱 You have an unread text from Jordan about picking up groceries "
        "on your way home."
    )
    .in_conversation("default")
    .with_priority(70)
    .at_offset(minutes=60)
    .with_metadata(
        message_type="proactive_reminder",
        context_sources=["calendar", "weather", "sms"],
    )
)


# =============================================================================
# Scenario Definition
# =============================================================================

SCENARIO_2 = WorkflowScenario(
    name="Multi-Modality Morning Simulation",
    description=(
        "Simulates a realistic 2-hour morning (8:00 AM - 10:00 AM) where "
        "multiple modalities interact. Tests skip-to-next navigation and "
        "state accumulation across SMS, Calendar, Email, Location, Weather, "
        "and Chat modalities."
    ),
    complexity="medium",
    modalities=["sms", "calendar", "email", "location", "weather", "chat"],
    steps=[
        # ---------------------------------------------------------------------
        # Steps 1-8: Create all scheduled events
        # Note: Simulation is already started by the client_with_engine fixture
        # ---------------------------------------------------------------------
        WorkflowStep(
            step_type=StepType.CREATE_EVENT,
            description="Create Event #1: SMS from spouse (T+5m)",
            params={"event": EVENT_1_SMS_SPOUSE},
            expect_status=200,
            assertions=[
                ResponseValidator.has_field("event_id"),
            ],
            store_as="event_1_sms",
        ),
        WorkflowStep(
            step_type=StepType.CREATE_EVENT,
            description="Create Event #2: Calendar standup (T+15m)",
            params={"event": EVENT_2_CALENDAR_STANDUP},
            expect_status=200,
            assertions=[
                ResponseValidator.has_field("event_id"),
            ],
            store_as="event_2_calendar",
        ),
        WorkflowStep(
            step_type=StepType.CREATE_EVENT,
            description="Create Event #3: Email with agenda (T+20m)",
            params={"event": EVENT_3_EMAIL_AGENDA},
            expect_status=200,
            assertions=[
                ResponseValidator.has_field("event_id"),
            ],
            store_as="event_3_email",
        ),
        WorkflowStep(
            step_type=StepType.CREATE_EVENT,
            description="Create Event #4: Location - leaving home (T+30m)",
            params={"event": EVENT_4_LOCATION_LEAVING},
            expect_status=200,
            assertions=[
                ResponseValidator.has_field("event_id"),
            ],
            store_as="event_4_location",
        ),
        WorkflowStep(
            step_type=StepType.CREATE_EVENT,
            description="Create Event #5: Location - subway station (T+35m)",
            params={"event": EVENT_5_LOCATION_SUBWAY},
            expect_status=200,
            assertions=[
                ResponseValidator.has_field("event_id"),
            ],
            store_as="event_5_location",
        ),
        WorkflowStep(
            step_type=StepType.CREATE_EVENT,
            description="Create Event #6: Weather update - rain (T+45m)",
            params={"event": EVENT_6_WEATHER_RAIN},
            expect_status=200,
            assertions=[
                ResponseValidator.has_field("event_id"),
            ],
            store_as="event_6_weather",
        ),
        WorkflowStep(
            step_type=StepType.CREATE_EVENT,
            description="Create Event #7: Location - arrived at work (T+55m)",
            params={"event": EVENT_7_LOCATION_WORK},
            expect_status=200,
            assertions=[
                ResponseValidator.has_field("event_id"),
            ],
            store_as="event_7_location",
        ),
        WorkflowStep(
            step_type=StepType.CREATE_EVENT,
            description="Create Event #8: Chat assistant reminder (T+60m)",
            params={"event": EVENT_8_CHAT_REMINDER},
            expect_status=200,
            assertions=[
                ResponseValidator.has_field("event_id"),
            ],
            store_as="event_8_chat",
        ),

        # ---------------------------------------------------------------------
        # Step 9: Verify 8 pending events with correct modality distribution
        # ---------------------------------------------------------------------
        WorkflowStep(
            step_type=StepType.VERIFY_EVENT_SUMMARY,
            description="Verify 8 pending events with correct modality counts",
            assertions=[
                EventSummaryValidator.pending_count(8),
                EventSummaryValidator.executed_count(0),
                EventSummaryValidator.failed_count(0),
                EventSummaryValidator.modality_count("sms", 1),
                EventSummaryValidator.modality_count("calendar", 1),
                EventSummaryValidator.modality_count("email", 1),
                EventSummaryValidator.modality_count("location", 3),
                EventSummaryValidator.modality_count("weather", 1),
                EventSummaryValidator.modality_count("chat", 1),
            ],
        ),

        # ---------------------------------------------------------------------
        # Steps 10-17: Skip-to-next execution sequence
        # Each skip advances time to the next event and executes it
        # ---------------------------------------------------------------------

        # Skip 1: Execute SMS from spouse (T+5m)
        WorkflowStep(
            step_type=StepType.SKIP_TO_NEXT,
            description="Skip to Event #1: SMS from spouse",
            expect_status=200,
            assertions=[
                ResponseValidator.has_field("events_executed", 1),
            ],
        ),
        WorkflowStep(
            step_type=StepType.VERIFY_STATE,
            description="Verify SMS from spouse in state",
            params={"modality": "sms"},
            assertions=[
                StateValidator.sms_count(1),
                StateValidator.sms_from(SPOUSE_PHONE),
                StateValidator.sms_body_contains("groceries"),
            ],
        ),

        # Skip 2: Execute Calendar event (T+15m)
        WorkflowStep(
            step_type=StepType.SKIP_TO_NEXT,
            description="Skip to Event #2: Calendar standup",
            expect_status=200,
            assertions=[
                ResponseValidator.has_field("events_executed", 1),
            ],
        ),
        WorkflowStep(
            step_type=StepType.VERIFY_STATE,
            description="Verify calendar event created",
            params={"modality": "calendar"},
            assertions=[
                StateValidator.calendar_event_count(1),
                StateValidator.calendar_event_exists("Team Standup"),
                StateValidator.calendar_event_at_time("Team Standup", "09:00"),
            ],
        ),

        # Skip 3: Execute Email with agenda (T+20m)
        WorkflowStep(
            step_type=StepType.SKIP_TO_NEXT,
            description="Skip to Event #3: Email with agenda",
            expect_status=200,
            assertions=[
                ResponseValidator.has_field("events_executed", 1),
            ],
        ),
        WorkflowStep(
            step_type=StepType.VERIFY_STATE,
            description="Verify email from Alice in inbox",
            params={"modality": "email"},
            assertions=[
                StateValidator.email_count(1),
                StateValidator.email_from("alice@company.com"),
                StateValidator.email_subject_contains("Standup Agenda"),
            ],
        ),

        # Skip 4: Execute Location - leaving home (T+30m)
        WorkflowStep(
            step_type=StepType.SKIP_TO_NEXT,
            description="Skip to Event #4: Location - leaving home",
            expect_status=200,
            assertions=[
                ResponseValidator.has_field("events_executed", 1),
            ],
        ),
        WorkflowStep(
            step_type=StepType.VERIFY_STATE,
            description="Verify location shows 'Outside Home'",
            params={"modality": "location"},
            assertions=[
                StateValidator.location_is("Outside Home"),
                StateValidator.location_near(40.7135, -74.0046),
            ],
        ),

        # Skip 5: Execute Location - subway station (T+35m)
        WorkflowStep(
            step_type=StepType.SKIP_TO_NEXT,
            description="Skip to Event #5: Location - subway station",
            expect_status=200,
            assertions=[
                ResponseValidator.has_field("events_executed", 1),
            ],
        ),
        WorkflowStep(
            step_type=StepType.VERIFY_STATE,
            description="Verify location shows 'Canal Street Station'",
            params={"modality": "location"},
            assertions=[
                StateValidator.location_is("Canal Street Station"),
                StateValidator.location_near(40.7200, -74.0010),
            ],
        ),

        # Skip 6: Execute Weather update (T+45m)
        WorkflowStep(
            step_type=StepType.SKIP_TO_NEXT,
            description="Skip to Event #6: Weather update - rain",
            expect_status=200,
            assertions=[
                ResponseValidator.has_field("events_executed", 1),
            ],
        ),
        WorkflowStep(
            step_type=StepType.VERIFY_STATE,
            description="Verify weather shows rain conditions",
            params={"modality": "weather"},
            assertions=[
                StateValidator.weather_conditions("Light Rain"),
                StateValidator.weather_temperature_range(4.0, 8.0),  # ~6°C expected
            ],
        ),

        # Skip 7: Execute Location - arrived at work (T+55m)
        WorkflowStep(
            step_type=StepType.SKIP_TO_NEXT,
            description="Skip to Event #7: Location - arrived at work",
            expect_status=200,
            assertions=[
                ResponseValidator.has_field("events_executed", 1),
            ],
        ),
        WorkflowStep(
            step_type=StepType.VERIFY_STATE,
            description="Verify location shows 'TechCorp Office'",
            params={"modality": "location"},
            assertions=[
                StateValidator.location_is("TechCorp Office"),
                StateValidator.location_near(WORK_LAT, WORK_LON),
            ],
        ),

        # Skip 8: Execute Chat assistant reminder (T+60m)
        WorkflowStep(
            step_type=StepType.SKIP_TO_NEXT,
            description="Skip to Event #8: Chat assistant reminder",
            expect_status=200,
            assertions=[
                ResponseValidator.has_field("events_executed", 1),
            ],
        ),
        WorkflowStep(
            step_type=StepType.VERIFY_STATE,
            description="Verify chat message from assistant",
            params={"modality": "chat"},
            assertions=[
                StateValidator.chat_message_count(1),
                StateValidator.chat_has_message_from("assistant", "Good morning"),
            ],
        ),

        # ---------------------------------------------------------------------
        # Step 26: Verify final event summary - all executed
        # ---------------------------------------------------------------------
        WorkflowStep(
            step_type=StepType.VERIFY_EVENT_SUMMARY,
            description="Verify all 8 events executed",
            assertions=[
                EventSummaryValidator.pending_count(0),
                EventSummaryValidator.executed_count(8),
                EventSummaryValidator.failed_count(0),
            ],
        ),

        # ---------------------------------------------------------------------
        # Step 27: Verify complete environment state
        # ---------------------------------------------------------------------
        WorkflowStep(
            step_type=StepType.VERIFY_ENVIRONMENT,
            description="Verify complete environment state snapshot",
            assertions=[
                ResponseValidator.has_field("modalities"),
                ResponseValidator.has_field("current_time"),
            ],
        ),

        # ---------------------------------------------------------------------
        # Step 28: Reset simulation
        # ---------------------------------------------------------------------
        WorkflowStep(
            step_type=StepType.RESET_SIMULATION,
            description="Reset simulation to initial state",
            expect_status=200,
            assertions=[
                ResponseValidator.has_field("message"),
            ],
        ),

        # ---------------------------------------------------------------------
        # Step 29: Verify clean state after reset
        # ---------------------------------------------------------------------
        WorkflowStep(
            step_type=StepType.VERIFY_SIMULATION_STATUS,
            description="Verify simulation is stopped after reset",
            assertions=[
                ResponseValidator.has_field("is_running", False),
            ],
        ),
        WorkflowStep(
            step_type=StepType.VERIFY_EVENT_SUMMARY,
            description="Verify events are reset to pending after reset",
            assertions=[
                # All 8 events should be reset to pending (not deleted)
                EventSummaryValidator.pending_count(8),
                EventSummaryValidator.executed_count(0),
                EventSummaryValidator.failed_count(0),
            ],
        ),
    ],
)
