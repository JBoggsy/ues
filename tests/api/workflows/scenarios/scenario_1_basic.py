"""
Scenario 1: Basic Manual Time Control

This scenario tests the fundamental simulation lifecycle and manual
time advancement with a simple email-only workflow.

Tests:
- Simulation can be started in manual mode
- Events can be scheduled at specific future times
- Manual time advancement executes events in the correct order
- Pause/resume functionality works correctly
- Environment state accurately reflects executed events
- Simulation stop returns accurate statistics

See SCENARIO_1_BASIC_MANUAL_CONTROL.md for detailed documentation.
"""

from .base import WorkflowScenario, WorkflowStep, StepType
from ..builders import email
from ..validators import (
    StateValidator,
    EventSummaryValidator,
    ResponseValidator,
)


# =============================================================================
# Email Event Definitions
# =============================================================================

EMAIL_1_CALENDAR_REMINDER = (
    email()
    .receive()
    .from_address("calendar@company.com")
    .to("user@example.com")
    .subject("Reminder: Team Standup in 30 minutes")
    .body(
        "This is a reminder that your meeting 'Team Standup' starts at 9:30 AM.\n\n"
        "Location: Conference Room B\n"
        "Duration: 30 minutes\n\n"
        "Click here to join the video call or view meeting details."
    )
    .with_headers(**{
        "X-Calendar-Event-ID": "evt-standup-001",
        "X-Priority": "normal",
    })
    .at_offset(seconds=60)
    .with_metadata(source="calendar_integration", event_type="meeting_reminder")
)

EMAIL_2_COWORKER = (
    email()
    .receive()
    .from_address("alice.johnson@company.com")
    .to("user@example.com")
    .subject("Quick question about the project")
    .body(
        "Hey,\n\n"
        "Do you have a minute to chat about the API documentation? "
        "I found a few inconsistencies I wanted to run by you before the review meeting.\n\n"
        "Let me know when you're free.\n\n"
        "Thanks,\n"
        "Alice"
    )
    .at_offset(seconds=120)
    .with_metadata(source="external", sender_department="engineering")
)

EMAIL_3_AUTOMATED_REPORT = (
    email()
    .receive()
    .from_address("noreply@analytics.company.com")
    .to("user@example.com")
    .subject("Daily Analytics Report - November 28, 2025")
    .body(
        "Your daily analytics report is ready.\n\n"
        "=== Summary ===\n"
        "Page Views: 12,453\n"
        "Unique Visitors: 3,891\n"
        "Avg Session Duration: 4m 32s\n"
        "Bounce Rate: 42.3%\n\n"
        "Top Pages:\n"
        "1. /dashboard - 2,341 views\n"
        "2. /products - 1,892 views\n"
        "3. /about - 987 views\n\n"
        "View the full report at: https://analytics.company.com/reports/daily/2025-11-28"
    )
    .with_headers(**{
        "X-Auto-Generated": "true",
        "List-Unsubscribe": "<mailto:unsubscribe@analytics.company.com>",
    })
    .at_offset(seconds=180)
    .with_metadata(source="automated", report_type="daily_analytics")
)


# =============================================================================
# Scenario Definition
# =============================================================================

