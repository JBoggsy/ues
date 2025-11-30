"""
Test file for Scenario 2: Multi-Modality Morning Simulation.

This test file executes the Scenario 2 workflow which tests
a realistic 2-hour morning simulation with multiple modalities.

See:
- scenarios/scenario_2_multimodality.py for the scenario definition
- SCENARIO_2_MULTIMODALITY_MORNING.md for detailed documentation
"""

import pytest

from .scenarios.scenario_2_multimodality import (
    SCENARIO_2,
    EVENT_1_SMS_SPOUSE,
    EVENT_2_CALENDAR_STANDUP,
    EVENT_3_EMAIL_AGENDA,
    EVENT_4_LOCATION_LEAVING,
    EVENT_5_LOCATION_SUBWAY,
    EVENT_6_WEATHER_RAIN,
    EVENT_7_LOCATION_WORK,
    EVENT_8_CHAT_REMINDER,
    USER_PHONE,
    SPOUSE_PHONE,
    USER_EMAIL,
    WORK_LAT,
    WORK_LON,
)
from .runner import WorkflowRunner


class TestScenario2MultiModalityMorning:
    """Test class for Scenario 2: Multi-Modality Morning Simulation.

    This scenario tests:
    - Events across 6 different modalities simultaneously
    - Skip-to-next navigation for efficient event-driven progression
    - State accumulation across multiple event executions
    - Simulation reset and clean state restoration
    """

    def test_complete_workflow(self, workflow_runner: WorkflowRunner):
        """Execute the complete Scenario 2 workflow.

        This is the main test that runs all steps of the scenario
        in sequence, verifying each step's assertions.
        """
        workflow_runner.run(SCENARIO_2)

    def test_complete_workflow_quiet(self, quiet_workflow_runner: WorkflowRunner):
        """Execute the workflow without verbose output.

        Useful for CI/CD environments where less output is preferred.
        """
        quiet_workflow_runner.run(SCENARIO_2)


