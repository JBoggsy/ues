"""Time state model."""

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from models.base_input import ModalityInput
from models.base_state import ModalityState


class TimeSettingsHistoryEntry(BaseModel):
    """A single entry in the time settings history.

    Tracks historical time preference changes with timestamp.

    Args:
        timestamp: When this settings change occurred.
        timezone: Timezone identifier at this point.
        format_preference: Time format preference at this point.
        date_format: Date format preference if set.
        locale: Locale identifier if set.
        week_start: Week start preference if set.
    """

    timestamp: datetime = Field(description="When this settings change occurred")
    timezone: str = Field(description="Timezone identifier")
    format_preference: Literal["12h", "24h"] = Field(description="Time format preference")
    date_format: Optional[str] = Field(default=None, description="Date format preference")
    locale: Optional[str] = Field(default=None, description="Locale identifier")
    week_start: Optional[Literal["sunday", "monday"]] = Field(default=None, description="Week start preference")

    def to_dict(self) -> dict[str, Any]:
        """Convert this entry to a dictionary.

        Returns:
            Dictionary representation of this settings entry.
        """
        result = {
            "timestamp": self.timestamp.isoformat(),
            "timezone": self.timezone,
            "format_preference": self.format_preference,
        }
        if self.date_format:
            result["date_format"] = self.date_format
        if self.locale:
            result["locale"] = self.locale
        if self.week_start:
            result["week_start"] = self.week_start
        return result