SCENARIO_1 = WorkflowScenario(
    name="Basic Manual Time Control",
    description=(
        "Tests fundamental simulation lifecycle and manual time advancement "
        "with a simple email-only workflow. Note: simulation is started by the "
        "test fixture before this scenario runs."
    ),
    complexity="simple",
    modalities=["email"],
    steps=[
        # ---------------------------------------------------------------------
        # Steps 1-3: Create scheduled email events
        # Note: Simulation is already started by the client_with_engine fixture
        # ---------------------------------------------------------------------
        WorkflowStep(
            step_type=StepType.CREATE_EVENT,
            description="Create Email #1 (calendar reminder) scheduled for T+60s",
            params={"event": EMAIL_1_CALENDAR_REMINDER},
            expect_status=200,
            assertions=[
                ResponseValidator.has_field("event_id"),
            ],
            store_as="email_1",
        ),
        WorkflowStep(
            step_type=StepType.CREATE_EVENT,
            description="Create Email #2 (coworker message) scheduled for T+120s",
            params={"event": EMAIL_2_COWORKER},
            expect_status=200,
            assertions=[
                ResponseValidator.has_field("event_id"),
            ],
            store_as="email_2",
        ),
        WorkflowStep(
            step_type=StepType.CREATE_EVENT,
            description="Create Email #3 (automated report) scheduled for T+180s",
            params={"event": EMAIL_3_AUTOMATED_REPORT},
            expect_status=200,
            assertions=[
                ResponseValidator.has_field("event_id"),
            ],
            store_as="email_3",
        ),

        # ---------------------------------------------------------------------
        # Step 4: Verify 3 pending events in queue
        # ---------------------------------------------------------------------
        WorkflowStep(
            step_type=StepType.VERIFY_EVENT_SUMMARY,
            description="Verify 3 pending email events in queue",
            assertions=[
                EventSummaryValidator.pending_count(3),
                EventSummaryValidator.executed_count(0),
                EventSummaryValidator.failed_count(0),
                EventSummaryValidator.modality_count("email", 3),
            ],
        ),

        # ---------------------------------------------------------------------
        # Step 5: Advance time by 60 seconds (execute Email #1)
        # ---------------------------------------------------------------------
        WorkflowStep(
            step_type=StepType.ADVANCE_TIME,
            description="Advance time by 60 seconds (execute Email #1)",
            params={"seconds": 60},
            expect_status=200,
        ),

        # ---------------------------------------------------------------------
        # Step 6: Verify Email #1 in inbox
        # ---------------------------------------------------------------------
        WorkflowStep(
            step_type=StepType.VERIFY_STATE,
            description="Verify Email #1 (calendar reminder) is in inbox",
            params={"modality": "email"},
            assertions=[
                StateValidator.email_count(1),
                StateValidator.email_from("calendar@company.com"),
                StateValidator.email_subject_contains("Team Standup"),
            ],
        ),

        # ---------------------------------------------------------------------
        # Step 7: Pause simulation
        # ---------------------------------------------------------------------
        WorkflowStep(
            step_type=StepType.PAUSE,
            description="Pause simulation",
            expect_status=200,
        ),

        # ---------------------------------------------------------------------
        # Step 8: Verify time state shows paused
        # Note: Manual time advance still works when paused - pause only
        # affects auto-advance mode
        # ---------------------------------------------------------------------
        WorkflowStep(
            step_type=StepType.VERIFY_TIME_STATE,
            description="Verify simulation is paused",
            assertions=[
                ResponseValidator.has_field("is_paused", True),
            ],
        ),

        # ---------------------------------------------------------------------
        # Step 9: Resume simulation
        # ---------------------------------------------------------------------
        WorkflowStep(
            step_type=StepType.RESUME,
            description="Resume simulation",
            expect_status=200,
        ),

        # ---------------------------------------------------------------------
        # Step 10: Advance time by 120 seconds (execute Email #2 and #3)
        # ---------------------------------------------------------------------
        WorkflowStep(
            step_type=StepType.ADVANCE_TIME,
            description="Advance time by 120 seconds (execute remaining emails)",
            params={"seconds": 120},
            expect_status=200,
        ),

        # ---------------------------------------------------------------------
        # Step 11: Verify all 3 emails in inbox
        # ---------------------------------------------------------------------
        WorkflowStep(
            step_type=StepType.VERIFY_STATE,
            description="Verify all 3 emails are in inbox",
            params={"modality": "email"},
            assertions=[
                StateValidator.email_count(3),
                StateValidator.email_from("calendar@company.com"),
                StateValidator.email_from("alice.johnson@company.com"),
                StateValidator.email_from("noreply@analytics.company.com"),
            ],
        ),

        # ---------------------------------------------------------------------
        # Step 12: Verify event summary shows all executed
        # ---------------------------------------------------------------------
        WorkflowStep(
            step_type=StepType.VERIFY_EVENT_SUMMARY,
            description="Verify all events have been executed",
            assertions=[
                EventSummaryValidator.pending_count(0),
                EventSummaryValidator.executed_count(3),
                EventSummaryValidator.failed_count(0),
            ],
        ),

        # ---------------------------------------------------------------------
        # Step 13: Stop simulation
        # ---------------------------------------------------------------------
        WorkflowStep(
            step_type=StepType.STOP_SIMULATION,
            description="Stop simulation and verify final counts",
            expect_status=200,
            assertions=[
                ResponseValidator.has_field("status", "stopped"),
                lambda r: r.get("events_executed", 0) == 3,
                lambda r: r.get("events_failed", 0) == 0,
            ],
        ),
    ],
)
