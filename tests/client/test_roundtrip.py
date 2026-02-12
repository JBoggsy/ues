"""Round-trip deserialization tests: Server model → JSON → Client model.

These tests verify that server-side Pydantic models, when serialized to JSON
(as the API would), can be correctly deserialized into the corresponding
client-side Pydantic models with all field values preserved.

This catches:
  - Field name mismatches (value silently becomes None/default)
  - Enum value mismatches (validation errors)
  - Structural mismatches (nested models fail to parse)
  - Serialization format mismatches (e.g., datetime → string format differences)

Background:
    The schema sync tests (test_model_schema_sync.py) compare field names and
    types at the class level.  These round-trip tests go further by exercising
    the actual serialization/deserialization path with realistic data, catching
    issues that static schema comparison cannot detect (e.g., custom field
    serializers that change field names or formats).

    See ``docs/client/CLIENT_SERVER_AUDIT.md`` for the original audit and
    ``docs/client/CLIENT_SERVER_REMEDIATION_PLAN.md`` for Phase 5.2.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

# ---------------------------------------------------------------------------
# Server models
# ---------------------------------------------------------------------------
from ues.models.modalities.calendar_input import (
    Attachment as ServerAttachment,
    Attendee as ServerAttendee,
    RecurrenceRule as ServerRecurrenceRule,
    Reminder as ServerReminder,
)
from ues.models.modalities.calendar_state import (
    Calendar as ServerCalendar,
    CalendarEvent as ServerCalendarEvent,
)
from ues.models.modalities.chat_state import (
    ChatMessage as ServerChatMessage,
    ConversationMetadata as ServerConversationMetadata,
)
from ues.models.modalities.contacts_input import (
    ContactIdentifier as ServerContactIdentifier,
    PostalAddress as ServerPostalAddress,
)
from ues.models.modalities.contacts_state import (
    Contact as ServerContact,
)
from ues.models.modalities.email_input import (
    EmailAttachment as ServerEmailAttachment,
)
from ues.models.modalities.email_state import (
    Email as ServerEmail,
    EmailSummary as ServerEmailSummary,
    EmailThread as ServerEmailThread,
)
from ues.models.modalities.sms_state import (
    GroupParticipant as ServerGroupParticipant,
    MessageAttachment as ServerMessageAttachment,
    MessageReaction as ServerMessageReaction,
    SMSConversation as ServerSMSConversation,
    SMSMessage as ServerSMSMessage,
)
from ues.models.modalities.weather_input import (
    CurrentWeather as ServerCurrentWeather,
    DailyFeelsLike as ServerDailyFeelsLike,
    DailyForecast as ServerDailyForecast,
    DailyTemperature as ServerDailyTemperature,
    HourlyForecast as ServerHourlyForecast,
    MinutelyForecast as ServerMinutelyForecast,
    WeatherAlert as ServerWeatherAlert,
    WeatherCondition as ServerWeatherCondition,
    WeatherReport as ServerWeatherReport,
)

# ---------------------------------------------------------------------------
# Client models
# ---------------------------------------------------------------------------
from ues.client._calendar import (
    Attachment as ClientAttachment,
    Attendee as ClientAttendee,
    CalendarContainer as ClientCalendar,
    CalendarEvent as ClientCalendarEvent,
    RecurrenceRule as ClientRecurrenceRule,
    Reminder as ClientReminder,
)
from ues.client._chat import (
    ChatMessage as ClientChatMessage,
    ConversationMetadata as ClientConversationMetadata,
)
from ues.client._contacts import (
    Contact as ClientContact,
    ContactIdentifier as ClientContactIdentifier,
    PostalAddress as ClientPostalAddress,
)
from ues.client._email import (
    Email as ClientEmail,
    EmailAttachment as ClientEmailAttachment,
    EmailSummary as ClientEmailSummary,
    EmailThread as ClientEmailThread,
)
from ues.client._sms import (
    GroupParticipant as ClientGroupParticipant,
    MessageAttachment as ClientMessageAttachment,
    MessageReaction as ClientMessageReaction,
    SMSConversation as ClientSMSConversation,
    SMSMessage as ClientSMSMessage,
)
from ues.client._weather import (
    CurrentWeather as ClientCurrentWeather,
    DailyFeelsLike as ClientDailyFeelsLike,
    DailyForecast as ClientDailyForecast,
    DailyTemperature as ClientDailyTemperature,
    HourlyForecast as ClientHourlyForecast,
    MinutelyForecast as ClientMinutelyForecast,
    WeatherAlert as ClientWeatherAlert,
    WeatherCondition as ClientWeatherCondition,
    WeatherReport as ClientWeatherReport,
)


# ===================================================================
# Helpers
# ===================================================================

_NOW = datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc)
_EARLIER = datetime(2026, 2, 10, 10, 0, 0, tzinfo=timezone.utc)


def _roundtrip(server_instance, client_model):
    """Serialize a server model to JSON dict, then deserialize into client model.

    Uses ``model_dump(mode="json")`` which is what FastAPI's JSON response
    serialization does under the hood.

    Args:
        server_instance: A populated server-side Pydantic model instance.
        client_model: The client-side Pydantic model class.

    Returns:
        An instance of ``client_model`` deserialized from the JSON dict.
    """
    json_data = server_instance.model_dump(mode="json")
    return client_model(**json_data)


# ===================================================================
# Email Round-Trip Tests
# ===================================================================


class TestEmailRoundTrip:
    """Round-trip tests for email models."""

    def test_email_attachment_roundtrip(self):
        """EmailAttachment serializes and deserializes with all fields intact."""
        server = ServerEmailAttachment(
            filename="report.pdf",
            size=1024,
            mime_type="application/pdf",
            content_id="cid-001",
        )
        client = _roundtrip(server, ClientEmailAttachment)

        assert client.filename == "report.pdf"
        assert client.size == 1024
        assert client.mime_type == "application/pdf"
        assert client.content_id == "cid-001"
        assert client.attachment_id == server.attachment_id  # UUID preserved

    def test_email_roundtrip(self):
        """Full Email model round-trips with all fields populated."""
        server = ServerEmail(
            message_id="msg-001",
            thread_id="thread-001",
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
            cc_addresses=["cc@example.com"],
            bcc_addresses=["bcc@example.com"],
            reply_to_address="reply@example.com",
            subject="Test Subject",
            body_text="Hello, world!",
            body_html="<p>Hello, world!</p>",
            in_reply_to="msg-000",
            references=["msg-000"],
            sent_at=_EARLIER,
            received_at=_NOW,
            is_read=True,
            is_starred=True,
            priority="high",
            folder="inbox",
            labels=["important", "work"],
        )
        client = _roundtrip(server, ClientEmail)

        assert client.message_id == "msg-001"
        assert client.thread_id == "thread-001"
        assert client.from_address == "sender@example.com"
        assert client.to_addresses == ["recipient@example.com"]
        assert client.cc_addresses == ["cc@example.com"]
        assert client.bcc_addresses == ["bcc@example.com"]
        assert client.reply_to_address == "reply@example.com"
        assert client.subject == "Test Subject"
        assert client.body_text == "Hello, world!"
        assert client.body_html == "<p>Hello, world!</p>"
        assert client.in_reply_to == "msg-000"
        assert client.references == ["msg-000"]
        assert client.is_read is True
        assert client.is_starred is True
        assert client.priority == "high"
        assert client.folder == "inbox"
        assert client.labels == ["important", "work"]

    def test_email_thread_roundtrip(self):
        """EmailThread round-trips including set → list conversion."""
        server = ServerEmailThread(
            thread_id="thread-001",
            subject="Discussion",
            participant_addresses={"alice@example.com", "bob@example.com"},
            message_ids=["msg-001", "msg-002"],
            created_at=_EARLIER,
            last_message_at=_NOW,
            message_count=2,
            unread_count=1,
        )
        client = _roundtrip(server, ClientEmailThread)

        assert client.thread_id == "thread-001"
        assert client.subject == "Discussion"
        # set serializes to list; order is not guaranteed
        assert set(client.participant_addresses) == {
            "alice@example.com",
            "bob@example.com",
        }
        assert client.message_ids == ["msg-001", "msg-002"]
        assert client.message_count == 2
        assert client.unread_count == 1

    def test_email_summary_roundtrip(self):
        """EmailSummary round-trips with all fields."""
        server = ServerEmailSummary(
            message_id="msg-001",
            thread_id="thread-001",
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
            subject="Summary Test",
            sent_at=_EARLIER,
            received_at=_NOW,
            is_read=False,
            is_starred=True,
            folder="inbox",
            has_attachments=True,
            attachment_count=2,
            body_preview="Hello, this is a preview...",
        )
        client = _roundtrip(server, ClientEmailSummary)

        assert client.message_id == "msg-001"
        assert client.subject == "Summary Test"
        assert client.has_attachments is True
        assert client.attachment_count == 2
        assert client.body_preview == "Hello, this is a preview..."


# ===================================================================
# SMS Round-Trip Tests
# ===================================================================


class TestSMSRoundTrip:
    """Round-trip tests for SMS models."""

    def test_message_attachment_roundtrip(self):
        """MessageAttachment round-trips with all fields."""
        server = ServerMessageAttachment(
            filename="photo.jpg",
            size=2048000,
            mime_type="image/jpeg",
            thumbnail_url="https://example.com/thumb.jpg",
            duration=None,
        )
        client = _roundtrip(server, ClientMessageAttachment)

        assert client.filename == "photo.jpg"
        assert client.size == 2048000
        assert client.mime_type == "image/jpeg"
        assert client.attachment_id == server.attachment_id
        assert client.thumbnail_url == "https://example.com/thumb.jpg"
        assert client.duration is None

    def test_message_reaction_roundtrip(self):
        """MessageReaction round-trips with all fields."""
        server = ServerMessageReaction(
            message_id="msg-001",
            phone_number="+15551234567",
            emoji="👍",
            timestamp=_NOW,
        )
        client = _roundtrip(server, ClientMessageReaction)

        assert client.message_id == "msg-001"
        assert client.reaction_id == server.reaction_id
        assert client.phone_number == "+15551234567"
        assert client.emoji == "👍"

    def test_group_participant_roundtrip(self):
        """GroupParticipant round-trips with all fields."""
        server = ServerGroupParticipant(
            phone_number="+15559876543",
            is_admin=True,
            joined_at=_EARLIER,
            left_at=_NOW,
        )
        client = _roundtrip(server, ClientGroupParticipant)

        assert client.phone_number == "+15559876543"
        assert client.is_admin is True
        assert client.left_at is not None

    def test_sms_message_roundtrip(self):
        """Full SMSMessage round-trips with attachments and reactions."""
        attachment = ServerMessageAttachment(
            filename="voice.ogg",
            size=51200,
            mime_type="audio/ogg",
            duration=15,
        )
        reaction = ServerMessageReaction(
            message_id="sms-001",
            phone_number="+15559876543",
            emoji="❤️",
            timestamp=_NOW,
        )
        server = ServerSMSMessage(
            message_id="sms-001",
            thread_id="conv-001",
            from_number="+15551234567",
            to_numbers=["+15559876543"],
            body="Check this out!",
            attachments=[attachment],
            reactions=[reaction],
            message_type="rcs",
            direction="outgoing",
            sent_at=_NOW,
            delivered_at=_NOW,
            is_read=True,
            delivery_status="delivered",
            replied_to_message_id="sms-000",
        )
        client = _roundtrip(server, ClientSMSMessage)

        assert client.message_id == "sms-001"
        assert client.thread_id == "conv-001"
        assert client.from_number == "+15551234567"
        assert client.to_numbers == ["+15559876543"]
        assert client.body == "Check this out!"
        assert len(client.attachments) == 1
        assert client.attachments[0].filename == "voice.ogg"
        assert client.attachments[0].duration == 15
        assert len(client.reactions) == 1
        assert client.reactions[0].emoji == "❤️"
        assert client.message_type == "rcs"
        assert client.direction == "outgoing"
        assert client.delivery_status == "delivered"
        assert client.replied_to_message_id == "sms-000"

    def test_sms_conversation_roundtrip(self):
        """SMSConversation round-trips with group features."""
        participant = ServerGroupParticipant(
            phone_number="+15551234567",
            is_admin=True,
            joined_at=_EARLIER,
        )
        server = ServerSMSConversation(
            thread_id="conv-001",
            conversation_type="group",
            participants=[participant],
            group_name="Work Chat",
            group_photo_url="https://example.com/group.jpg",
            created_at=_EARLIER,
            created_by="+15551234567",
            last_message_at=_NOW,
            message_count=42,
            unread_count=3,
            is_pinned=True,
            is_muted=False,
            is_archived=False,
            draft_message="Hey everyone...",
        )
        client = _roundtrip(server, ClientSMSConversation)

        assert client.thread_id == "conv-001"
        assert client.conversation_type == "group"
        assert len(client.participants) == 1
        assert client.participants[0].phone_number == "+15551234567"
        assert client.participants[0].is_admin is True
        assert client.group_name == "Work Chat"
        assert client.created_by == "+15551234567"
        assert client.message_count == 42
        assert client.unread_count == 3
        assert client.is_pinned is True
        assert client.draft_message == "Hey everyone..."


# ===================================================================
# Calendar Round-Trip Tests
# ===================================================================


class TestCalendarRoundTrip:
    """Round-trip tests for calendar models."""

    def test_attendee_roundtrip(self):
        """Attendee round-trips with all fields."""
        server = ServerAttendee(
            email="attendee@example.com",
            display_name="Alice",
            optional=True,
            response="accepted",
            comment="I'll be there!",
        )
        client = _roundtrip(server, ClientAttendee)

        assert client.email == "attendee@example.com"
        assert client.display_name == "Alice"
        assert client.optional is True
        assert client.response == "accepted"
        assert client.comment == "I'll be there!"

    def test_reminder_roundtrip(self):
        """Reminder round-trips with constraint."""
        server = ServerReminder(minutes_before=30, type="email")
        client = _roundtrip(server, ClientReminder)

        assert client.minutes_before == 30
        assert client.type == "email"

    def test_attachment_roundtrip(self):
        """Attachment round-trips with all fields."""
        server = ServerAttachment(
            filename="slides.pptx",
            size=5120000,
            mime_type="application/vnd.ms-powerpoint",
            url="https://files.example.com/slides.pptx",
            data=None,
        )
        client = _roundtrip(server, ClientAttachment)

        assert client.filename == "slides.pptx"
        assert client.size == 5120000
        assert client.mime_type == "application/vnd.ms-powerpoint"
        assert client.url == "https://files.example.com/slides.pptx"
        assert client.data is None
        assert client.attachment_id == server.attachment_id

    def test_recurrence_rule_roundtrip(self):
        """RecurrenceRule round-trips with all recurrence options."""
        server = ServerRecurrenceRule(
            frequency="weekly",
            interval=2,
            days_of_week=["monday", "wednesday", "friday"],
            end_type="until",
            end_date=date(2026, 6, 30),
        )
        client = _roundtrip(server, ClientRecurrenceRule)

        assert client.frequency == "weekly"
        assert client.interval == 2
        assert client.days_of_week == ["monday", "wednesday", "friday"]
        assert client.end_type == "until"
        assert client.end_date == date(2026, 6, 30)
        assert client.day_of_month is None
        assert client.month_of_year is None

    def test_recurrence_rule_monthly_roundtrip(self):
        """RecurrenceRule with monthly frequency and count end type."""
        server = ServerRecurrenceRule(
            frequency="monthly",
            day_of_month=15,
            end_type="count",
            count=12,
        )
        client = _roundtrip(server, ClientRecurrenceRule)

        assert client.frequency == "monthly"
        assert client.day_of_month == 15
        assert client.end_type == "count"
        assert client.count == 12

    def test_calendar_event_roundtrip(self):
        """Full CalendarEvent round-trips with all sub-models.

        CalendarEvent uses field_serializer for datetime fields, so this test
        exercises the actual JSON serialization path (datetimes → ISO strings).
        """
        attendee = ServerAttendee(
            email="bob@example.com",
            response="tentative",
        )
        reminder = ServerReminder(minutes_before=15, type="notification")
        attachment = ServerAttachment(
            filename="agenda.pdf",
            size=10240,
            mime_type="application/pdf",
        )
        recurrence = ServerRecurrenceRule(
            frequency="daily",
            interval=1,
            end_type="count",
            count=5,
        )

        server = ServerCalendarEvent(
            event_id="evt-001",
            calendar_id="primary",
            title="Team Standup",
            description="Daily sync meeting",
            start=_EARLIER,
            end=_NOW,
            all_day=False,
            timezone="America/New_York",
            location="Conference Room B",
            status="confirmed",
            organizer="manager@example.com",
            attendees=[attendee],
            recurrence=recurrence,
            recurrence_exceptions={"2026-02-15", "2026-02-20"},
            recurrence_id=None,
            parent_event_id="evt-parent",
            reminders=[reminder],
            color="#dc2626",
            visibility="private",
            transparency="opaque",
            attachments=[attachment],
            conference_link="https://meet.example.com/standup",
            created_at=_EARLIER,
            updated_at=_NOW,
            deleted_at=None,
        )
        client = _roundtrip(server, ClientCalendarEvent)

        assert client.event_id == "evt-001"
        assert client.calendar_id == "primary"
        assert client.title == "Team Standup"
        assert client.description == "Daily sync meeting"
        assert client.all_day is False
        assert client.timezone == "America/New_York"
        assert client.location == "Conference Room B"
        assert client.status == "confirmed"
        assert client.organizer == "manager@example.com"

        # Attendees
        assert len(client.attendees) == 1
        assert client.attendees[0].email == "bob@example.com"
        assert client.attendees[0].response == "tentative"

        # Recurrence
        assert client.recurrence is not None
        assert client.recurrence.frequency == "daily"
        assert client.recurrence.count == 5

        # Recurrence exceptions (set → list in JSON → set on client)
        assert client.recurrence_exceptions == {"2026-02-15", "2026-02-20"}

        # Parent event
        assert client.parent_event_id == "evt-parent"
        assert client.recurrence_id is None

        # Reminders
        assert len(client.reminders) == 1
        assert client.reminders[0].minutes_before == 15

        # Attachments
        assert len(client.attachments) == 1
        assert client.attachments[0].filename == "agenda.pdf"

        # Visual properties
        assert client.color == "#dc2626"
        assert client.visibility == "private"
        assert client.transparency == "opaque"
        assert client.conference_link == "https://meet.example.com/standup"

        # Timestamps (serialized to strings by server, parsed back by client)
        assert client.deleted_at is None

    def test_calendar_event_with_deleted_at_roundtrip(self):
        """CalendarEvent with deleted_at populated round-trips correctly."""
        deletion_time = datetime(2026, 2, 11, 8, 0, 0, tzinfo=timezone.utc)
        server = ServerCalendarEvent(
            event_id="evt-deleted",
            calendar_id="primary",
            title="Cancelled Meeting",
            start=_EARLIER,
            end=_NOW,
            created_at=_EARLIER,
            updated_at=_NOW,
            deleted_at=deletion_time,
        )
        client = _roundtrip(server, ClientCalendarEvent)

        assert client.event_id == "evt-deleted"
        assert client.deleted_at is not None

    def test_calendar_container_roundtrip(self):
        """Calendar (server) → CalendarContainer (client) round-trip.

        The server Calendar model uses field_serializer to convert
        created_at/updated_at to ISO strings. The client CalendarContainer
        accepts both ``datetime`` and ``str`` for these fields.
        """
        server = ServerCalendar(
            calendar_id="work",
            name="Work Calendar",
            color="#22c55e",
            visible=True,
            event_ids={"evt-001", "evt-002", "evt-003"},
            default_reminders=[
                ServerReminder(minutes_before=10, type="notification"),
            ],
        )
        client = _roundtrip(server, ClientCalendar)

        assert client.calendar_id == "work"
        assert client.name == "Work Calendar"
        assert client.color == "#22c55e"
        assert client.visible is True
        # set → list in JSON → set on client
        assert client.event_ids == {"evt-001", "evt-002", "evt-003"}
        assert len(client.default_reminders) == 1
        assert client.default_reminders[0].minutes_before == 10
        # created_at and updated_at come as ISO strings from server serializer
        assert client.created_at is not None
        assert client.updated_at is not None


# ===================================================================
# Chat Round-Trip Tests
# ===================================================================


class TestChatRoundTrip:
    """Round-trip tests for chat models."""

    def test_chat_message_text_roundtrip(self):
        """ChatMessage with string content round-trips."""
        server = ServerChatMessage(
            message_id="chat-001",
            conversation_id="default",
            role="user",
            content="Hello, how are you?",
            timestamp=_NOW,
            metadata={"token_count": 5},
        )
        client = _roundtrip(server, ClientChatMessage)

        assert client.message_id == "chat-001"
        assert client.conversation_id == "default"
        assert client.role == "user"
        assert client.content == "Hello, how are you?"
        assert client.metadata == {"token_count": 5}

    def test_chat_message_multimodal_roundtrip(self):
        """ChatMessage with list content (multimodal) round-trips."""
        server = ServerChatMessage(
            message_id="chat-002",
            conversation_id="vision",
            role="user",
            content=[
                {"type": "text", "text": "What's in this image?"},
                {"type": "image_url", "url": "https://example.com/cat.jpg"},
            ],
            timestamp=_NOW,
        )
        client = _roundtrip(server, ClientChatMessage)

        assert client.message_id == "chat-002"
        assert isinstance(client.content, list)
        assert len(client.content) == 2
        assert client.content[0]["type"] == "text"
        assert client.content[1]["type"] == "image_url"

    def test_conversation_metadata_roundtrip(self):
        """ConversationMetadata round-trips with participant_roles set."""
        server = ServerConversationMetadata(
            conversation_id="conv-001",
            created_at=_EARLIER,
            last_message_at=_NOW,
            message_count=10,
            participant_roles={"user", "assistant"},
        )
        client = _roundtrip(server, ClientConversationMetadata)

        assert client.conversation_id == "conv-001"
        assert client.message_count == 10
        assert client.participant_roles == {"user", "assistant"}


# ===================================================================
# Weather Round-Trip Tests
# ===================================================================


class TestWeatherRoundTrip:
    """Round-trip tests for weather models."""

    def test_weather_condition_roundtrip(self):
        """WeatherCondition round-trips."""
        server = ServerWeatherCondition(
            id=800,
            main="Clear",
            description="clear sky",
            icon="01d",
        )
        client = _roundtrip(server, ClientWeatherCondition)

        assert client.id == 800
        assert client.main == "Clear"
        assert client.description == "clear sky"
        assert client.icon == "01d"

    def test_current_weather_roundtrip(self):
        """CurrentWeather with all fields round-trips."""
        condition = ServerWeatherCondition(
            id=801, main="Clouds", description="few clouds", icon="02d"
        )
        server = ServerCurrentWeather(
            dt=1707580800,
            sunrise=1707559200,
            sunset=1707597600,
            temp=280.5,
            feels_like=277.3,
            pressure=1013,
            humidity=65,
            dew_point=274.1,
            uvi=3.5,
            clouds=25,
            visibility=10000,
            wind_speed=5.2,
            wind_deg=180,
            wind_gust=8.1,
            weather=[condition],
        )
        client = _roundtrip(server, ClientCurrentWeather)

        assert client.dt == 1707580800
        assert client.temp == 280.5
        assert client.feels_like == 277.3
        assert client.pressure == 1013
        assert client.humidity == 65
        assert client.wind_gust == 8.1
        assert len(client.weather) == 1
        assert client.weather[0].main == "Clouds"

    def test_minutely_forecast_roundtrip(self):
        """MinutelyForecast round-trips."""
        server = ServerMinutelyForecast(dt=1707580800, precipitation=0.5)
        client = _roundtrip(server, ClientMinutelyForecast)

        assert client.dt == 1707580800
        assert client.precipitation == 0.5

    def test_hourly_forecast_roundtrip(self):
        """HourlyForecast with rain/snow data round-trips."""
        condition = ServerWeatherCondition(
            id=500, main="Rain", description="light rain", icon="10d"
        )
        server = ServerHourlyForecast(
            dt=1707580800,
            temp=282.0,
            feels_like=279.5,
            pressure=1010,
            humidity=80,
            dew_point=278.0,
            uvi=1.0,
            clouds=90,
            visibility=5000,
            wind_speed=3.5,
            wind_deg=270,
            weather=[condition],
            pop=0.75,
            rain={"1h": 1.2},
        )
        client = _roundtrip(server, ClientHourlyForecast)

        assert client.dt == 1707580800
        assert client.temp == 282.0
        assert client.pop == 0.75
        assert client.rain == {"1h": 1.2}
        assert client.snow is None

    def test_daily_forecast_roundtrip(self):
        """DailyForecast with nested temp/feels_like round-trips."""
        condition = ServerWeatherCondition(
            id=802, main="Clouds", description="scattered clouds", icon="03d"
        )
        temp = ServerDailyTemperature(
            day=285.0, min=278.0, max=290.0,
            night=280.0, eve=283.0, morn=279.0,
        )
        feels = ServerDailyFeelsLike(
            day=282.0, night=277.0, eve=280.0, morn=276.0,
        )
        server = ServerDailyForecast(
            dt=1707580800,
            sunrise=1707559200,
            sunset=1707597600,
            moonrise=1707570000,
            moonset=1707606000,
            moon_phase=0.5,
            summary="Partly cloudy throughout the day",
            temp=temp,
            feels_like=feels,
            pressure=1015,
            humidity=55,
            dew_point=275.0,
            wind_speed=4.0,
            wind_deg=200,
            wind_gust=7.5,
            weather=[condition],
            clouds=40,
            pop=0.2,
            rain=1.5,
            uvi=5.0,
        )
        client = _roundtrip(server, ClientDailyForecast)

        assert client.dt == 1707580800
        assert client.summary == "Partly cloudy throughout the day"
        assert client.temp.day == 285.0
        assert client.temp.min == 278.0
        assert client.temp.max == 290.0
        assert client.feels_like.day == 282.0
        assert client.rain == 1.5
        assert client.uvi == 5.0

    def test_weather_alert_roundtrip(self):
        """WeatherAlert round-trips with tags."""
        server = ServerWeatherAlert(
            sender_name="National Weather Service",
            event="Winter Storm Warning",
            start=1707580800,
            end=1707667200,
            description="Heavy snow expected with accumulations of 8-12 inches.",
            tags=["Snow", "Winter Storm"],
        )
        client = _roundtrip(server, ClientWeatherAlert)

        assert client.sender_name == "National Weather Service"
        assert client.event == "Winter Storm Warning"
        assert client.start == 1707580800
        assert client.end == 1707667200
        assert client.tags == ["Snow", "Winter Storm"]

    def test_weather_report_full_roundtrip(self):
        """Full WeatherReport with all sections round-trips."""
        condition = ServerWeatherCondition(
            id=800, main="Clear", description="clear sky", icon="01d"
        )
        current = ServerCurrentWeather(
            dt=1707580800, sunrise=1707559200, sunset=1707597600,
            temp=295.0, feels_like=293.5, pressure=1013, humidity=50,
            dew_point=284.0, uvi=7.0, clouds=5, visibility=10000,
            wind_speed=3.0, wind_deg=150, weather=[condition],
        )
        minutely = ServerMinutelyForecast(dt=1707580800, precipitation=0.0)
        hourly = ServerHourlyForecast(
            dt=1707580800, temp=295.0, feels_like=293.5, pressure=1013,
            humidity=50, dew_point=284.0, uvi=7.0, clouds=5,
            wind_speed=3.0, wind_deg=150, weather=[condition], pop=0.0,
        )
        temp = ServerDailyTemperature(
            day=295.0, min=288.0, max=299.0,
            night=290.0, eve=293.0, morn=289.0,
        )
        feels = ServerDailyFeelsLike(
            day=293.0, night=288.0, eve=291.0, morn=287.0,
        )
        daily = ServerDailyForecast(
            dt=1707580800, sunrise=1707559200, sunset=1707597600,
            moonrise=1707570000, moonset=1707606000, moon_phase=0.25,
            temp=temp, feels_like=feels, pressure=1013, humidity=50,
            dew_point=284.0, wind_speed=3.0, wind_deg=150,
            weather=[condition], clouds=5, pop=0.0, uvi=7.0,
        )
        alert = ServerWeatherAlert(
            sender_name="NWS", event="Heat Advisory",
            start=1707580800, end=1707667200,
            description="Temperatures expected to exceed 100F.",
        )

        server = ServerWeatherReport(
            lat=40.7128,
            lon=-74.0060,
            timezone="America/New_York",
            timezone_offset=-18000,
            current=current,
            minutely=[minutely],
            hourly=[hourly],
            daily=[daily],
            alerts=[alert],
        )
        client = _roundtrip(server, ClientWeatherReport)

        assert client.lat == 40.7128
        assert client.lon == -74.0060
        assert client.timezone == "America/New_York"
        assert client.timezone_offset == -18000
        assert client.current is not None
        assert client.current.temp == 295.0
        assert client.minutely is not None
        assert len(client.minutely) == 1
        assert client.hourly is not None
        assert len(client.hourly) == 1
        assert client.daily is not None
        assert len(client.daily) == 1
        assert client.daily[0].temp.day == 295.0
        assert client.alerts is not None
        assert len(client.alerts) == 1
        assert client.alerts[0].event == "Heat Advisory"


# ===================================================================
# Edge Case Tests
# ===================================================================


class TestRoundTripEdgeCases:
    """Edge cases and boundary conditions in round-trip serialization."""

    def test_empty_lists_preserved(self):
        """Empty collections round-trip correctly (not dropped or None)."""
        server = ServerEmail(
            message_id="empty-test",
            thread_id="thread-empty",
            from_address="test@example.com",
            to_addresses=["to@example.com"],
            subject="Empty lists test",
            body_text="Test",
            sent_at=_NOW,
            received_at=_NOW,
        )
        client = _roundtrip(server, ClientEmail)

        assert client.cc_addresses == []
        assert client.bcc_addresses == []
        assert client.references == []
        assert client.labels == []
        assert client.attachments == []

    def test_none_optional_fields_preserved(self):
        """Optional fields that are None round-trip as None."""
        server = ServerEmail(
            message_id="none-test",
            thread_id="thread-none",
            from_address="test@example.com",
            to_addresses=["to@example.com"],
            subject="None test",
            body_text="Test",
            sent_at=_NOW,
            received_at=_NOW,
        )
        client = _roundtrip(server, ClientEmail)

        assert client.reply_to_address is None
        assert client.body_html is None
        assert client.in_reply_to is None

    def test_empty_recurrence_exceptions_roundtrip(self):
        """Empty set of recurrence exceptions round-trips."""
        server = ServerCalendarEvent(
            event_id="evt-no-exceptions",
            calendar_id="primary",
            title="Normal Recurring",
            start=_EARLIER,
            end=_NOW,
            recurrence_exceptions=set(),
            created_at=_EARLIER,
            updated_at=_NOW,
        )
        client = _roundtrip(server, ClientCalendarEvent)

        assert client.recurrence_exceptions == set()

    def test_sms_message_minimal_roundtrip(self):
        """SMSMessage with only required fields round-trips."""
        server = ServerSMSMessage(
            thread_id="conv-minimal",
            from_number="+15551234567",
            to_numbers=["+15559876543"],
            body="Hi",
            direction="incoming",
            sent_at=_NOW,
        )
        client = _roundtrip(server, ClientSMSMessage)

        assert client.body == "Hi"
        assert client.direction == "incoming"
        assert client.attachments == []
        assert client.reactions == []
        assert client.is_read is False
        assert client.is_deleted is False
        assert client.is_spam is False

    def test_weather_report_no_optional_sections(self):
        """WeatherReport with no optional sections round-trips."""
        server = ServerWeatherReport(
            lat=51.5074,
            lon=-0.1278,
            timezone="Europe/London",
            timezone_offset=0,
        )
        client = _roundtrip(server, ClientWeatherReport)

        assert client.lat == 51.5074
        assert client.lon == -0.1278
        assert client.current is None
        assert client.minutely is None
        assert client.hourly is None
        assert client.daily is None
        assert client.alerts is None

    def test_conversation_metadata_empty_roles(self):
        """ConversationMetadata with empty participant_roles round-trips."""
        server = ServerConversationMetadata(
            conversation_id="empty-roles",
            created_at=_NOW,
            last_message_at=_NOW,
            message_count=0,
            participant_roles=set(),
        )
        client = _roundtrip(server, ClientConversationMetadata)

        assert client.participant_roles == set()
        assert client.message_count == 0


# ===================================================================
# Contacts Round-Trip Tests
# ===================================================================


class TestContactsRoundTrip:
    """Round-trip tests for contacts models."""

    def test_contact_identifier_roundtrip(self):
        """ContactIdentifier serializes and deserializes with all fields."""
        server = ServerContactIdentifier(
            identifier_type="phone",
            value="+15551234567",
            label="mobile",
        )
        client = _roundtrip(server, ClientContactIdentifier)

        assert client.identifier_type == "phone"
        assert client.value == "+15551234567"
        assert client.label == "mobile"

    def test_contact_identifier_no_label_roundtrip(self):
        """ContactIdentifier without optional label round-trips."""
        server = ServerContactIdentifier(
            identifier_type="email",
            value="alice@example.com",
        )
        client = _roundtrip(server, ClientContactIdentifier)

        assert client.identifier_type == "email"
        assert client.value == "alice@example.com"
        assert client.label is None

    def test_postal_address_full_roundtrip(self):
        """PostalAddress with all fields round-trips."""
        server = ServerPostalAddress(
            street="123 Main St",
            city="Springfield",
            state="IL",
            postal_code="62704",
            country="US",
            label="home",
        )
        client = _roundtrip(server, ClientPostalAddress)

        assert client.street == "123 Main St"
        assert client.city == "Springfield"
        assert client.state == "IL"
        assert client.postal_code == "62704"
        assert client.country == "US"
        assert client.label == "home"

    def test_postal_address_minimal_roundtrip(self):
        """PostalAddress with no fields round-trips (all optional)."""
        server = ServerPostalAddress()
        client = _roundtrip(server, ClientPostalAddress)

        assert client.street is None
        assert client.city is None
        assert client.state is None
        assert client.postal_code is None
        assert client.country is None
        assert client.label is None

    def test_contact_full_roundtrip(self):
        """Full Contact model round-trips with all fields populated."""
        server = ServerContact(
            contact_id="contact-001",
            first_name="Alice",
            last_name="Smith",
            display_name="Mom",
            nickname="Ali",
            identifiers=[
                ServerContactIdentifier(
                    identifier_type="phone",
                    value="+15551234567",
                    label="mobile",
                ),
                ServerContactIdentifier(
                    identifier_type="email",
                    value="alice@example.com",
                    label="work",
                ),
            ],
            company="Acme Corp",
            job_title="Engineer",
            addresses=[
                ServerPostalAddress(
                    street="123 Main St",
                    city="Springfield",
                    state="IL",
                    postal_code="62704",
                    country="US",
                    label="home",
                ),
            ],
            birthday=date(1990, 5, 15),
            notes="Friend from college",
            photo_url="https://example.com/photo.jpg",
            is_favorite=True,
            is_blocked=False,
            groups={"Family", "Work"},
            created_at=_EARLIER,
            updated_at=_NOW,
        )
        client = _roundtrip(server, ClientContact)

        assert client.contact_id == "contact-001"
        assert client.first_name == "Alice"
        assert client.last_name == "Smith"
        assert client.display_name == "Mom"
        assert client.nickname == "Ali"
        assert len(client.identifiers) == 2
        assert client.identifiers[0].identifier_type == "phone"
        assert client.identifiers[0].value == "+15551234567"
        assert client.identifiers[1].identifier_type == "email"
        assert client.identifiers[1].value == "alice@example.com"
        assert client.company == "Acme Corp"
        assert client.job_title == "Engineer"
        assert len(client.addresses) == 1
        assert client.addresses[0].street == "123 Main St"
        assert client.addresses[0].city == "Springfield"
        # birthday serializes as ISO date string
        assert client.birthday == "1990-05-15"
        assert client.notes == "Friend from college"
        assert client.photo_url == "https://example.com/photo.jpg"
        assert client.is_favorite is True
        assert client.is_blocked is False
        # set serializes to list; order is not guaranteed
        assert set(client.groups) == {"Family", "Work"}

    def test_contact_minimal_roundtrip(self):
        """Contact with only required fields round-trips."""
        server = ServerContact(
            contact_id="contact-minimal",
            created_at=_EARLIER,
            updated_at=_NOW,
        )
        client = _roundtrip(server, ClientContact)

        assert client.contact_id == "contact-minimal"
        assert client.first_name is None
        assert client.last_name is None
        assert client.display_name is None
        assert client.nickname is None
        assert client.identifiers == []
        assert client.company is None
        assert client.job_title is None
        assert client.addresses == []
        assert client.birthday is None
        assert client.notes is None
        assert client.photo_url is None
        assert client.is_favorite is False
        assert client.is_blocked is False
        assert client.groups == []

    def test_contact_no_birthday_roundtrip(self):
        """Contact with no birthday round-trips correctly."""
        server = ServerContact(
            contact_id="contact-no-bday",
            first_name="Bob",
            identifiers=[
                ServerContactIdentifier(
                    identifier_type="phone",
                    value="+15559876543",
                ),
            ],
            created_at=_EARLIER,
            updated_at=_NOW,
        )
        client = _roundtrip(server, ClientContact)

        assert client.first_name == "Bob"
        assert client.birthday is None
        assert len(client.identifiers) == 1
