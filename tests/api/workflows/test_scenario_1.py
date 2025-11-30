"""
Test file for Scenario 1: Basic Manual Time Control.

This test file executes the Scenario 1 workflow which tests
fundamental simulation lifecycle and manual time advancement
with email events.

See:
- scenarios/scenario_1_basic.py for the scenario definition
- SCENARIO_1_BASIC_MANUAL_CONTROL.md for detailed documentation
"""

import pytest

from .scenarios.scenario_1_basic import (
    SCENARIO_1,
    EMAIL_1_CALENDAR_REMINDER,
    EMAIL_2_COWORKER,
    EMAIL_3_AUTOMATED_REPORT,
)
from .runner import WorkflowRunner


class TestScenario1BasicManualControl:
    """Test class for Scenario 1: Basic Manual Time Control.

    This scenario tests:
    - Simulation can be started in manual mode
    - Events can be scheduled at specific future times
    - Manual time advancement executes events correctly
    - Pause/resume functionality works
    - Environment state accurately reflects executed events
    - Simulation stop returns accurate statistics
    """

    def test_complete_workflow(self, workflow_runner: WorkflowRunner):
        """Execute the complete Scenario 1 workflow.

        This is the main test that runs all 13 steps of the scenario
        in sequence, verifying each step's assertions.
        """
        workflow_runner.run(SCENARIO_1)

    def test_complete_workflow_quiet(self, quiet_workflow_runner: WorkflowRunner):
        """Execute the workflow without verbose output.

        Useful for CI/CD environments where less output is preferred.
        """
        quiet_workflow_runner.run(SCENARIO_1)


class TestScenario1IndividualSteps:
    """Individual step tests for debugging Scenario 1.

    These tests verify individual components of the workflow
    in isolation, useful for debugging failures in the full workflow.
    """

    def test_simulation_starts_in_manual_mode(self, client_with_engine):
        """Verify simulation can start in manual mode."""
        client, engine = client_with_engine

        # Stop the auto-started simulation first
        client.post("/simulation/stop")

        # Start in manual mode
        response = client.post("/simulation/start", json={"auto_advance": False})
        assert response.status_code == 200

        data = response.json()
        assert data.get("status") == "running"

    def test_email_event_creation(self, client_with_engine):
        """Verify email events can be created with builders."""
        client, engine = client_with_engine
        from datetime import datetime

        # Get current simulation time as base
        time_response = client.get("/simulator/time")
        base_time = datetime.fromisoformat(time_response.json()["current_time"])

        event_data = EMAIL_1_CALENDAR_REMINDER.build(base_time)

        response = client.post("/events", json=event_data)
        assert response.status_code == 200

        data = response.json()
        assert "event_id" in data
        assert data.get("modality") == "email"

    def test_pause_sets_pause_state(self, client_with_engine):
        """Verify pause sets the paused state.
        
        Note: Pause only affects auto-advance mode. Manual time advance
        still works when paused.
        """
        client, engine = client_with_engine

        # Pause the simulation
        response = client.post("/simulator/time/pause")
        assert response.status_code == 200

        # Verify is_paused is True
        data = response.json()
        assert data.get("is_paused") is True

        # Verify time state reflects pause
        time_response = client.get("/simulator/time")
        assert time_response.json().get("is_paused") is True

    def test_resume_allows_time_advance(self, client_with_engine):
        """Verify resume allows time advancement after pause."""
        client, engine = client_with_engine

        # Pause
        client.post("/simulator/time/pause")

        # Resume
        response = client.post("/simulator/time/resume")
        assert response.status_code == 200

        # Now time advance should work
        response = client.post(
            "/simulator/time/advance",
            json={"seconds": 1},
        )
        assert response.status_code == 200


