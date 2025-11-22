"""Fixtures for Time modality."""

from datetime import datetime, timezone as tz

from models.modalities.time_input import TimeInput
from models.modalities.time_state import TimeState


def create_time_input(
    timezone: str = "UTC",
    format_preference: str = "12h",
    timestamp: datetime | None = None,
    **kwargs,
) -> TimeInput:
    """Create a TimeInput with sensible defaults.

    Args:
        timezone: IANA timezone identifier (default: UTC).
        format_preference: Time format "12h" or "24h" (default: 12h).
        timestamp: When settings change occurred (defaults to now).
        **kwargs: Additional fields to override.

    Returns:
        TimeInput instance ready for testing.
    """
    return TimeInput(
        timezone=timezone,
        format_preference=format_preference,
        timestamp=timestamp or datetime.now(tz.utc),
        **kwargs,
    )


def create_time_state(
    timezone: str = "UTC",
    format_preference: str = "12h",
    last_updated: datetime | None = None,
    **kwargs,
) -> TimeState:
    """Create a TimeState with sensible defaults.

    Args:
        timezone: Current IANA timezone identifier (default: UTC).
        format_preference: Current time format (default: 12h).
        last_updated: When state was last updated (defaults to now).
        **kwargs: Additional fields to override.

    Returns:
        TimeState instance ready for testing.
    """
    return TimeState(
        timezone=timezone,
        format_preference=format_preference,
        last_updated=last_updated or datetime.now(tz.utc),
        **kwargs,
    )


# Pre-built timezone examples
UTC_INPUT = create_time_input(
    timezone="UTC",
    format_preference="24h",
)

US_EASTERN_INPUT = create_time_input(
    timezone="America/New_York",
    format_preference="12h",
    date_format="MM/DD/YYYY",
    locale="en_US",
)

US_PACIFIC_INPUT = create_time_input(
    timezone="America/Los_Angeles",
    format_preference="12h",
    date_format="MM/DD/YYYY",
)

UK_INPUT = create_time_input(
    timezone="Europe/London",
    format_preference="24h",
    date_format="DD/MM/YYYY",
    locale="en_GB",
    week_start="monday",
)

TOKYO_INPUT = create_time_input(
    timezone="Asia/Tokyo",
    format_preference="24h",
    date_format="YYYY-MM-DD",
    locale="ja_JP",
)

PARIS_INPUT = create_time_input(
    timezone="Europe/Paris",
    format_preference="24h",
    date_format="DD/MM/YYYY",
    locale="fr_FR",
    week_start="monday",
)

SYDNEY_INPUT = create_time_input(
    timezone="Australia/Sydney",
    format_preference="12h",
    date_format="DD/MM/YYYY",
    locale="en_AU",
)


# State examples
UTC_STATE = create_time_state(
    timezone="UTC",
    format_preference="24h",
)

US_EASTERN_STATE = create_time_state(
    timezone="America/New_York",
    format_preference="12h",
    date_format="MM/DD/YYYY",
    locale="en_US",
)


# Invalid examples for validation testing
INVALID_TIME_INPUTS = {
    "bad_timezone": {
        "timezone": "Not/A/Timezone",
        "format_preference": "12h",
        "timestamp": datetime.now(tz.utc),
    },
    "bad_date_format": {
        "timezone": "UTC",
        "format_preference": "12h",
        "date_format": "INVALID_FORMAT",
        "timestamp": datetime.now(tz.utc),
    },
}


# JSON fixtures for API testing
TIME_JSON_EXAMPLES = {
    "simple": {
        "modality_type": "time",
        "timestamp": "2025-01-15T10:30:00Z",
        "timezone": "UTC",
        "format_preference": "24h",
    },
    "us_eastern": {
        "modality_type": "time",
        "timestamp": "2025-01-15T14:00:00Z",
        "timezone": "America/New_York",
        "format_preference": "12h",
        "date_format": "MM/DD/YYYY",
        "locale": "en_US",
    },
    "uk_preferences": {
        "modality_type": "time",
        "timestamp": "2025-01-15T16:00:00Z",
        "timezone": "Europe/London",
        "format_preference": "24h",
        "date_format": "DD/MM/YYYY",
        "locale": "en_GB",
        "week_start": "monday",
    },
}
