"""
Fluent event builders for workflow scenarios.

These builders provide a clean, readable syntax for constructing
event data for each modality. They can be used directly in scenario
definitions and will be built into proper request dictionaries at
execution time.

Example:
    EMAIL_1 = (
        email()
        .receive()
        .from_address("sender@example.com")
        .to("recipient@example.com")
        .subject("Hello")
        .body("World")
        .at_offset(seconds=60)
    )
"""

from datetime import datetime, timedelta
from typing import Any, Self


class EventBuilder:
    """Base class for fluent event builders.

    Subclasses should set self._modality and populate self._data
    with modality-specific fields.
    """

    def __init__(self, modality: str):
        self._modality = modality
        self._data: dict[str, Any] = {}
        self._scheduled_time: datetime | timedelta | None = None
        self._priority: int = 50
        self._metadata: dict[str, Any] = {}
        self._agent_id: str | None = None

    def at_time(self, time: datetime) -> Self:
        """Schedule at an absolute datetime."""
        self._scheduled_time = time
        return self

    def at_offset(self, seconds: float = 0, minutes: float = 0, hours: float = 0) -> Self:
        """Schedule at a relative offset from simulation start time."""
        total_seconds = seconds + (minutes * 60) + (hours * 3600)
        self._scheduled_time = timedelta(seconds=total_seconds)
        return self

    def with_priority(self, priority: int) -> Self:
        """Set event priority (0-100, higher = more important)."""
        self._priority = priority
        return self

    def with_metadata(self, **kwargs: Any) -> Self:
        """Add custom metadata to the event."""
        self._metadata.update(kwargs)
        return self

    def from_agent(self, agent_id: str) -> Self:
        """Set the agent ID that created this event."""
        self._agent_id = agent_id
        return self

    def build(self, base_time: datetime) -> dict[str, Any]:
        """Build the complete event request dictionary.

        Args:
            base_time: The simulation start time for resolving relative offsets.

        Returns:
            A dictionary suitable for POST /events.
        """
        if isinstance(self._scheduled_time, timedelta):
            scheduled = base_time + self._scheduled_time
        elif self._scheduled_time is not None:
            scheduled = self._scheduled_time
        else:
            scheduled = base_time

        result = {
            "modality": self._modality,
            "scheduled_time": scheduled.isoformat(),
            "priority": self._priority,
            "data": self._data,
        }

        if self._metadata:
            result["metadata"] = self._metadata

        if self._agent_id:
            result["agent_id"] = self._agent_id

        return result

    def build_immediate(self) -> dict[str, Any]:
        """Build an immediate event request dictionary.

        Returns:
            A dictionary suitable for POST /events/immediate.
        """
        result = {
            "modality": self._modality,
            "data": self._data,
        }

        if self._metadata:
            result["metadata"] = self._metadata

        if self._agent_id:
            result["agent_id"] = self._agent_id

        return result


class EmailEventBuilder(EventBuilder):
    """Builder for email modality events."""

    def __init__(self):
        super().__init__("email")
        self._data = {
            "operation": "receive",
            "to_addresses": [],
        }

    def receive(self) -> Self:
        """Set operation to receive (incoming email)."""
        self._data["operation"] = "receive"
        return self

    def send(self) -> Self:
        """Set operation to send (outgoing email)."""
        self._data["operation"] = "send"
        return self

    def from_address(self, address: str) -> Self:
        """Set the sender address."""
        self._data["from_address"] = address
        return self

    def to(self, *addresses: str) -> Self:
        """Set recipient addresses."""
        self._data["to_addresses"] = list(addresses)
        return self

    def cc(self, *addresses: str) -> Self:
        """Set CC addresses."""
        self._data["cc_addresses"] = list(addresses)
        return self

    def bcc(self, *addresses: str) -> Self:
        """Set BCC addresses."""
        self._data["bcc_addresses"] = list(addresses)
        return self

    def subject(self, subject: str) -> Self:
        """Set the email subject."""
        self._data["subject"] = subject
        return self

    def body(self, text: str, html: str | None = None) -> Self:
        """Set the email body (text and optional HTML)."""
        self._data["body_text"] = text
        if html:
            self._data["body_html"] = html
        return self

    def with_headers(self, **headers: str) -> Self:
        """Add custom email headers as metadata (headers aren't part of EmailInput).
        
        Note: This stores headers in the event metadata, not in the email data itself,
        since EmailInput doesn't have a headers field.
        """
        self._metadata.setdefault("email_headers", {}).update(headers)
        return self
        return self


