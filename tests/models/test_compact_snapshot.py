"""Unit tests for compact snapshot functionality across all modality states.

These tests verify that each modality's get_compact_snapshot() method returns
appropriately sized, LLM-context-optimized data structures.
"""

from datetime import datetime, timedelta, timezone

import pytest

# Shared test timestamp
NOW = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)


class TestBaseStateCompactSnapshot:
    """Test default compact snapshot behavior from ModalityState base class."""

    def test_format_relative_time_future(self):
        """Test _format_relative_time for future times."""
        from ues.models.base_state import ModalityState

        now = NOW

        # 30 minutes from now
        future = now + timedelta(minutes=30)
        result = ModalityState._format_relative_time(future, now)
        assert result == "in 30 minutes"

        # 2 hours from now
        future = now + timedelta(hours=2)
        result = ModalityState._format_relative_time(future, now)
        assert result == "in 2 hours"

        # 1 day from now
        future = now + timedelta(days=1)
        result = ModalityState._format_relative_time(future, now)
        assert result == "in 1 day"

    def test_format_relative_time_past(self):
        """Test _format_relative_time for past times."""
        from ues.models.base_state import ModalityState

        now = NOW

        # 30 minutes ago
        past = now - timedelta(minutes=30)
        result = ModalityState._format_relative_time(past, now)
        assert result == "30 minutes ago"

        # 2 hours ago
        past = now - timedelta(hours=2)
        result = ModalityState._format_relative_time(past, now)
        assert result == "2 hours ago"

    def test_format_relative_time_singular(self):
        """Test _format_relative_time uses singular forms correctly."""
        from ues.models.base_state import ModalityState

        now = NOW

        # 1 minute
        future = now + timedelta(minutes=1)
        result = ModalityState._format_relative_time(future, now)
        assert result == "in 1 minute"

        # 1 hour
        future = now + timedelta(hours=1)
        result = ModalityState._format_relative_time(future, now)
        assert result == "in 1 hour"


class TestLocationCompactSnapshot:
    """Test LocationState.get_compact_snapshot()."""

    def test_compact_snapshot_with_location(self):
        """Test compact snapshot includes current location info."""
        from ues.models.modalities.location_state import LocationState

        state = LocationState(last_updated=NOW)
        
        # Set a location using the correct field names
        state.current_latitude = 37.7749
        state.current_longitude = -122.4194
        state.current_address = "123 Main St, San Francisco, CA"
        state.current_named_location = "Office"

        snapshot = state.get_compact_snapshot(NOW)

        assert "summary" in snapshot
        assert "current" in snapshot
        current = snapshot["current"]
        assert current["latitude"] == 37.7749
        assert current["longitude"] == -122.4194
        assert current["address"] == "123 Main St, San Francisco, CA"
        assert current["named_location"] == "Office"

    def test_compact_snapshot_no_location(self):
        """Test compact snapshot when no location is set."""
        from ues.models.modalities.location_state import LocationState

        state = LocationState(last_updated=NOW)

        snapshot = state.get_compact_snapshot(NOW)

        assert "summary" in snapshot
        assert snapshot["current"] is None


class TestTimeCompactSnapshot:
    """Test TimeState.get_compact_snapshot()."""

    def test_compact_snapshot_includes_preferences(self):
        """Test compact snapshot includes timezone and format preferences."""
        from ues.models.modalities.time_state import TimeState

        state = TimeState(last_updated=NOW)

        snapshot = state.get_compact_snapshot(NOW)

        assert "summary" in snapshot
        assert "timezone" in snapshot
        assert "format_24h" in snapshot
        # Default is UTC and 12h format
        assert snapshot["timezone"] == "UTC"
        assert snapshot["format_24h"] is False


class TestWeatherCompactSnapshot:
    """Test WeatherState.get_compact_snapshot()."""

    def test_compact_snapshot_with_weather(self):
        """Test compact snapshot includes current weather conditions."""
        from ues.models.modalities.weather_input import (
            CurrentWeather,
            WeatherCondition,
            WeatherInput,
            WeatherReport,
        )
        from ues.models.modalities.weather_state import WeatherState

        state = WeatherState(last_updated=NOW)

        # Create a weather report in OpenWeather format
        current_weather = CurrentWeather(
            dt=int(NOW.timestamp()),
            sunrise=int((NOW - timedelta(hours=6)).timestamp()),
            sunset=int((NOW + timedelta(hours=6)).timestamp()),
            temp=293.15,  # 20°C in Kelvin
            feels_like=295.15,
            pressure=1013,
            humidity=45,
            dew_point=282.15,
            uvi=5.0,
            clouds=10,
            visibility=10000,
            wind_speed=3.5,
            wind_deg=315,
            weather=[
                WeatherCondition(
                    id=800,
                    main="Clear",
                    description="clear sky",
                    icon="01d",
                )
            ],
        )
        report = WeatherReport(
            lat=37.7749,
            lon=-122.4194,
            timezone="America/Los_Angeles",
            timezone_offset=-28800,
            current=current_weather,
        )

        # Apply via input
        weather_input = WeatherInput(
            latitude=37.7749,
            longitude=-122.4194,
            report=report,
            timestamp=NOW,
        )
        state.apply_input(weather_input)

        snapshot = state.get_compact_snapshot(NOW)

        assert "summary" in snapshot
        assert "location_count" in snapshot
        assert snapshot["location_count"] == 1
        assert "current" in snapshot
        current = snapshot["current"]
        assert current is not None
        assert "location" in current
        assert current["condition"] == "Clear"
        assert current["temperature_c"] == 20.0

    def test_compact_snapshot_no_weather(self):
        """Test compact snapshot when no weather data is available."""
        from ues.models.modalities.weather_state import WeatherState

        state = WeatherState(last_updated=NOW)

        snapshot = state.get_compact_snapshot(NOW)

        assert "summary" in snapshot
        assert snapshot["current"] is None
        assert snapshot["location_count"] == 0


