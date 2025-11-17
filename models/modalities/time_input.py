"""Time input model."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import Field, field_validator

from models.base_input import ModalityInput


class TimeInput(ModalityInput):
    """Input for updating time-related settings.

    Represents changes to user preferences for time display, including timezone
    and format preferences (12-hour vs 24-hour). This does NOT control simulator
    time - it tracks how the user wants time to be displayed.

    Args:
        modality_type: Always "time" for this input type.
        timestamp: When this settings change logically occurred (simulator time).
        input_id: Unique identifier for this specific settings update.
        timezone: Timezone identifier in IANA format (e.g., "America/New_York", "UTC", "Europe/London").
        format_preference: Time format preference ("12h" or "24h").
        date_format: Optional date format preference (e.g., "MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD").
        locale: Optional locale identifier for localized formatting (e.g., "en_US", "en_GB", "fr_FR").
        week_start: Optional day of week to start on ("sunday" or "monday").
    """

    modality_type: str = Field(default="time", frozen=True)
    timezone: str = Field(
        description="Timezone identifier in IANA format (e.g., 'America/New_York', 'UTC')"
    )
    format_preference: Literal["12h", "24h"] = Field(
        description="Time format preference: 12-hour or 24-hour"
    )
    date_format: Optional[str] = Field(
        default=None,
        description="Date format preference (e.g., 'MM/DD/YYYY', 'DD/MM/YYYY', 'YYYY-MM-DD')",
    )
    locale: Optional[str] = Field(
        default=None,
        description="Locale identifier for localized formatting (e.g., 'en_US', 'en_GB')",
    )
    week_start: Optional[Literal["sunday", "monday"]] = Field(
        default=None, description="First day of the week for calendar display"
    )

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        """Validate timezone is a recognized IANA timezone identifier.

        Args:
            value: Timezone identifier to validate.

        Returns:
            The validated timezone identifier.

        Raises:
            ValueError: If timezone is not recognized.
        """
        try:
            from zoneinfo import ZoneInfo

            ZoneInfo(value)
        except Exception as e:
            raise ValueError(f"Invalid timezone '{value}': {e}")
        return value

    @field_validator("date_format")
    @classmethod
    def validate_date_format(cls, value: Optional[str]) -> Optional[str]:
        """Validate date format contains expected components.

        Args:
            value: Date format string to validate.

        Returns:
            The validated date format.

        Raises:
            ValueError: If date format is invalid.
        """
        if value is None:
            return value

        valid_formats = {
            "MM/DD/YYYY",
            "DD/MM/YYYY",
            "YYYY-MM-DD",
            "YYYY/MM/DD",
            "DD.MM.YYYY",
            "DD-MM-YYYY",
        }
        if value not in valid_formats:
            raise ValueError(
                f"Date format must be one of {valid_formats}, got '{value}'"
            )
        return value

    def validate_input(self) -> None:
        """Perform modality-specific validation beyond Pydantic field validation.

        For TimeInput, all validation is handled by Pydantic field validators.
        This method is provided for consistency with the base class interface.

        Raises:
            ValueError: Never raised (all validation in field validators).
        """
        pass

    def get_affected_entities(self) -> list[str]:
        """Return list of entity IDs affected by this input.

        For time settings, we consider the user's time preferences as a single entity.

        Returns:
            List containing "user_time_preferences".
        """
        return ["user_time_preferences"]

    def get_summary(self) -> str:
        """Return human-readable one-line summary of this input.

        Examples:
            - "Changed timezone to America/New_York (12h format)"
            - "Updated time format to 24h"
            - "Changed timezone to Europe/London (24h format, DD/MM/YYYY)"

        Returns:
            Brief description of the time settings change for logging/UI display.
        """
        parts = [f"timezone to {self.timezone}", f"{self.format_preference} format"]

        if self.date_format:
            parts.append(self.date_format)
        if self.locale:
            parts.append(f"locale: {self.locale}")
        if self.week_start:
            parts.append(f"week starts: {self.week_start}")

        if len(parts) == 2:
            return f"Changed {parts[0]} ({parts[1]})"
        else:
            return f"Updated time settings: {', '.join(parts)}"

    def should_merge_with(self, other: "ModalityInput") -> bool:
        """Determine if this input should be merged with another input.

        Time setting changes within 5 seconds are considered rapid adjustments
        and can be merged to show only the final state.

        Args:
            other: Another input to compare against.

        Returns:
            True if inputs should be merged (within 5 seconds).
        """
        if not isinstance(other, TimeInput):
            return False

        time_diff = abs((self.timestamp - other.timestamp).total_seconds())
        return time_diff <= 5.0
