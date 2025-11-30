"""
Test file for Scenario 3: Interactive Agent Conversation with Scheduling.

This test file executes the Scenario 3 workflow which tests a complex,
interactive session where a user communicates with an AI assistant
through chat, triggering actions across multiple modalities.

See:
- scenarios/scenario_3_interactive.py for the scenario definition
- SCENARIO_3_INTERACTIVE_AGENT_CONVERSATION.md for detailed documentation
"""

import pytest

from .scenarios.scenario_3_interactive import (
    SCENARIO_3,
    SETUP_CALENDAR_DENTIST,
    SETUP_EMAIL_HR,
    SETUP_EMAIL_BOB,
    SETUP_EMAIL_NEWSLETTER,
    SETUP_LOCATION_OFFICE,
    EVENT_1_USER_SCHEDULE_QUERY,
    EVENT_2_ASSISTANT_SCHEDULE,
    EVENT_3_USER_SCHEDULE_BOB,
    EVENT_4_ASSISTANT_CONFLICT,
    EVENT_5_USER_CHOOSE_3PM,
    EVENT_6_ASSISTANT_CONFIRM,
    EVENT_7_CALENDAR_BOB_MEETING,
    EVENT_8_EMAIL_BOB_CONFIRM,
    EVENT_9_USER_EMAIL_ACTIONS,
    EVENT_10_ASSISTANT_EMAIL_CONFIRM,
    EVENT_13_ASSISTANT_REMINDER,
    EVENT_14_USER_SUMMARY,
    EVENT_15_ASSISTANT_SUMMARY,
    USER_EMAIL,
    OFFICE_LAT,
    OFFICE_LON,
)
from .runner import WorkflowRunner


class TestScenario3InteractiveAgentConversation:
    """Test class for Scenario 3: Interactive Agent Conversation with Scheduling.

    This scenario tests:
    - Multi-turn conversational flow with user and assistant messages
    - Calendar conflict detection and resolution
    - Cross-modality operations (chat triggering calendar/email actions)
    - Proactive assistant reminders based on time
    - End-of-day summary generation
    """

    def test_complete_workflow(self, workflow_runner: WorkflowRunner):
        """Execute the complete Scenario 3 workflow.

        This is the main test that runs all steps of the scenario
        in sequence, verifying each step's assertions.
        """
        workflow_runner.run(SCENARIO_3)

    def test_complete_workflow_quiet(self, quiet_workflow_runner: WorkflowRunner):
        """Execute the workflow without verbose output.

        Useful for CI/CD environments where less output is preferred.
        """
        quiet_workflow_runner.run(SCENARIO_3)


