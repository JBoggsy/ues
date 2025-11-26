"""Helper functions for API integration tests.

This module provides convenience functions for creating valid event request data
for API tests. Each modality has its own helper function that returns properly
formatted data dictionaries ready for use in HTTP requests.

These helpers ensure:
- Correct field names matching the actual model implementations
- Valid default values for required fields
- Easy customization of specific fields for test scenarios
- Consistent data structure across tests
"""

import time
from datetime import datetime
from typing import Any, Optional


def make_event_request(
    scheduled_time: datetime,
    modality: str,
    data: dict[str, Any],
    priority: int = 50,
    metadata: Optional[dict[str, Any]] = None,
    agent_id: Optional[str] = None,
) -> dict[str, Any]:
    """Create a complete event creation request.
    
    Args:
        scheduled_time: When the event should execute (simulator time).
        modality: Modality type (e.g., "email", "sms", "chat").
        data: Modality-specific event data (use modality helper functions).
        priority: Event execution priority (0-100, default: 50).
        metadata: Optional custom metadata dictionary.
        agent_id: Optional ID of agent creating this event.
    
    Returns:
        Complete event request dictionary ready for POST /events.
    
    Example:
        >>> request = make_event_request(
        ...     event_time,
        ...     "email",
        ...     email_event_data(subject="Test"),
        ... )
        >>> response = client.post("/events", json=request)
    """
    request: dict[str, Any] = {
        "scheduled_time": scheduled_time.isoformat(),
        "modality": modality,
        "data": data,
        "priority": priority,
    }
    
    if metadata is not None:
        request["metadata"] = metadata
    
    if agent_id is not None:
        request["agent_id"] = agent_id
    
    return request


# Email Event Helpers

def email_event_data(
    operation: str = "receive",
    from_address: str = "sender@example.com",
    to_addresses: Optional[list[str]] = None,
    subject: str = "Test Email",
    body_text: str = "This is a test email.",
    cc_addresses: Optional[list[str]] = None,
    bcc_addresses: Optional[list[str]] = None,
    body_html: Optional[str] = None,
    message_id: Optional[str] = None,
    thread_id: Optional[str] = None,
    **kwargs,
) -> dict[str, Any]:
    """Create email event data for API requests.
    
    Args:
        operation: Email operation type (e.g., "receive", "send", "delete", "move").
        from_address: Sender email address.
        to_addresses: List of recipient email addresses (defaults to ["user@example.com"]).
        subject: Email subject line.
        body_text: Plain text email body content.
        cc_addresses: Optional list of CC recipient addresses.
        bcc_addresses: Optional list of BCC recipient addresses.
        body_html: Optional HTML email body content.
        message_id: Optional message ID (auto-generated if not provided for new emails).
        thread_id: Optional thread identifier for conversation grouping.
        **kwargs: Additional email fields (e.g., priority, attachments, labels, folder).
    
    Returns:
        Email event data dictionary ready for event creation.
    
    Example:
        >>> data = email_event_data(
        ...     operation="receive",
        ...     subject="Meeting Tomorrow",
        ...     from_address="boss@company.com",
        ... )
    """
    data: dict[str, Any] = {
        "operation": operation,
        "from_address": from_address,
        "to_addresses": to_addresses or ["user@example.com"],
        "subject": subject,
        "body_text": body_text,
    }
    
    if cc_addresses is not None:
        data["cc_addresses"] = cc_addresses
    
    if bcc_addresses is not None:
        data["bcc_addresses"] = bcc_addresses
    
    if body_html is not None:
        data["body_html"] = body_html
    
    if message_id is not None:
        data["message_id"] = message_id
    
    if thread_id is not None:
        data["thread_id"] = thread_id
    
    data.update(kwargs)
    return data


# SMS Event Helpers