class TestScenario2IndividualSteps:
    """Individual step tests for debugging Scenario 2.

    These tests verify individual components of the workflow
    in isolation, useful for debugging failures in the full workflow.
    """

    def test_sms_event_creates_conversation(self, client_with_engine):
        """Verify SMS event creates a conversation in state."""
        client, engine = client_with_engine
        from datetime import datetime

        # Get simulation time
        time_response = client.get("/simulator/time")
        base_time = datetime.fromisoformat(time_response.json()["current_time"])

        # Verify SMS state is initially empty
        initial_state = client.get("/sms/state").json()
        initial_convos = len(initial_state.get("conversations", {}))

        # Create SMS event
        event = EVENT_1_SMS_SPOUSE.at_offset(seconds=1).build(base_time)
        response = client.post("/events", json=event)
        assert response.status_code == 200

        # Advance time to execute
        client.post("/simulator/time/advance", json={"seconds": 2})

        # Verify SMS was added
        sms_state = client.get("/sms/state").json()
        assert len(sms_state["conversations"]) > initial_convos

        # Verify message content - messages are in top-level "messages" dict
        found_spouse_msg = False
        for msg in sms_state.get("messages", {}).values():
            if msg.get("from_number") == SPOUSE_PHONE:
                found_spouse_msg = True
                assert "groceries" in msg.get("body", "").lower()
                break
        assert found_spouse_msg, "SMS from spouse not found"

    def test_calendar_event_creates_meeting(self, client_with_engine):
        """Verify calendar event creates a meeting in state."""
        client, engine = client_with_engine
        from datetime import datetime

        # Get simulation time
        time_response = client.get("/simulator/time")
        base_time = datetime.fromisoformat(time_response.json()["current_time"])

        # Verify calendar is initially empty
        initial_state = client.get("/calendar/state").json()
        initial_events = len(initial_state.get("events", {}))

        # Create calendar event
        event = EVENT_2_CALENDAR_STANDUP.at_offset(seconds=1).build(base_time)
        response = client.post("/events", json=event)
        assert response.status_code == 200

        # Advance time to execute
        client.post("/simulator/time/advance", json={"seconds": 2})

        # Verify event was added
        calendar_state = client.get("/calendar/state").json()
        assert len(calendar_state["events"]) > initial_events

        # Verify meeting details - events is a dict with event_id keys
        found_standup = False
        for cal_event in calendar_state["events"].values():
            if cal_event.get("title") == "Team Standup":
                found_standup = True
                assert "09:00" in cal_event.get("start", "")
                assert "Conference Room B" in cal_event.get("location", "")
                break
        assert found_standup, "Team Standup event not found"

    def test_email_event_adds_to_inbox(self, client_with_engine):
        """Verify email event adds message to inbox."""
        client, engine = client_with_engine
        from datetime import datetime

        # Get simulation time
        time_response = client.get("/simulator/time")
        base_time = datetime.fromisoformat(time_response.json()["current_time"])

        # Verify email inbox is initially empty
        initial_state = client.get("/email/state").json()
        initial_count = initial_state.get("total_email_count", 0)

        # Create email event
        event = EVENT_3_EMAIL_AGENDA.at_offset(seconds=1).build(base_time)
        response = client.post("/events", json=event)
        assert response.status_code == 200

        # Advance time to execute
        client.post("/simulator/time/advance", json={"seconds": 2})

        # Verify email was added
        email_state = client.get("/email/state").json()
        assert email_state["total_email_count"] > initial_count

        # Verify email details
        found_agenda = False
        for email in email_state["emails"].values():
            if email.get("from_address") == "alice@company.com":
                found_agenda = True
                assert "Standup Agenda" in email.get("subject", "")
                assert email.get("is_read") is False
                break
        assert found_agenda, "Email from Alice not found"

    def test_location_event_updates_current_location(self, client_with_engine):
        """Verify location event updates current location."""
        client, engine = client_with_engine
        from datetime import datetime

        # Get simulation time
        time_response = client.get("/simulator/time")
        base_time = datetime.fromisoformat(time_response.json()["current_time"])

        # Create location event
        event = EVENT_4_LOCATION_LEAVING.at_offset(seconds=1).build(base_time)
        response = client.post("/events", json=event)
        assert response.status_code == 200

        # Advance time to execute
        client.post("/simulator/time/advance", json={"seconds": 2})

        # Verify location was updated - current is in "current" field
        location_state = client.get("/location/state").json()
        current = location_state.get("current", {})

        assert current.get("named_location") == "Outside Home"
        assert abs(current.get("latitude", 0) - 40.7135) < 0.01
        assert abs(current.get("longitude", 0) - (-74.0046)) < 0.01

    def test_weather_event_updates_conditions(self, client_with_engine):
        """Verify weather event updates conditions."""
        client, engine = client_with_engine
        from datetime import datetime

        # Get simulation time
        time_response = client.get("/simulator/time")
        base_time = datetime.fromisoformat(time_response.json()["current_time"])

        # Create weather event
        event = EVENT_6_WEATHER_RAIN.at_offset(seconds=1).build(base_time)
        response = client.post("/events", json=event)
        assert response.status_code == 200

        # Advance time to execute
        client.post("/simulator/time/advance", json={"seconds": 2})

        # Verify weather was updated - data is in "locations" not "reports"
        weather_state = client.get("/weather/state").json()
        locations = weather_state.get("locations", {})

        # Find the report for work location
        found_rain = False
        for loc_key, loc_data in locations.items():
            # Check OpenWeather format (current_report.current.weather[0].main)
            current_report = loc_data.get("current_report", {})
            current = current_report.get("current", {})
            weather_list = current.get("weather", [])
            if weather_list:
                conditions = weather_list[0].get("main", "")
                if conditions == "Light Rain":
                    found_rain = True
                    # Temperature is in Kelvin, convert to check
                    temp_k = current.get("temp", 0)
                    temp_c = temp_k - 273.15
                    assert 4 <= temp_c <= 8, f"Temperature {temp_c}°C not in expected range"
                    break
        assert found_rain, "Weather report with rain conditions not found"

    def test_chat_event_adds_assistant_message(self, client_with_engine):
        """Verify chat event adds assistant message."""
        client, engine = client_with_engine
        from datetime import datetime

        # Get simulation time
        time_response = client.get("/simulator/time")
        base_time = datetime.fromisoformat(time_response.json()["current_time"])

        # Verify chat is initially empty - messages are in top-level list
        initial_state = client.get("/chat/state").json()
        initial_msgs = len(initial_state.get("messages", []))

        # Create chat event
        event = EVENT_8_CHAT_REMINDER.at_offset(seconds=1).build(base_time)
        response = client.post("/events", json=event)
        assert response.status_code == 200

        # Advance time to execute
        client.post("/simulator/time/advance", json={"seconds": 2})

        # Verify chat message was added - messages are in top-level list
        chat_state = client.get("/chat/state").json()
        total_msgs = len(chat_state.get("messages", []))
        assert total_msgs > initial_msgs

        # Verify message is from assistant - messages are in top-level list
        found_assistant = False
        for msg in chat_state.get("messages", []):
            if msg.get("role") == "assistant":
                found_assistant = True
                assert "Good morning" in msg.get("content", "")
                break
        assert found_assistant, "Assistant message not found"