class TestScenario3SetupPhase:
    """Tests for the setup phase of Scenario 3.

    These tests verify that the initial state is correctly established
    before the main workflow begins.
    """

    def test_setup_creates_calendar_event(self, client_with_engine):
        """Verify setup creates the dentist appointment."""
        client, engine = client_with_engine
        from datetime import datetime

        # Get simulation time
        time_response = client.get("/simulator/time")
        base_time = datetime.fromisoformat(time_response.json()["current_time"])

        # Verify calendar is initially empty
        initial_state = client.get("/calendar/state").json()
        initial_events = len(initial_state.get("events", {}))

        # Create setup calendar event (as immediate event)
        event_data = SETUP_CALENDAR_DENTIST.build_immediate()
        response = client.post("/events/immediate", json=event_data)
        # Accept both 200 and 201 as success codes
        assert response.status_code in (200, 201)

        # Advance slightly to execute
        client.post("/simulator/time/advance", json={"seconds": 0.5})

        # Verify calendar event was added
        calendar_state = client.get("/calendar/state").json()
        assert len(calendar_state["events"]) > initial_events

        # Find and verify the dentist appointment
        found_dentist = False
        for event in calendar_state["events"].values():
            if event.get("title") == "Dentist Appointment":
                found_dentist = True
                assert "14:00" in event.get("start", "")
                assert "15:00" in event.get("end", "")
                assert "Bright Smiles" in event.get("location", "")
                break
        assert found_dentist, "Dentist Appointment not found"

    def test_setup_creates_three_emails(self, client_with_engine):
        """Verify setup creates three unread emails."""
        client, engine = client_with_engine

        # Verify email is initially empty
        initial_state = client.get("/email/state").json()
        initial_count = initial_state.get("total_email_count", 0)

        # Create setup email events (as immediate events)
        for email_builder in [SETUP_EMAIL_HR, SETUP_EMAIL_BOB, SETUP_EMAIL_NEWSLETTER]:
            event_data = email_builder.build_immediate()
            response = client.post("/events/immediate", json=event_data)
            # Accept both 200 and 201 as success codes
            assert response.status_code in (200, 201)

        # Advance slightly to execute
        client.post("/simulator/time/advance", json={"seconds": 0.5})

        # Verify emails were added
        email_state = client.get("/email/state").json()
        assert email_state["total_email_count"] == initial_count + 3

        # Verify all emails are unread
        assert email_state.get("unread_count", 0) >= 3

        # Verify senders
        senders = [e.get("from_address") for e in email_state["emails"].values()]
        assert "hr@company.com" in senders
        assert "bob@company.com" in senders
        assert "newsletter@techweekly.com" in senders

    def test_setup_creates_location(self, client_with_engine):
        """Verify setup sets location to TechCorp Office."""
        client, engine = client_with_engine

        # Create setup location event (as immediate event)
        event_data = SETUP_LOCATION_OFFICE.build_immediate()
        response = client.post("/events/immediate", json=event_data)
        # Accept both 200 and 201 as success codes
        assert response.status_code in (200, 201)

        # Advance slightly to execute
        client.post("/simulator/time/advance", json={"seconds": 0.5})

        # Verify location was set
        location_state = client.get("/location/state").json()
        current = location_state.get("current", {})

        assert current.get("named_location") == "TechCorp Office"
        assert abs(current.get("latitude", 0) - OFFICE_LAT) < 0.01
        assert abs(current.get("longitude", 0) - OFFICE_LON) < 0.01