class TestEventExecutionUpdatesEnvironment:
    """Tests that verify executed events actually update the environment state.
    
    These tests go beyond checking event status - they verify that the
    simulation environment reflects the correct state after events execute.
    """

    def test_email_receive_event_adds_email_to_state(self, client_with_engine):
        """Verify receiving an email event adds it to the email state.
        
        This test creates a "receive" email event, executes it, and verifies:
        1. The event status changes to "executed"
        2. The email appears in the email state
        3. The email has the correct sender, subject, and body
        """
        client, engine = client_with_engine
        from datetime import datetime

        # Get simulation time
        time_response = client.get("/simulator/time")
        base_time = datetime.fromisoformat(time_response.json()["current_time"])

        # Verify email state is initially empty
        initial_state = client.get("/email/state").json()
        initial_count = initial_state.get("total_email_count", 0)

        # Create email event scheduled for T+1s
        event = EMAIL_1_CALENDAR_REMINDER.at_offset(seconds=1).build(base_time)
        create_response = client.post("/events", json=event)
        assert create_response.status_code == 200
        event_id = create_response.json()["event_id"]

        # Verify event is pending
        event_detail = client.get(f"/events/{event_id}").json()
        assert event_detail["status"] == "pending"

        # Advance time to execute the event
        client.post("/simulator/time/advance", json={"seconds": 2})

        # Verify event status changed to executed
        event_detail = client.get(f"/events/{event_id}").json()
        assert event_detail["status"] == "executed", (
            f"Expected event status 'executed', got '{event_detail['status']}'"
        )

        # Verify email was added to state
        email_state = client.get("/email/state").json()
        assert email_state["total_email_count"] == initial_count + 1, (
            f"Expected {initial_count + 1} emails, got {email_state['total_email_count']}"
        )

        # Verify the email has correct content
        emails = email_state["emails"]
        assert len(emails) == initial_count + 1
        
        # Find the new email and verify its content
        new_email = None
        for email in emails.values():
            if email.get("from_address") == "calendar@company.com":
                new_email = email
                break
        
        assert new_email is not None, "Email from calendar@company.com not found"
        assert "Team Standup" in new_email.get("subject", ""), (
            f"Expected 'Team Standup' in subject, got '{new_email.get('subject')}'"
        )
        assert new_email.get("is_read") is False, "New email should be unread"

    def test_multiple_email_events_accumulate_correctly(self, client_with_engine):
        """Verify multiple email events accumulate in state correctly.
        
        This test creates multiple email events at different times and verifies:
        1. Each event executes at the correct time
        2. Emails accumulate in state (not overwritten)
        3. Each email has correct, distinct content
        """
        client, engine = client_with_engine
        from datetime import datetime

        # Get simulation time
        time_response = client.get("/simulator/time")
        base_time = datetime.fromisoformat(time_response.json()["current_time"])

        # Verify initial state
        initial_state = client.get("/email/state").json()
        initial_count = initial_state.get("total_email_count", 0)

        # Create three email events at different times
        events = [
            (EMAIL_1_CALENDAR_REMINDER, 60, "calendar@company.com"),
            (EMAIL_2_COWORKER, 120, "alice.johnson@company.com"),
            (EMAIL_3_AUTOMATED_REPORT, 180, "noreply@analytics.company.com"),
        ]
        
        event_ids = []
        for builder, offset, _ in events:
            event = builder.at_offset(seconds=offset).build(base_time)
            response = client.post("/events", json=event)
            assert response.status_code == 200
            event_ids.append(response.json()["event_id"])

        # Verify all events pending
        summary = client.get("/events/summary").json()
        assert summary["pending"] == 3

        # Advance time by 60s - should execute first email
        client.post("/simulator/time/advance", json={"seconds": 60})
        
        email_state = client.get("/email/state").json()
        assert email_state["total_email_count"] == initial_count + 1, (
            f"After 60s: expected {initial_count + 1} emails, got {email_state['total_email_count']}"
        )
        
        # Verify first event executed, others pending
        assert client.get(f"/events/{event_ids[0]}").json()["status"] == "executed"
        assert client.get(f"/events/{event_ids[1]}").json()["status"] == "pending"
        assert client.get(f"/events/{event_ids[2]}").json()["status"] == "pending"

        # Advance another 60s - should execute second email
        client.post("/simulator/time/advance", json={"seconds": 60})
        
        email_state = client.get("/email/state").json()
        assert email_state["total_email_count"] == initial_count + 2, (
            f"After 120s: expected {initial_count + 2} emails, got {email_state['total_email_count']}"
        )
        
        # Verify second email is from alice
        has_alice_email = any(
            e.get("from_address") == "alice.johnson@company.com"
            for e in email_state["emails"].values()
        )
        assert has_alice_email, "Email from alice.johnson@company.com not found after 120s"

        # Advance another 60s - should execute third email
        client.post("/simulator/time/advance", json={"seconds": 60})
        
        email_state = client.get("/email/state").json()
        assert email_state["total_email_count"] == initial_count + 3, (
            f"After 180s: expected {initial_count + 3} emails, got {email_state['total_email_count']}"
        )

        # Verify all three emails present with correct senders
        senders = {e.get("from_address") for e in email_state["emails"].values()}
        expected_senders = {
            "calendar@company.com",
            "alice.johnson@company.com", 
            "noreply@analytics.company.com",
        }
        assert expected_senders.issubset(senders), (
            f"Missing senders. Expected {expected_senders}, got {senders}"
        )

        # Verify all events marked executed
        summary = client.get("/events/summary").json()
        assert summary["executed"] == 3
        assert summary["pending"] == 0

    def test_immediate_event_executes_with_minimal_time_advance(self, client_with_engine):
        """Verify immediate events execute with minimal time advancement.
        
        The /events/immediate endpoint creates an event scheduled at the
        current time with high priority. It still requires time to advance
        (even by a tiny amount) to trigger execution.
        """
        client, engine = client_with_engine
        from datetime import datetime

        # Get simulation time
        time_response = client.get("/simulator/time")
        base_time = datetime.fromisoformat(time_response.json()["current_time"])

        # Verify initial state
        initial_state = client.get("/email/state").json()
        initial_count = initial_state.get("total_email_count", 0)

        # Create immediate event
        event = EMAIL_2_COWORKER.at_offset(seconds=0).build(base_time)
        response = client.post("/events/immediate", json={
            "modality": "email",
            "data": event["data"],
        })
        assert response.status_code == 200
        event_id = response.json()["event_id"]
        
        # Event should be pending (not yet executed)
        event_detail = client.get(f"/events/{event_id}").json()
        assert event_detail["status"] == "pending"

        # Minimal time advance to trigger execution
        client.post("/simulator/time/advance", json={"seconds": 0.001})
        
        # Now email should be in state
        email_state = client.get("/email/state").json()
        assert email_state["total_email_count"] == initial_count + 1, (
            f"After minimal time advance, expected {initial_count + 1} emails, "
            f"got {email_state['total_email_count']}"
        )
        
        # Verify event was executed
        event_detail = client.get(f"/events/{event_id}").json()
        assert event_detail["status"] == "executed"

        # Verify email content
        has_coworker_email = any(
            e.get("from_address") == "alice.johnson@company.com"
            for e in email_state["emails"].values()
        )
        assert has_coworker_email, "Email from alice not found"

    def test_email_content_matches_event_data(self, client_with_engine):
        """Verify email content in state exactly matches the event data.
        
        This is a detailed content verification test.
        """
        client, engine = client_with_engine
        from datetime import datetime

        # Get simulation time
        time_response = client.get("/simulator/time")
        base_time = datetime.fromisoformat(time_response.json()["current_time"])

        # Create and execute immediate event
        event = EMAIL_1_CALENDAR_REMINDER.at_offset(seconds=0).build(base_time)
        client.post("/events/immediate", json={
            "modality": "email",
            "data": event["data"],
        })
        
        # Advance time to execute the event
        client.post("/simulator/time/advance", json={"seconds": 0.001})

        # Get the email from state
        email_state = client.get("/email/state").json()
        emails = list(email_state["emails"].values())
        assert len(emails) >= 1, "Expected at least 1 email after execution"
        
        # Find our email
        calendar_email = None
        for email in emails:
            if email.get("from_address") == "calendar@company.com":
                calendar_email = email
                break
        
        assert calendar_email is not None, "Calendar email not found"
        
        # Verify all fields match event data
        event_data = event["data"]
        assert calendar_email["from_address"] == event_data["from_address"]
        assert calendar_email["subject"] == event_data["subject"]
        assert calendar_email["body_text"] == event_data["body_text"]
        assert "user@example.com" in calendar_email.get("to_addresses", [])

    def test_stop_returns_accurate_execution_counts(self, client_with_engine):
        """Verify simulation stop returns accurate event execution statistics.
        
        This test creates events, executes some, and verifies the stop
        response accurately reflects what was executed.
        """
        client, engine = client_with_engine
        from datetime import datetime

        # Get simulation time
        time_response = client.get("/simulator/time")
        base_time = datetime.fromisoformat(time_response.json()["current_time"])

        # Create 3 events at different times
        event1 = EMAIL_1_CALENDAR_REMINDER.at_offset(seconds=10).build(base_time)
        event2 = EMAIL_2_COWORKER.at_offset(seconds=20).build(base_time)
        event3 = EMAIL_3_AUTOMATED_REPORT.at_offset(seconds=1000).build(base_time)  # Far future
        
        client.post("/events", json=event1)
        client.post("/events", json=event2)
        client.post("/events", json=event3)

        # Advance time to execute first two only
        client.post("/simulator/time/advance", json={"seconds": 30})

        # Verify email state shows 2 emails
        email_state = client.get("/email/state").json()
        assert email_state["total_email_count"] == 2

        # Stop simulation
        stop_response = client.post("/simulation/stop").json()
        
        assert stop_response["status"] == "stopped"
        assert stop_response["events_executed"] == 2, (
            f"Expected 2 executed events, got {stop_response['events_executed']}"
        )

    def test_event_execution_updates_correct_modality_only(self, client_with_engine):
        """Verify email events only update email state, not other modalities.
        
        This ensures events don't accidentally affect unrelated state.
        """
        client, engine = client_with_engine
        from datetime import datetime

        # Get simulation time
        time_response = client.get("/simulator/time")
        base_time = datetime.fromisoformat(time_response.json()["current_time"])

        # Capture initial state of multiple modalities
        initial_email = client.get("/email/state").json()
        initial_chat = client.get("/chat/state").json()
        initial_sms = client.get("/sms/state").json()
        
        initial_email_count = initial_email.get("total_email_count", 0)
        initial_chat_count = len(initial_chat.get("conversations", {}))
        initial_sms_convos = len(initial_sms.get("conversations", {}))

        # Execute an email event
        event = EMAIL_1_CALENDAR_REMINDER.at_offset(seconds=0).build(base_time)
        client.post("/events/immediate", json={
            "modality": "email",
            "data": event["data"],
        })
        
        # Advance time to execute the event
        client.post("/simulator/time/advance", json={"seconds": 0.001})

        # Verify email state changed
        final_email = client.get("/email/state").json()
        assert final_email["total_email_count"] == initial_email_count + 1

        # Verify other modalities unchanged
        final_chat = client.get("/chat/state").json()
        final_sms = client.get("/sms/state").json()
        
        assert len(final_chat.get("conversations", {})) == initial_chat_count, (
            "Chat state should not change from email event"
        )
        assert len(final_sms.get("conversations", {})) == initial_sms_convos, (
            "SMS state should not change from email event"
        )