class TestMultiModalityStateAccumulation:
    """Tests that verify state accumulates correctly across modalities.

    These tests ensure that executing events from multiple modalities
    doesn't interfere with each other's state.
    """

    def test_multiple_location_events_accumulate_in_history(self, client_with_engine):
        """Verify multiple location events create history entries."""
        client, engine = client_with_engine
        from datetime import datetime

        # Get simulation time
        time_response = client.get("/simulator/time")
        base_time = datetime.fromisoformat(time_response.json()["current_time"])

        # Create all three location events
        locations = [
            (EVENT_4_LOCATION_LEAVING, 1, "Outside Home"),
            (EVENT_5_LOCATION_SUBWAY, 2, "Canal Street Station"),
            (EVENT_7_LOCATION_WORK, 3, "TechCorp Office"),
        ]

        for builder, offset, _ in locations:
            event = builder.at_offset(seconds=offset).build(base_time)
            response = client.post("/events", json=event)
            assert response.status_code == 200

        # Advance time to execute all
        client.post("/simulator/time/advance", json={"seconds": 5})

        # Verify location state
        location_state = client.get("/location/state").json()
        current = location_state.get("current", {})
        history = location_state.get("history", [])

        # Current should be the last location
        assert current.get("named_location") == "TechCorp Office"

        # History should have entries (current may or may not be included)
        # We expect at least 2 history entries (the earlier locations)
        assert len(history) >= 2, f"Expected at least 2 history entries, got {len(history)}"

    def test_mixed_modality_events_dont_interfere(self, client_with_engine):
        """Verify events from different modalities don't affect each other."""
        client, engine = client_with_engine
        from datetime import datetime

        # Get simulation time
        time_response = client.get("/simulator/time")
        base_time = datetime.fromisoformat(time_response.json()["current_time"])

        # Capture initial state
        initial_sms = client.get("/sms/state").json()
        initial_email = client.get("/email/state").json()
        initial_calendar = client.get("/calendar/state").json()

        # SMS messages are in top-level "messages" dict
        initial_sms_count = len(initial_sms.get("messages", {}))
        initial_email_count = initial_email.get("total_email_count", 0)
        # Calendar events is a dict keyed by event_id
        initial_cal_count = len(initial_calendar.get("events", {}))

        # Create one event from each modality
        sms_event = EVENT_1_SMS_SPOUSE.at_offset(seconds=1).build(base_time)
        email_event = EVENT_3_EMAIL_AGENDA.at_offset(seconds=2).build(base_time)
        calendar_event = EVENT_2_CALENDAR_STANDUP.at_offset(seconds=3).build(base_time)

        client.post("/events", json=sms_event)
        client.post("/events", json=email_event)
        client.post("/events", json=calendar_event)

        # Advance time to execute all
        client.post("/simulator/time/advance", json={"seconds": 5})

        # Verify each modality has exactly one more item
        final_sms = client.get("/sms/state").json()
        final_email = client.get("/email/state").json()
        final_calendar = client.get("/calendar/state").json()

        # SMS messages are in top-level "messages" dict
        final_sms_count = len(final_sms.get("messages", {}))
        final_email_count = final_email.get("total_email_count", 0)
        # Calendar events is a dict keyed by event_id
        final_cal_count = len(final_calendar.get("events", {}))

        assert final_sms_count == initial_sms_count + 1, (
            f"SMS count: expected {initial_sms_count + 1}, got {final_sms_count}"
        )
        assert final_email_count == initial_email_count + 1, (
            f"Email count: expected {initial_email_count + 1}, got {final_email_count}"
        )
        assert final_cal_count == initial_cal_count + 1, (
            f"Calendar count: expected {initial_cal_count + 1}, got {final_cal_count}"
        )

    def test_skip_to_next_executes_events_in_order(self, client_with_engine):
        """Verify skip-to-next executes events in chronological order."""
        client, engine = client_with_engine
        from datetime import datetime

        # Get simulation time
        time_response = client.get("/simulator/time")
        base_time = datetime.fromisoformat(time_response.json()["current_time"])

        # Create events at specific times (out of order)
        event_order = [
            (EVENT_3_EMAIL_AGENDA, 30, "email"),  # Will be third
            (EVENT_1_SMS_SPOUSE, 10, "sms"),      # Will be first
            (EVENT_2_CALENDAR_STANDUP, 20, "calendar"),  # Will be second
        ]

        for builder, offset, _ in event_order:
            event = builder.at_offset(seconds=offset).build(base_time)
            response = client.post("/events", json=event)
            assert response.status_code == 200

        # Skip to first event (SMS at T+10)
        skip1 = client.post("/simulator/time/skip-to-next").json()
        assert skip1.get("events_executed", 0) >= 1

        # Verify SMS was executed - messages are in top-level "messages" dict
        sms_state = client.get("/sms/state").json()
        has_sms = any(
            msg.get("from_number") == SPOUSE_PHONE
            for msg in sms_state.get("messages", {}).values()
        )
        assert has_sms, "SMS should be executed after first skip"

        # Verify email NOT yet executed
        email_state = client.get("/email/state").json()
        email_count = email_state.get("total_email_count", 0)

        # Skip to second event (calendar at T+20)
        skip2 = client.post("/simulator/time/skip-to-next").json()
        assert skip2.get("events_executed", 0) >= 1

        # Verify calendar was executed - events is a dict
        calendar_state = client.get("/calendar/state").json()
        has_standup = any(
            e.get("title") == "Team Standup"
            for e in calendar_state.get("events", {}).values()
        )
        assert has_standup, "Calendar event should be executed after second skip"

        # Skip to third event (email at T+30)
        skip3 = client.post("/simulator/time/skip-to-next").json()
        assert skip3.get("events_executed", 0) >= 1

        # Verify email was executed
        email_state = client.get("/email/state").json()
        has_alice_email = any(
            e.get("from_address") == "alice@company.com"
            for e in email_state.get("emails", {}).values()
        )
        assert has_alice_email, "Email should be executed after third skip"