class SMSEventBuilder(EventBuilder):
    """Builder for SMS modality events."""

    def __init__(self):
        super().__init__("sms")
        self._data = {
            "action": "receive_message",
            "message_data": {
                "to_numbers": [],
                "message_type": "sms",
            },
        }

    def receive(self) -> Self:
        """Set action to receive (incoming SMS)."""
        self._data["action"] = "receive_message"
        return self

    def send(self) -> Self:
        """Set action to send (outgoing SMS)."""
        self._data["action"] = "send_message"
        return self

    def from_number(self, number: str) -> Self:
        """Set the sender phone number."""
        self._data["message_data"]["from_number"] = number
        return self

    def to(self, *numbers: str) -> Self:
        """Set recipient phone numbers."""
        self._data["message_data"]["to_numbers"] = list(numbers)
        return self

    def body(self, text: str) -> Self:
        """Set the message body."""
        self._data["message_data"]["body"] = text
        return self

    def as_mms(self) -> Self:
        """Mark as MMS message."""
        self._data["message_data"]["message_type"] = "mms"
        return self

    def as_rcs(self) -> Self:
        """Mark as RCS message."""
        self._data["message_data"]["message_type"] = "rcs"
        return self


class ChatEventBuilder(EventBuilder):
    """Builder for chat modality events."""

    def __init__(self):
        super().__init__("chat")
        self._data = {
            "operation": "send_message",
            "role": "user",
            "content": "",
            "conversation_id": "default",
        }

    def user_message(self, content: str) -> Self:
        """Create a user message."""
        self._data["role"] = "user"
        self._data["content"] = content
        return self

    def assistant_message(self, content: str) -> Self:
        """Create an assistant message."""
        self._data["role"] = "assistant"
        self._data["content"] = content
        return self

    def system_message(self, content: str) -> Self:
        """Create a system message."""
        self._data["role"] = "system"
        self._data["content"] = content
        return self

    def in_conversation(self, conversation_id: str) -> Self:
        """Set the conversation ID."""
        self._data["conversation_id"] = conversation_id
        return self


class CalendarEventBuilder(EventBuilder):
    """Builder for calendar modality events."""

    def __init__(self):
        super().__init__("calendar")
        self._data = {
            "operation": "create",
        }

    def create(self) -> Self:
        """Set action to create a calendar event."""
        self._data["operation"] = "create"
        return self

    def update(self, event_id: str) -> Self:
        """Set action to update an existing event."""
        self._data["operation"] = "update"
        self._data["event_id"] = event_id
        return self

    def delete(self, event_id: str) -> Self:
        """Set action to delete an event."""
        self._data["operation"] = "delete"
        self._data["event_id"] = event_id
        return self

    def title(self, title: str) -> Self:
        """Set the event title."""
        self._data["title"] = title
        return self

    def description(self, description: str) -> Self:
        """Set the event description."""
        self._data["description"] = description
        return self

    def start(self, time: datetime | str) -> Self:
        """Set the event start time."""
        if isinstance(time, datetime):
            time = time.isoformat()
        self._data["start"] = time
        return self

    def end(self, time: datetime | str) -> Self:
        """Set the event end time."""
        if isinstance(time, datetime):
            time = time.isoformat()
        self._data["end"] = time
        return self

    def location(self, location: str) -> Self:
        """Set the event location."""
        self._data["location"] = location
        return self

    def attendees(self, *emails: str) -> Self:
        """Set the event attendees as simple email list."""
        # Convert to list of Attendee-like dicts
        self._data["attendees"] = [
            {"email": email} for email in emails
        ]
        return self

    def reminder(self, minutes_before: int, method: str = "notification") -> Self:
        """Add a reminder to the event."""
        if "reminders" not in self._data:
            self._data["reminders"] = []
        self._data["reminders"].append({
            "minutes_before": minutes_before,
            "type": method,
        })
        return self

    def on_calendar(self, calendar_id: str) -> Self:
        """Set which calendar to add the event to."""
        self._data["calendar_id"] = calendar_id
        return self


class LocationEventBuilder(EventBuilder):
    """Builder for location modality events."""

    def __init__(self):
        super().__init__("location")
        self._data = {}

    def at(self, latitude: float, longitude: float) -> Self:
        """Set the location coordinates."""
        self._data["latitude"] = latitude
        self._data["longitude"] = longitude
        return self

    def altitude(self, meters: float) -> Self:
        """Set the altitude in meters."""
        self._data["altitude"] = meters
        return self

    def accuracy(self, meters: float) -> Self:
        """Set the location accuracy in meters."""
        self._data["accuracy"] = meters
        return self

    def speed(self, meters_per_second: float) -> Self:
        """Set the current speed."""
        self._data["speed"] = meters_per_second
        return self

    def heading(self, degrees: float) -> Self:
        """Set the heading/bearing in degrees (0-360)."""
        self._data["bearing"] = degrees
        return self

    def named(self, name: str) -> Self:
        """Set a human-readable location name."""
        self._data["named_location"] = name
        return self

    def address(self, address: str) -> Self:
        """Set the street address."""
        self._data["address"] = address
        return self

    def bearing(self, degrees: float) -> Self:
        """Set the bearing in degrees (0-360)."""
        self._data["bearing"] = degrees
        return self