class TestEmailCompactSnapshot:
    """Test EmailState.get_compact_snapshot()."""

    def test_compact_snapshot_with_emails(self):
        """Test compact snapshot includes unread count and recent subjects."""
        from ues.models.modalities.email_input import EmailInput
        from ues.models.modalities.email_state import EmailState

        state = EmailState(last_updated=NOW)

        # Receive emails via apply_input
        email1 = EmailInput(
            operation="receive",
            from_address="alice@example.com",
            from_name="Alice",
            to_addresses=["user@example.com"],
            subject="Meeting Tomorrow",
            body_text="Let's discuss the project.",
            timestamp=NOW - timedelta(hours=1),
        )
        state.apply_input(email1)

        email2 = EmailInput(
            operation="receive",
            from_address="bob@example.com",
            from_name="Bob",
            to_addresses=["user@example.com"],
            subject="Quick Question",
            body_text="Can you help?",
            timestamp=NOW - timedelta(hours=2),
        )
        state.apply_input(email2)

        snapshot = state.get_compact_snapshot(NOW)

        assert "summary" in snapshot
        assert "unread_count" in snapshot
        assert snapshot["unread_count"] == 2
        assert "total_count" in snapshot
        assert "recent_unread" in snapshot
        assert len(snapshot["recent_unread"]) == 2
        # Most recent should be first (from_name may not be set, falls back to email)
        assert snapshot["recent_unread"][0]["subject"] == "Meeting Tomorrow"

    def test_compact_snapshot_limits_recent(self):
        """Test compact snapshot limits recent emails to 5."""
        from ues.models.modalities.email_input import EmailInput
        from ues.models.modalities.email_state import EmailState

        state = EmailState(last_updated=NOW)

        # Add 10 unread emails
        for i in range(10):
            email = EmailInput(
                operation="receive",
                from_address=f"sender{i}@example.com",
                to_addresses=["user@example.com"],
                subject=f"Subject {i}",
                body_text="Content",
                timestamp=NOW - timedelta(hours=i),
            )
            state.apply_input(email)

        snapshot = state.get_compact_snapshot(NOW)

        assert snapshot["unread_count"] == 10
        assert len(snapshot["recent_unread"]) == 5

    def test_compact_snapshot_no_emails(self):
        """Test compact snapshot when no emails exist."""
        from ues.models.modalities.email_state import EmailState

        state = EmailState(last_updated=NOW)

        snapshot = state.get_compact_snapshot(NOW)

        assert snapshot["unread_count"] == 0
        assert snapshot["recent_unread"] == []
        assert snapshot["flagged_count"] == 0


class TestSMSCompactSnapshot:
    """Test SMSState.get_compact_snapshot()."""

    def test_compact_snapshot_with_messages(self):
        """Test compact snapshot includes unread conversations."""
        from ues.models.modalities.sms_input import SMSInput
        from ues.models.modalities.sms_state import SMSState

        state = SMSState(last_updated=NOW, user_phone_number="+10000000000")

        # Receive a message via apply_input
        msg = SMSInput(
            action="receive_message",
            timestamp=NOW - timedelta(minutes=30),
            message_data={
                "from_number": "+15551234567",
                "to_numbers": ["+10000000000"],
                "body": "Hey, are you free?",
                "message_type": "sms",
            },
        )
        state.apply_input(msg)

        snapshot = state.get_compact_snapshot(NOW)

        assert "summary" in snapshot
        assert "total_unread" in snapshot
        assert snapshot["total_unread"] == 1
        assert "unread_conversations" in snapshot
        assert len(snapshot["unread_conversations"]) == 1
        assert snapshot["unread_conversations"][0]["participant"] == "+15551234567"
        assert "last_message" in snapshot["unread_conversations"][0]

    def test_compact_snapshot_no_messages(self):
        """Test compact snapshot when no messages exist."""
        from ues.models.modalities.sms_state import SMSState

        state = SMSState(last_updated=NOW, user_phone_number="+10000000000")

        snapshot = state.get_compact_snapshot(NOW)

        assert snapshot["total_unread"] == 0
        assert snapshot["unread_conversations"] == []