class TestScenario3ChatConversation:
    """Tests for the chat conversation flow in Scenario 3.

    These tests verify that chat messages are created correctly
    and that the conversation flows as expected.
    """

    def test_user_schedule_query_creates_chat_message(self, client_with_engine):
        """Verify user's schedule query creates a chat message."""
        client, engine = client_with_engine
        from datetime import datetime

        # Get simulation time
        time_response = client.get("/simulator/time")
        base_time = datetime.fromisoformat(time_response.json()["current_time"])

        # Verify chat is initially empty
        initial_state = client.get("/chat/state").json()
        initial_msgs = len(initial_state.get("messages", []))

        # Create user schedule query event
        event = EVENT_1_USER_SCHEDULE_QUERY.at_offset(seconds=1).build(base_time)
        response = client.post("/events", json=event)
        assert response.status_code == 200

        # Advance time to execute
        client.post("/simulator/time/advance", json={"seconds": 2})

        # Verify chat message was added
        chat_state = client.get("/chat/state").json()
        messages = chat_state.get("messages", [])
        assert len(messages) > initial_msgs

        # Find and verify the user message
        found_query = False
        for msg in messages:
            if msg.get("role") == "user" and "schedule" in msg.get("content", "").lower():
                found_query = True
                assert msg.get("conversation_id") == "main"
                break
        assert found_query, "User schedule query message not found"

    def test_assistant_response_lists_dentist_appointment(self, client_with_engine):
        """Verify assistant response correctly lists the dentist appointment."""
        client, engine = client_with_engine
        from datetime import datetime

        # Get simulation time
        time_response = client.get("/simulator/time")
        base_time = datetime.fromisoformat(time_response.json()["current_time"])

        # Set up the dentist appointment first
        dentist_event = SETUP_CALENDAR_DENTIST.build_immediate()
        client.post("/events/immediate", json=dentist_event)
        client.post("/simulator/time/advance", json={"seconds": 0.5})

        # Create schedule query and response events
        query_event = EVENT_1_USER_SCHEDULE_QUERY.at_offset(seconds=1).build(base_time)
        response_event = EVENT_2_ASSISTANT_SCHEDULE.at_offset(seconds=2).build(base_time)

        client.post("/events", json=query_event)
        client.post("/events", json=response_event)

        # Advance time to execute
        client.post("/simulator/time/advance", json={"seconds": 3})

        # Verify assistant response
        chat_state = client.get("/chat/state").json()
        messages = chat_state.get("messages", [])

        found_response = False
        for msg in messages:
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                if "Dentist Appointment" in content:
                    found_response = True
                    # Verify key details are mentioned
                    assert "2:00 PM" in content or "14:00" in content
                    break
        assert found_response, "Assistant response with dentist appointment not found"

    def test_conflict_detection_conversation(self, client_with_engine):
        """Verify the conflict detection conversation flow."""
        client, engine = client_with_engine
        from datetime import datetime

        # Get simulation time
        time_response = client.get("/simulator/time")
        base_time = datetime.fromisoformat(time_response.json()["current_time"])

        # Set up the dentist appointment first
        dentist_event = SETUP_CALENDAR_DENTIST.build_immediate()
        client.post("/events/immediate", json=dentist_event)
        client.post("/simulator/time/advance", json={"seconds": 0.5})

        # Create conflict conversation events
        user_request = EVENT_3_USER_SCHEDULE_BOB.at_offset(seconds=1).build(base_time)
        assistant_conflict = EVENT_4_ASSISTANT_CONFLICT.at_offset(seconds=2).build(base_time)

        client.post("/events", json=user_request)
        client.post("/events", json=assistant_conflict)

        # Advance time to execute
        client.post("/simulator/time/advance", json={"seconds": 3})

        # Verify conflict detection
        chat_state = client.get("/chat/state").json()
        messages = chat_state.get("messages", [])

        # Find user's request
        found_request = any(
            msg.get("role") == "user" and "Bob" in msg.get("content", "")
            for msg in messages
        )
        assert found_request, "User's meeting request not found"

        # Find assistant's conflict detection
        found_conflict = any(
            msg.get("role") == "assistant" and "Conflict" in msg.get("content", "")
            for msg in messages
        )
        assert found_conflict, "Assistant's conflict detection not found"