def sms_event_data(
    action: str = "receive_message",
    from_number: str = "+1234567890",
    to_numbers: Optional[list[str]] = None,
    body: str = "Test message",
    **kwargs,
) -> dict[str, Any]:
    """Create SMS event data for API requests.
    
    Args:
        action: SMS action type (e.g., "send_message", "receive_message", "delete_message").
        from_number: Sender phone number in E.164 format.
        to_numbers: List of recipient phone numbers (defaults to ["+0987654321"]).
        body: Message text content.
        **kwargs: Additional SMS fields for specific actions (e.g., message_id, conversation_id).
    
    Returns:
        SMS event data dictionary ready for event creation.
    
    Note:
        SMS uses a nested structure with message_data for send/receive actions.
    
    Example:
        >>> data = sms_event_data(
        ...     action="receive_message",
        ...     from_number="+15551234567",
        ...     body="Meeting at 3pm",
        ... )
    """
    data: dict[str, Any] = {
        "action": action,
    }
    
    # For send_message and receive_message, wrap in message_data
    if action in ["send_message", "receive_message"]:
        data["message_data"] = {
            "from_number": from_number,
            "to_numbers": to_numbers or ["+0987654321"],
            "body": body,
        }
        # Add any additional message_data fields from kwargs
        if kwargs:
            data["message_data"].update(kwargs)
    else:
        # For other actions, add fields directly
        data.update(kwargs)
    
    return data


# Chat Event Helpers