class TestChatCompactSnapshot:
    """Test ChatState.get_compact_snapshot()."""

    def test_compact_snapshot_with_messages(self):
        """Test compact snapshot includes last exchange."""
        from ues.models.modalities.chat_input import ChatInput
        from ues.models.modalities.chat_state import ChatState

        state = ChatState(last_updated=NOW)

        # Add messages via apply_input
        user_msg = ChatInput(
            operation="send_message",
            role="user",
            content="What's the weather?",
            timestamp=NOW - timedelta(minutes=5),
        )
        state.apply_input(user_msg)

        assistant_msg = ChatInput(
            operation="send_message",
            role="assistant",
            content="It's sunny and 72°F.",
            timestamp=NOW - timedelta(minutes=4),
        )
        state.apply_input(assistant_msg)

        snapshot = state.get_compact_snapshot(NOW)

        assert "summary" in snapshot
        assert "message_count" in snapshot
        assert snapshot["message_count"] == 2
        assert "last_user_message" in snapshot
        assert snapshot["last_user_message"] == "What's the weather?"
        assert "last_assistant_message" in snapshot
        assert snapshot["last_assistant_message"] == "It's sunny and 72°F."

    def test_compact_snapshot_no_messages(self):
        """Test compact snapshot when no messages exist."""
        from ues.models.modalities.chat_state import ChatState

        state = ChatState(last_updated=NOW)

        snapshot = state.get_compact_snapshot(NOW)

        assert snapshot["message_count"] == 0
        assert snapshot["last_user_message"] is None
        assert snapshot["last_assistant_message"] is None


class TestCalendarCompactSnapshot:
    """Test CalendarState.get_compact_snapshot()."""

    def test_compact_snapshot_with_events(self):
        """Test compact snapshot includes current and next events."""
        from ues.models.modalities.calendar_input import CalendarInput
        from ues.models.modalities.calendar_state import CalendarState

        state = CalendarState(last_updated=NOW)

        # Add events via apply_input
        current_event = CalendarInput(
            operation="create",
            event_id="ev1",
            title="Team Meeting",
            start=NOW - timedelta(minutes=30),
            end=NOW + timedelta(minutes=30),
            timestamp=NOW,
        )
        state.apply_input(current_event)

        next_event = CalendarInput(
            operation="create",
            event_id="ev2",
            title="Lunch Break",
            start=NOW + timedelta(hours=2),
            end=NOW + timedelta(hours=3),
            timestamp=NOW,
        )
        state.apply_input(next_event)

        snapshot = state.get_compact_snapshot(NOW)

        assert "summary" in snapshot
        assert "total_events" in snapshot
        assert snapshot["total_events"] == 2
        assert "current_event" in snapshot
        assert snapshot["current_event"]["title"] == "Team Meeting"
        assert "next_event" in snapshot
        assert snapshot["next_event"]["title"] == "Lunch Break"
        assert "today_count" in snapshot
        assert snapshot["today_count"] == 2

    def test_compact_snapshot_no_events(self):
        """Test compact snapshot when no events exist."""
        from ues.models.modalities.calendar_state import CalendarState

        state = CalendarState(last_updated=NOW)

        snapshot = state.get_compact_snapshot(NOW)

        assert snapshot["current_event"] is None
        assert snapshot["next_event"] is None
        assert snapshot["today_count"] == 0


class TestEnvironmentCompactSnapshot:
    """Test Environment.get_compact_snapshot() and get_compact_snapshot_text()."""

    def test_environment_compact_snapshot(self):
        """Test environment returns compact snapshots for all modalities."""
        from tests.fixtures.core.environments import create_environment
        from tests.fixtures.modalities import (
            calendar,
            chat,
            email,
            location,
            sms,
            time,
            weather,
        )

        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
                "time": time.create_time_state(),
                "weather": weather.create_weather_state(),
                "email": email.create_email_state(),
                "sms": sms.create_sms_state(),
                "chat": chat.create_chat_state(),
                "calendar": calendar.create_calendar_state(),
            }
        )
        env.time_state.current_time = NOW

        snapshot = env.get_compact_snapshot()

        assert "snapshot_time" in snapshot
        assert "modalities" in snapshot
        modalities = snapshot["modalities"]
        
        # All modalities should be present
        assert "location" in modalities
        assert "time" in modalities
        assert "weather" in modalities
        assert "email" in modalities
        assert "sms" in modalities
        assert "chat" in modalities
        assert "calendar" in modalities

    def test_environment_compact_snapshot_text(self):
        """Test environment returns LLM-formatted text."""
        from tests.fixtures.core.environments import create_environment
        from tests.fixtures.modalities import (
            calendar,
            chat,
            email,
            location,
            sms,
            time,
            weather,
        )

        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
                "time": time.create_time_state(),
                "weather": weather.create_weather_state(),
                "email": email.create_email_state(),
                "sms": sms.create_sms_state(),
                "chat": chat.create_chat_state(),
                "calendar": calendar.create_calendar_state(),
            }
        )
        env.time_state.current_time = NOW

        text = env.get_compact_snapshot_text()

        assert isinstance(text, str)
        # Check for some expected content
        assert len(text) > 0
        # Check for emoji formatting (at least one should be present)
        assert any(emoji in text for emoji in ["📅", "📍", "📧", "💬", "📱", "🌤", "⏰"])