class TestScenario3CalendarOperations:
    """Tests for calendar operations in Scenario 3.

    These tests verify that calendar events are created and modified
    correctly during the workflow.
    """

    def test_meeting_with_bob_created_at_3pm(self, client_with_engine):
        """Verify the Meeting with Bob is created at 3 PM after conflict resolution."""
        client, engine = client_with_engine
        from datetime import datetime

        # Get simulation time
        time_response = client.get("/simulator/time")
        base_time = datetime.fromisoformat(time_response.json()["current_time"])

        # Set up the dentist appointment first
        dentist_event = SETUP_CALENDAR_DENTIST.build_immediate()
        client.post("/events/immediate", json=dentist_event)
        client.post("/simulator/time/advance", json={"seconds": 0.5})

        # Create the Bob meeting event
        bob_meeting = EVENT_7_CALENDAR_BOB_MEETING.at_offset(seconds=1).build(base_time)
        response = client.post("/events", json=bob_meeting)
        assert response.status_code == 200

        # Advance time to execute
        client.post("/simulator/time/advance", json={"seconds": 2})

        # Verify calendar has 2 events
        calendar_state = client.get("/calendar/state").json()
        events = calendar_state.get("events", {})
        assert len(events) == 2, f"Expected 2 events, got {len(events)}"

        # Find and verify the Bob meeting
        found_bob_meeting = False
        for event in events.values():
            if event.get("title") == "Meeting with Bob":
                found_bob_meeting = True
                # Verify it's at 3 PM, not 2 PM
                assert "15:00" in event.get("start", ""), "Meeting should be at 3 PM"
                assert "14:00" not in event.get("start", ""), "Meeting should NOT be at 2 PM"
                assert "bob@company.com" in str(event.get("attendees", []))
                break
        assert found_bob_meeting, "Meeting with Bob not found in calendar"

    def test_calendar_has_both_events_after_scheduling(self, client_with_engine):
        """Verify calendar has both events after scheduling is complete."""
        client, engine = client_with_engine
        from datetime import datetime

        # Get simulation time
        time_response = client.get("/simulator/time")
        base_time = datetime.fromisoformat(time_response.json()["current_time"])

        # Create both calendar events
        dentist_event = SETUP_CALENDAR_DENTIST.at_offset(seconds=1).build(base_time)
        bob_meeting = EVENT_7_CALENDAR_BOB_MEETING.at_offset(seconds=2).build(base_time)

        client.post("/events", json=dentist_event)
        client.post("/events", json=bob_meeting)

        # Advance time to execute
        client.post("/simulator/time/advance", json={"seconds": 3})

        # Verify calendar state
        calendar_state = client.get("/calendar/state").json()
        events = calendar_state.get("events", {})

        # Should have exactly 2 events
        assert len(events) == 2, f"Expected 2 events, got {len(events)}"

        # Verify both events exist
        titles = [e.get("title") for e in events.values()]
        assert "Dentist Appointment" in titles
        assert "Meeting with Bob" in titles


class TestScenario3EmailOperations:
    """Tests for email operations in Scenario 3.

    These tests verify that email actions (read, star) work correctly.
    """

    def test_email_receive_adds_to_inbox(self, client_with_engine):
        """Verify receiving an email adds it to the inbox."""
        client, engine = client_with_engine
        from datetime import datetime

        # Get simulation time
        time_response = client.get("/simulator/time")
        base_time = datetime.fromisoformat(time_response.json()["current_time"])

        # Get initial email count
        initial_state = client.get("/email/state").json()
        initial_count = initial_state.get("total_email_count", 0)

        # Create Bob's confirmation email event
        bob_confirm = EVENT_8_EMAIL_BOB_CONFIRM.at_offset(seconds=1).build(base_time)
        response = client.post("/events", json=bob_confirm)
        assert response.status_code == 200

        # Advance time to execute
        client.post("/simulator/time/advance", json={"seconds": 2})

        # Verify email was added
        email_state = client.get("/email/state").json()
        assert email_state["total_email_count"] == initial_count + 1

        # Find and verify the email
        found_confirm = False
        for email in email_state["emails"].values():
            if "Meeting Invite" in email.get("subject", ""):
                found_confirm = True
                assert email.get("from_address") == "bob@company.com"
                assert email.get("is_read") is False  # Should be unread
                break
        assert found_confirm, "Bob's confirmation email not found"

    def test_mark_read_via_api_action(self, client_with_engine):
        """Verify marking emails as read via the modality action API."""
        client, engine = client_with_engine

        # Create setup emails (as immediate events)
        for email_builder in [SETUP_EMAIL_HR, SETUP_EMAIL_BOB, SETUP_EMAIL_NEWSLETTER]:
            event_data = email_builder.build_immediate()
            client.post("/events/immediate", json=event_data)

        # Advance slightly to execute
        client.post("/simulator/time/advance", json={"seconds": 0.5})

        # Verify emails are unread
        initial_state = client.get("/email/state").json()
        assert initial_state.get("unread_count", 0) >= 3

        # Find Bob's email message_id
        bob_message_ids = []
        for msg_id, email in initial_state["emails"].items():
            if email.get("from_address") == "bob@company.com":
                bob_message_ids.append(msg_id)

        # Skip test if no emails found (shouldn't happen, but safety check)
        if not bob_message_ids:
            pytest.skip("No Bob emails found to mark as read")

        # Mark Bob's email as read via API using message_ids
        response = client.post(
            "/email/read",
            json={"message_ids": bob_message_ids}
        )
        assert response.status_code == 200

        # Verify Bob's email is now read
        email_state = client.get("/email/state").json()
        for msg_id in bob_message_ids:
            email = email_state["emails"].get(msg_id)
            if email:
                assert email.get("is_read") is True, "Bob's email should be marked as read"

    def test_star_via_api_action(self, client_with_engine):
        """Verify starring emails via the modality action API."""
        client, engine = client_with_engine

        # Create setup emails (as immediate events)
        for email_builder in [SETUP_EMAIL_HR, SETUP_EMAIL_BOB, SETUP_EMAIL_NEWSLETTER]:
            event_data = email_builder.build_immediate()
            client.post("/events/immediate", json=event_data)

        # Advance slightly to execute
        client.post("/simulator/time/advance", json={"seconds": 0.5})

        # Find Bob's email message_id
        initial_state = client.get("/email/state").json()
        bob_message_ids = []
        for msg_id, email in initial_state["emails"].items():
            if email.get("from_address") == "bob@company.com":
                bob_message_ids.append(msg_id)

        # Skip test if no emails found
        if not bob_message_ids:
            pytest.skip("No Bob emails found to star")

        # Star Bob's email via API using message_ids
        response = client.post(
            "/email/star",
            json={"message_ids": bob_message_ids}
        )
        assert response.status_code == 200

        # Verify Bob's email is now starred
        email_state = client.get("/email/state").json()
        for msg_id in bob_message_ids:
            email = email_state["emails"].get(msg_id)
            if email:
                assert email.get("is_starred") is True, "Bob's email should be starred"