class WeatherEventBuilder(EventBuilder):
    """Builder for weather modality events.
    
    Creates weather data in OpenWeather API format required by WeatherInput.
    """

    def __init__(self):
        super().__init__("weather")
        import time as time_module
        self._now = int(time_module.time())
        self._lat = 0.0
        self._lon = 0.0
        self._temp = 293.15  # 20°C in Kelvin
        self._feels_like = 293.15
        self._humidity = 50
        self._pressure = 1013
        self._wind_speed = 3.5
        self._wind_deg = 180
        self._visibility = 10000
        self._clouds = 20
        self._conditions = "Clear"
        self._description = "clear sky"
        self._uvi = 5.0
        self._dew_point = 283.15
        self._pop = 0.0  # precipitation probability (0-1)
        
    def _build_report(self) -> dict:
        """Build the OpenWeather-format report."""
        return {
            "lat": self._lat,
            "lon": self._lon,
            "timezone": "UTC",
            "timezone_offset": 0,
            "current": {
                "dt": self._now,
                "sunrise": self._now - 3600,
                "sunset": self._now + 3600,
                "temp": self._temp,
                "feels_like": self._feels_like,
                "pressure": self._pressure,
                "humidity": self._humidity,
                "dew_point": self._dew_point,
                "uvi": self._uvi,
                "clouds": self._clouds,
                "visibility": self._visibility,
                "wind_speed": self._wind_speed,
                "wind_deg": self._wind_deg,
                "weather": [
                    {
                        "id": 800,  # Clear sky
                        "main": self._conditions,
                        "description": self._description,
                        "icon": "01d",
                    }
                ],
            },
        }
    
    def build(self, base_time: datetime) -> dict[str, Any]:
        """Build the complete event request dictionary with OpenWeather format.

        Args:
            base_time: The simulation start time for resolving relative offsets.

        Returns:
            A dictionary suitable for POST /events.
        """
        if isinstance(self._scheduled_time, timedelta):
            scheduled = base_time + self._scheduled_time
        elif self._scheduled_time is not None:
            scheduled = self._scheduled_time
        else:
            scheduled = base_time

        result = {
            "modality": self._modality,
            "scheduled_time": scheduled.isoformat(),
            "priority": self._priority,
            "data": {
                "latitude": self._lat,
                "longitude": self._lon,
                "report": self._build_report(),
            },
        }

        if self._metadata:
            result["metadata"] = self._metadata

        if self._agent_id:
            result["agent_id"] = self._agent_id

        return result

    def at(self, latitude: float, longitude: float) -> Self:
        """Set the location for the weather report."""
        self._lat = latitude
        self._lon = longitude
        return self

    def temperature(self, temp_celsius: float, feels_like_celsius: float | None = None) -> Self:
        """Set temperature in Celsius (converted to Kelvin internally)."""
        self._temp = temp_celsius + 273.15  # Convert to Kelvin
        if feels_like_celsius is not None:
            self._feels_like = feels_like_celsius + 273.15
        else:
            self._feels_like = self._temp
        return self

    def humidity(self, percent: int) -> Self:
        """Set humidity percentage."""
        self._humidity = percent
        return self

    def conditions(self, conditions: str, description: str | None = None) -> Self:
        """Set weather conditions (e.g., 'Clear', 'Light Rain')."""
        self._conditions = conditions
        self._description = description or conditions.lower()
        return self

    def wind(self, speed: float, direction: int | None = None) -> Self:
        """Set wind speed (m/s) and optional direction (degrees)."""
        self._wind_speed = speed
        if direction is not None:
            self._wind_deg = direction
        return self

    def pressure(self, hpa: int) -> Self:
        """Set atmospheric pressure in hPa."""
        self._pressure = hpa
        return self

    def visibility(self, meters: int) -> Self:
        """Set visibility in meters."""
        self._visibility = meters
        return self

    def cloud_cover(self, percent: int) -> Self:
        """Set cloud cover percentage."""
        self._clouds = percent
        return self

    def precipitation_probability(self, percent: int) -> Self:
        """Set precipitation probability (0-100, converted to 0-1 internally)."""
        self._pop = percent / 100.0
        return self


class TimeEventBuilder(EventBuilder):
    """Builder for time modality events (e.g., timezone changes)."""

    def __init__(self):
        super().__init__("time")
        self._data = {}

    def timezone(self, tz: str) -> Self:
        """Set the timezone (e.g., 'America/New_York')."""
        self._data["timezone"] = tz
        return self


# Factory functions for clean syntax
def email() -> EmailEventBuilder:
    """Create an email event builder."""
    return EmailEventBuilder()


def sms() -> SMSEventBuilder:
    """Create an SMS event builder."""
    return SMSEventBuilder()


def chat() -> ChatEventBuilder:
    """Create a chat event builder."""
    return ChatEventBuilder()


def calendar() -> CalendarEventBuilder:
    """Create a calendar event builder."""
    return CalendarEventBuilder()


def location() -> LocationEventBuilder:
    """Create a location event builder."""
    return LocationEventBuilder()


def weather() -> WeatherEventBuilder:
    """Create a weather event builder."""
    return WeatherEventBuilder()


def time_event() -> TimeEventBuilder:
    """Create a time event builder."""
    return TimeEventBuilder()