def chat_event_data(
    role: str = "user",
    content: str = "Hello",
    operation: str = "send_message",
    conversation_id: str = "default",
    message_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Create chat event data for API requests.
    
    Args:
        role: Message sender role ("user" or "assistant").
        content: Message content (string for text, list of dicts for multimodal).
        operation: Chat operation type (default: "send_message").
        conversation_id: Conversation/thread identifier (default: "default").
        message_id: Optional message ID (auto-generated if not provided).
        metadata: Optional additional data (e.g., token count, model info).
    
    Returns:
        Chat event data dictionary ready for event creation.
    
    Example:
        >>> data = chat_event_data(
        ...     role="user",
        ...     content="What's the weather today?",
        ... )
    """
    data: dict[str, Any] = {
        "operation": operation,
        "role": role,
        "content": content,
        "conversation_id": conversation_id,
    }
    
    if message_id is not None:
        data["message_id"] = message_id
    
    if metadata is not None:
        data["metadata"] = metadata
    
    return data


# Location Event Helpers

def location_event_data(
    latitude: float = 37.7749,
    longitude: float = -122.4194,
    address: Optional[str] = None,
    named_location: Optional[str] = None,
    altitude: Optional[float] = None,
    accuracy: Optional[float] = None,
    speed: Optional[float] = None,
    bearing: Optional[float] = None,
) -> dict[str, Any]:
    """Create location event data for API requests.
    
    Args:
        latitude: Latitude coordinate in decimal degrees (-90 to 90).
        longitude: Longitude coordinate in decimal degrees (-180 to 180).
        address: Optional human-readable address.
        named_location: Optional semantic name (e.g., "Home", "Office", "Gym").
        altitude: Optional altitude in meters above sea level.
        accuracy: Optional accuracy radius in meters.
        speed: Optional speed in meters per second.
        bearing: Optional bearing/heading in degrees (0-360, 0=North).
    
    Returns:
        Location event data dictionary ready for event creation.
    
    Example:
        >>> data = location_event_data(
        ...     latitude=40.7128,
        ...     longitude=-74.0060,
        ...     named_location="Office",
        ...     address="New York, NY",
        ... )
    """
    data: dict[str, Any] = {
        "latitude": latitude,
        "longitude": longitude,
    }
    
    if address is not None:
        data["address"] = address
    
    if named_location is not None:
        data["named_location"] = named_location
    
    if altitude is not None:
        data["altitude"] = altitude
    
    if accuracy is not None:
        data["accuracy"] = accuracy
    
    if speed is not None:
        data["speed"] = speed
    
    if bearing is not None:
        data["bearing"] = bearing
    
    return data


# Calendar Event Helpers

def calendar_event_data(
    operation: str = "create",
    title: str = "Test Event",
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    location: Optional[str] = None,
    description: Optional[str] = None,
    attendees: Optional[list[dict[str, Any]]] = None,
    event_id: Optional[str] = None,
    all_day: bool = False,
    **kwargs,
) -> dict[str, Any]:
    """Create calendar event data for API requests.
    
    Args:
        operation: Calendar operation ("create", "update", "delete").
        title: Event title/summary.
        start_time: Event start datetime (required for create).
        end_time: Event end datetime (required for create).
        location: Optional event location.
        description: Optional event description.
        attendees: Optional list of attendee dictionaries.
        event_id: Optional event ID (required for update/delete).
        all_day: Whether this is an all-day event (default: False).
        **kwargs: Additional calendar fields (e.g., recurrence, reminders, status).
    
    Returns:
        Calendar event data dictionary ready for event creation.
    
    Example:
        >>> from datetime import datetime, timedelta, timezone
        >>> now = datetime.now(timezone.utc)
        >>> data = calendar_event_data(
        ...     operation="create",
        ...     title="Team Meeting",
        ...     start_time=now + timedelta(hours=1),
        ...     end_time=now + timedelta(hours=2),
        ...     location="Conference Room A",
        ... )
    """
    data: dict[str, Any] = {
        "operation": operation,
        "title": title,
        "all_day": all_day,
    }
    
    if start_time is not None:
        data["start"] = start_time.isoformat()
    
    if end_time is not None:
        data["end"] = end_time.isoformat()
    
    if location is not None:
        data["location"] = location
    
    if description is not None:
        data["description"] = description
    
    if attendees is not None:
        data["attendees"] = attendees
    
    if event_id is not None:
        data["event_id"] = event_id
    
    data.update(kwargs)
    return data


# Time Preference Event Helpers

def time_event_data(
    timezone: str = "UTC",
    format_preference: str = "24h",
    date_format: Optional[str] = None,
    locale: Optional[str] = None,
    week_start: Optional[str] = None,
) -> dict[str, Any]:
    """Create time preference event data for API requests.
    
    Args:
        timezone: IANA timezone identifier (e.g., "America/New_York", "UTC").
        format_preference: Time format preference ("12h" or "24h").
        date_format: Optional date format (e.g., "MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD").
        locale: Optional locale identifier (e.g., "en_US", "en_GB", "fr_FR").
        week_start: Optional week start day ("sunday" or "monday").
    
    Returns:
        Time preference event data dictionary ready for event creation.
    
    Example:
        >>> data = time_event_data(
        ...     timezone="America/New_York",
        ...     format_preference="12h",
        ...     date_format="MM/DD/YYYY",
        ... )
    """
    data: dict[str, Any] = {
        "timezone": timezone,
        "format_preference": format_preference,
    }
    
    if date_format is not None:
        data["date_format"] = date_format
    
    if locale is not None:
        data["locale"] = locale
    
    if week_start is not None:
        data["week_start"] = week_start
    
    return data


# Weather Event Helpers

def weather_event_data(
    latitude: float = 37.7749,
    longitude: float = -122.4194,
    report: Optional[dict[str, Any]] = None,
    **kwargs,
) -> dict[str, Any]:
    """Create weather update event data for API requests.
    
    Args:
        latitude: Latitude coordinate for weather location (-90 to 90).
        longitude: Longitude coordinate for weather location (-180 to 180).
        report: Weather report data (OpenWeather API format). If None, creates minimal valid report.
        **kwargs: Additional weather fields.
    
    Returns:
        Weather event data dictionary ready for event creation.
    
    Note:
        Weather input requires a complete WeatherReport object. If not provided,
        this helper creates a minimal valid report with current conditions only.
    
    Example:
        >>> data = weather_event_data(
        ...     latitude=40.7128,
        ...     longitude=-74.0060,
        ... )
    """
    # Create minimal valid weather report if not provided
    if report is None:
        now = int(time.time())
        report = {
            "lat": latitude,
            "lon": longitude,
            "timezone": "UTC",
            "timezone_offset": 0,
            "current": {
                "dt": now,
                "sunrise": now - 3600,
                "sunset": now + 3600,
                "temp": 293.15,  # 20°C in Kelvin
                "feels_like": 293.15,
                "pressure": 1013,
                "humidity": 50,
                "dew_point": 283.15,
                "uvi": 5.0,
                "clouds": 20,
                "visibility": 10000,
                "wind_speed": 3.5,
                "wind_deg": 180,
                "weather": [
                    {
                        "id": 800,
                        "main": "Clear",
                        "description": "clear sky",
                        "icon": "01d",
                    }
                ],
            }
        }
    
    data: dict[str, Any] = {
        "latitude": latitude,
        "longitude": longitude,
        "report": report,
    }
    
    data.update(kwargs)
    return data