class TestScenario3ProactiveReminders:
    """Tests for proactive reminder functionality in Scenario 3."""

    def test_proactive_reminder_appears_in_chat(self, client_with_engine):
        """Verify proactive reminder appears as assistant message."""
        client, engine = client_with_engine
        from datetime import datetime

        # Get simulation time
        time_response = client.get("/simulator/time")
        base_time = datetime.fromisoformat(time_response.json()["current_time"])

        # Create proactive reminder event
        reminder = EVENT_13_ASSISTANT_REMINDER.at_offset(seconds=1).build(base_time)
        response = client.post("/events", json=reminder)
        assert response.status_code == 200

        # Advance time to execute
        client.post("/simulator/time/advance", json={"seconds": 2})

        # Verify reminder appears in chat
        chat_state = client.get("/chat/state").json()
        messages = chat_state.get("messages", [])

        found_reminder = False
        for msg in messages:
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                if "Reminder" in content and "dentist" in content.lower():
                    found_reminder = True
                    # Verify it mentions 15 minutes
                    assert "15 minutes" in content
                    break
        assert found_reminder, "Proactive dentist reminder not found in chat"


class TestScenario3DailySummary:
    """Tests for the daily summary functionality in Scenario 3."""

    def test_user_can_request_summary(self, client_with_engine):
        """Verify user can request a daily summary."""
        client, engine = client_with_engine
        from datetime import datetime

        # Get simulation time
        time_response = client.get("/simulator/time")
        base_time = datetime.fromisoformat(time_response.json()["current_time"])

        # Create summary request event
        summary_request = EVENT_14_USER_SUMMARY.at_offset(seconds=1).build(base_time)
        response = client.post("/events", json=summary_request)
        assert response.status_code == 200

        # Advance time to execute
        client.post("/simulator/time/advance", json={"seconds": 2})

        # Verify request appears in chat
        chat_state = client.get("/chat/state").json()
        messages = chat_state.get("messages", [])

        found_request = any(
            msg.get("role") == "user" and "summary" in msg.get("content", "").lower()
            for msg in messages
        )
        assert found_request, "User summary request not found in chat"

    def test_assistant_provides_summary(self, client_with_engine):
        """Verify assistant provides daily summary with correct content."""
        client, engine = client_with_engine
        from datetime import datetime

        # Get simulation time
        time_response = client.get("/simulator/time")
        base_time = datetime.fromisoformat(time_response.json()["current_time"])

        # Create summary request and response events
        summary_request = EVENT_14_USER_SUMMARY.at_offset(seconds=1).build(base_time)
        summary_response = EVENT_15_ASSISTANT_SUMMARY.at_offset(seconds=2).build(base_time)

        client.post("/events", json=summary_request)
        client.post("/events", json=summary_response)

        # Advance time to execute
        client.post("/simulator/time/advance", json={"seconds": 3})

        # Verify summary appears in chat
        chat_state = client.get("/chat/state").json()
        messages = chat_state.get("messages", [])

        found_summary = False
        for msg in messages:
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                if "Daily Summary" in content:
                    found_summary = True
                    # Verify key sections are present
                    assert "Calendar" in content
                    assert "Email" in content
                    break
        assert found_summary, "Assistant daily summary not found in chat"