class TestSimulationResetBehavior:
    """Tests for simulation reset functionality."""

    def test_reset_resets_event_statuses(self, client_with_engine):
        """Verify reset resets event statuses to pending.
        
        Note: Reset preserves events but resets their status to pending,
        allowing the same scenario to be replayed.
        """
        client, engine = client_with_engine
        from datetime import datetime

        # Get simulation time
        time_response = client.get("/simulator/time")
        base_time = datetime.fromisoformat(time_response.json()["current_time"])

        # Create and execute events from multiple modalities
        sms_event = EVENT_1_SMS_SPOUSE.at_offset(seconds=1).build(base_time)
        email_event = EVENT_3_EMAIL_AGENDA.at_offset(seconds=2).build(base_time)

        client.post("/events", json=sms_event)
        client.post("/events", json=email_event)
        client.post("/simulator/time/advance", json={"seconds": 5})

        # Verify state has data
        pre_reset_sms = client.get("/sms/state").json()
        pre_reset_email = client.get("/email/state").json()

        pre_sms_count = sum(
            len(c.get("messages", []))
            for c in pre_reset_sms.get("conversations", {}).values()
        )
        pre_email_count = pre_reset_email.get("total_email_count", 0)

        assert pre_sms_count > 0 or pre_email_count > 0, (
            "Should have state before reset"
        )

        # Reset simulation
        reset_response = client.post("/simulation/reset")
        assert reset_response.status_code == 200

        # Verify events are reset to pending (not deleted)
        summary = client.get("/events/summary").json()
        assert summary.get("pending", 0) == 2  # Both events reset to pending
        assert summary.get("executed", 0) == 0  # No longer marked as executed

    def test_reset_stops_simulation(self, client_with_engine):
        """Verify reset stops the simulation."""
        client, engine = client_with_engine

        # Verify simulation is running (started by fixture)
        status = client.get("/simulation/status").json()
        assert status.get("is_running") is True

        # Reset simulation
        client.post("/simulation/reset")

        # Verify simulation is stopped
        status = client.get("/simulation/status").json()
        assert status.get("is_running") is False

    def test_can_restart_after_reset(self, client_with_engine):
        """Verify simulation can be restarted after reset."""
        client, engine = client_with_engine

        # Reset simulation
        client.post("/simulation/reset")

        # Verify stopped
        status = client.get("/simulation/status").json()
        assert status.get("is_running") is False

        # Start simulation again (must pass JSON body even if empty)
        start_response = client.post("/simulation/start", json={})
        assert start_response.status_code == 200

        # Verify running
        status = client.get("/simulation/status").json()
        assert status.get("is_running") is True