class TimeState(ModalityState):
    """Current time-related state.

    Tracks user preferences for time display including timezone, format preferences,
    and related localization settings. This does NOT track simulator time - it tracks
    how the user wants time to be displayed to them.

    Args:
        modality_type: Always "time" for this state type.
        last_updated: Simulator time when this state was last modified.
        update_count: Number of times this state has been modified.
        timezone: Current timezone identifier in IANA format.
        format_preference: Current time format preference ("12h" or "24h").
        date_format: Current date format preference.
        locale: Current locale identifier for localized formatting.
        week_start: Current week start preference ("sunday" or "monday").
        settings_history: List of historical settings changes.
        max_history_size: Maximum number of historical settings to retain.
    """

    modality_type: str = Field(default="time", frozen=True)
    timezone: str = Field(
        default="UTC", description="Current timezone identifier in IANA format"
    )
    format_preference: Literal["12h", "24h"] = Field(
        default="12h", description="Current time format preference"
    )
    date_format: Optional[str] = Field(
        default=None, description="Current date format preference"
    )
    locale: Optional[str] = Field(
        default=None, description="Current locale identifier"
    )
    week_start: Optional[Literal["sunday", "monday"]] = Field(
        default=None, description="Current week start preference"
    )
    settings_history: list[TimeSettingsHistoryEntry] = Field(
        default_factory=list, description="List of historical settings changes"
    )
    max_history_size: int = Field(
        default=50, description="Maximum number of historical settings to retain"
    )

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True

    def apply_input(self, input_data: ModalityInput) -> None:
        """Apply a TimeInput to modify this state.

        Updates the current time preferences and adds the previous settings to history.
        Automatically manages history size by removing oldest entries when needed.

        Args:
            input_data: The TimeInput to apply to this state.

        Raises:
            ValueError: If input_data is not a TimeInput.
        """
        from models.modalities.time_input import TimeInput

        if not isinstance(input_data, TimeInput):
            raise ValueError(
                f"TimeState can only apply TimeInput, got {type(input_data)}"
            )

        previous_entry = TimeSettingsHistoryEntry(
            timestamp=self.last_updated,
            timezone=self.timezone,
            format_preference=self.format_preference,
            date_format=self.date_format,
            locale=self.locale,
            week_start=self.week_start,
        )
        self.settings_history.append(previous_entry)

        if len(self.settings_history) > self.max_history_size:
            self.settings_history.pop(0)

        self.timezone = input_data.timezone
        self.format_preference = input_data.format_preference
        self.date_format = input_data.date_format
        self.locale = input_data.locale
        self.week_start = input_data.week_start

        self.last_updated = input_data.timestamp
        self.update_count += 1

    def get_snapshot(self) -> dict[str, Any]:
        """Return a complete snapshot of current state for API responses.

        Returns:
            Dictionary representation of current time settings suitable for API responses.
        """
        snapshot: dict[str, Any] = {
            "modality_type": self.modality_type,
            "last_updated": self.last_updated.isoformat(),
            "update_count": self.update_count,
            "current": {
                "timezone": self.timezone,
                "format_preference": self.format_preference,
            },
            "history": [entry.to_dict() for entry in self.settings_history],
        }

        if self.date_format:
            snapshot["current"]["date_format"] = self.date_format
        if self.locale:
            snapshot["current"]["locale"] = self.locale
        if self.week_start:
            snapshot["current"]["week_start"] = self.week_start

        return snapshot

    def validate_state(self) -> list[str]:
        """Validate internal state consistency and return any issues.

        Checks for:
        - Valid timezone identifier
        - History entries are in chronological order
        - History size doesn't exceed maximum

        Returns:
            List of validation error messages (empty list if valid).
        """
        issues = []

        try:
            from zoneinfo import ZoneInfo

            ZoneInfo(self.timezone)
        except Exception:
            issues.append(f"Invalid timezone identifier: {self.timezone}")

        for i in range(1, len(self.settings_history)):
            if (
                self.settings_history[i].timestamp
                < self.settings_history[i - 1].timestamp
            ):
                issues.append(
                    f"Settings history not in chronological order at index {i}"
                )

        if len(self.settings_history) > self.max_history_size:
            issues.append(
                f"Settings history size {len(self.settings_history)} exceeds maximum {self.max_history_size}"
            )

        return issues

    def query(self, query_params: dict[str, Any]) -> dict[str, Any]:
        """Execute a query against this state.

        Supports filtering settings history by various criteria.

        Supported query parameters:
            - since: datetime - Return settings changes after this time
            - until: datetime - Return settings changes before this time
            - timezone: str - Return settings with this timezone
            - format_preference: str - Return settings with this format
            - limit: int - Maximum number of results to return
            - include_current: bool - Include current settings in results (default: True)

        Args:
            query_params: Dictionary of query parameters.

        Returns:
            Dictionary containing query results with matching settings.
        """
        since = query_params.get("since")
        until = query_params.get("until")
        timezone_filter = query_params.get("timezone")
        format_filter = query_params.get("format_preference")
        limit = query_params.get("limit")
        include_current = query_params.get("include_current", True)

        results = []

        if include_current:
            current_entry = {
                "timestamp": self.last_updated.isoformat(),
                "timezone": self.timezone,
                "format_preference": self.format_preference,
                "is_current": True,
            }
            if self.date_format:
                current_entry["date_format"] = self.date_format
            if self.locale:
                current_entry["locale"] = self.locale
            if self.week_start:
                current_entry["week_start"] = self.week_start

            if (
                (since is None or self.last_updated >= since)
                and (until is None or self.last_updated <= until)
                and (timezone_filter is None or self.timezone == timezone_filter)
                and (
                    format_filter is None
                    or self.format_preference == format_filter
                )
            ):
                results.append(current_entry)

        for entry in reversed(self.settings_history):
            if (
                (since is None or entry.timestamp >= since)
                and (until is None or entry.timestamp <= until)
                and (timezone_filter is None or entry.timezone == timezone_filter)
                and (
                    format_filter is None
                    or entry.format_preference == format_filter
                )
            ):
                entry_dict = entry.to_dict()
                entry_dict["is_current"] = False
                results.append(entry_dict)

        if limit is not None:
            results = results[:limit]

        return {"settings": results, "count": len(results)}

    def format_time(self, time: datetime) -> str:
        """Format a datetime according to current user preferences.

        This is a convenience method for formatting times according to the user's
        current timezone and format preferences.

        Args:
            time: The datetime to format (assumed to be in UTC or have timezone info).

        Returns:
            Formatted time string according to user preferences.
        """
        from zoneinfo import ZoneInfo

        localized_time = time.astimezone(ZoneInfo(self.timezone))

        if self.format_preference == "12h":
            time_str = localized_time.strftime("%I:%M %p")
        else:
            time_str = localized_time.strftime("%H:%M")

        return time_str

    def format_datetime(self, time: datetime) -> str:
        """Format a datetime with date according to current user preferences.

        Args:
            time: The datetime to format.

        Returns:
            Formatted datetime string according to user preferences.
        """
        from zoneinfo import ZoneInfo

        localized_time = time.astimezone(ZoneInfo(self.timezone))

        date_format_map = {
            "MM/DD/YYYY": "%m/%d/%Y",
            "DD/MM/YYYY": "%d/%m/%Y",
            "YYYY-MM-DD": "%Y-%m-%d",
            "YYYY/MM/DD": "%Y/%m/%d",
            "DD.MM.YYYY": "%d.%m.%Y",
            "DD-MM-YYYY": "%d-%m-%Y",
        }

        date_str = localized_time.strftime(
            date_format_map.get(self.date_format or "YYYY-MM-DD", "%Y-%m-%d")
        )
        time_str = self.format_time(localized_time)

        return f"{date_str} {time_str}"