class TestScenario3StateConsistency:
    """Tests for state consistency across modalities in Scenario 3."""

    def test_multi_modality_state_after_full_setup(self, client_with_engine):
        """Verify all modality states are consistent after setup."""
        client, engine = client_with_engine

        # Execute all setup events as immediate events
        setup_events = [
            SETUP_CALENDAR_DENTIST,
            SETUP_EMAIL_HR,
            SETUP_EMAIL_BOB,
            SETUP_EMAIL_NEWSLETTER,
            SETUP_LOCATION_OFFICE,
        ]

        for builder in setup_events:
            event_data = builder.build_immediate()
            response = client.post("/events/immediate", json=event_data)
            # Accept both 200 and 201 as success codes
            assert response.status_code in (200, 201)

        # Advance to execute all
        client.post("/simulator/time/advance", json={"seconds": 1})

        # Verify calendar state
        calendar_state = client.get("/calendar/state").json()
        assert len(calendar_state.get("events", {})) == 1
        assert any(
            e.get("title") == "Dentist Appointment"
            for e in calendar_state["events"].values()
        )

        # Verify email state
        email_state = client.get("/email/state").json()
        assert email_state.get("total_email_count") == 3
        assert email_state.get("unread_count") == 3

        # Verify location state
        location_state = client.get("/location/state").json()
        current = location_state.get("current", {})
        assert current.get("named_location") == "TechCorp Office"

        # Verify chat state (should be empty)
        chat_state = client.get("/chat/state").json()
        assert len(chat_state.get("messages", [])) == 0

    def test_environment_state_snapshot(self, client_with_engine):
        """Verify environment state snapshot contains all modalities."""
        client, engine = client_with_engine

        # Execute all setup events
        setup_events = [
            SETUP_CALENDAR_DENTIST,
            SETUP_EMAIL_HR,
            SETUP_EMAIL_BOB,
            SETUP_EMAIL_NEWSLETTER,
            SETUP_LOCATION_OFFICE,
        ]

        for builder in setup_events:
            event_data = builder.build_immediate()
            client.post("/events/immediate", json=event_data)

        client.post("/simulator/time/advance", json={"seconds": 1})

        # Get environment state snapshot
        env_state = client.get("/environment/state").json()

        # Verify all expected modalities are present
        modalities = env_state.get("modalities", {})
        assert "calendar" in modalities or "Calendar" in str(modalities)
        assert "email" in modalities or "Email" in str(modalities)
        assert "location" in modalities or "Location" in str(modalities)
        assert "chat" in modalities or "Chat" in str(modalities)