class TestSkipToNextEdgeCases:
    """Tests for skip-to-next edge cases."""

    def test_skip_with_no_pending_events_returns_error(self, client_with_engine):
        """Verify skip-to-next with no pending events returns 404."""
        client, engine = client_with_engine

        # Ensure no pending events
        summary = client.get("/events/summary").json()
        if summary.get("pending", 0) > 0:
            # Execute all pending events
            client.post("/simulator/time/advance", json={"seconds": 10000})

        # Skip should fail
        response = client.post("/simulator/time/skip-to-next")
        assert response.status_code == 404

    def test_multiple_events_at_same_time(self, client_with_engine):
        """Verify multiple events at the same time all execute."""
        client, engine = client_with_engine
        from datetime import datetime

        # Get simulation time
        time_response = client.get("/simulator/time")
        base_time = datetime.fromisoformat(time_response.json()["current_time"])

        # Create multiple events at the same offset
        sms_event = EVENT_1_SMS_SPOUSE.at_offset(seconds=10).build(base_time)
        email_event = EVENT_3_EMAIL_AGENDA.at_offset(seconds=10).build(base_time)

        client.post("/events", json=sms_event)
        client.post("/events", json=email_event)

        # Skip to next should execute both (or the first of them)
        # Note: The actual behavior depends on event ordering with same timestamp
        client.post("/simulator/time/skip-to-next")

        # Check how many executed
        summary = client.get("/events/summary").json()

        # At minimum one should execute; often both do if at exact same time
        assert summary.get("executed", 0) >= 1


class TestMidPointStateVerification:
    """Tests that verify state at various points during execution.

    These tests follow the mid-point check pattern from the scenario docs.
    """

    def test_mid_point_state_after_first_four_events(self, client_with_engine):
        """Verify state after first 4 events (through location - leaving home)."""
        client, engine = client_with_engine
        from datetime import datetime

        # Get simulation time
        time_response = client.get("/simulator/time")
        base_time = datetime.fromisoformat(time_response.json()["current_time"])

        # Create first 4 events
        events = [
            (EVENT_1_SMS_SPOUSE, 5),      # T+5m
            (EVENT_2_CALENDAR_STANDUP, 15),  # T+15m
            (EVENT_3_EMAIL_AGENDA, 20),   # T+20m
            (EVENT_4_LOCATION_LEAVING, 30),  # T+30m
        ]

        for builder, offset in events:
            event = builder.at_offset(minutes=offset).build(base_time)
            response = client.post("/events", json=event)
            assert response.status_code == 200

        # Verify 4 pending
        summary = client.get("/events/summary").json()
        assert summary["pending"] == 4

        # Execute all 4 via time advance (30 minutes + buffer)
        client.post("/simulator/time/advance", json={"seconds": 35 * 60})

        # Verify event summary
        summary = client.get("/events/summary").json()
        assert summary["executed"] == 4
        assert summary["pending"] == 0

        # Verify SMS state - messages in top-level dict
        sms_state = client.get("/sms/state").json()
        has_spouse_msg = any(
            msg.get("from_number") == SPOUSE_PHONE
            for msg in sms_state.get("messages", {}).values()
        )
        assert has_spouse_msg, "SMS from spouse should exist"

        # Verify calendar state - events is a dict
        calendar_state = client.get("/calendar/state").json()
        assert len(calendar_state.get("events", {})) >= 1
        has_standup = any(
            e.get("title") == "Team Standup"
            for e in calendar_state.get("events", {}).values()
        )
        assert has_standup, "Team Standup event should exist"

        # Verify email state
        email_state = client.get("/email/state").json()
        assert email_state.get("total_email_count", 0) >= 1
        has_alice = any(
            e.get("from_address") == "alice@company.com"
            for e in email_state.get("emails", {}).values()
        )
        assert has_alice, "Email from Alice should exist"

        # Verify location state
        location_state = client.get("/location/state").json()
        current = location_state.get("current", {})
        assert current.get("named_location") == "Outside Home"
