"""Simulator time management model."""

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class TimeMode(str, Enum):
    """Time control mode for the simulation."""

    PAUSED = "paused"
    MANUAL = "manual"
    REAL_TIME = "real_time"
    FAST_FORWARD = "fast_forward"
    SLOW_MOTION = "slow_motion"
    EVENT_DRIVEN = "event_driven"


class SimulatorTime(BaseModel):
    """Manages simulator time state.

    Simulator time is completely decoupled from wall-clock time,
    allowing for fast-forwarding, pausing, and instant jumps.
    See docs/SIMULATOR_TIME.md for detailed design.

    This class tracks the current state of time and provides methods
    for time calculations and queries. It does NOT advance itself -
    that's the SimulationEngine's responsibility.

    Args:
        current_time: The current simulator timestamp (timezone-aware).
        time_scale: Multiplier for time advancement (1.0 = real-time, must be > 0).
        is_paused: Whether time advancement is currently frozen.
        last_wall_time_update: Wall-clock time when current_time was last updated.
        auto_advance: Whether time automatically advances based on wall time.
    """

    current_time: datetime = Field(
        description="The current simulator timestamp (timezone-aware)"
    )
    time_scale: float = Field(
        default=1.0,
        description="Multiplier for time advancement (1.0 = real-time)",
        gt=0.0,
    )
    is_paused: bool = Field(
        default=False, description="Whether time advancement is currently frozen"
    )
    last_wall_time_update: datetime = Field(
        description="Wall-clock time when current_time was last updated"
    )
    auto_advance: bool = Field(
        default=False,
        description="Whether time automatically advances based on wall time",
    )

    @field_validator("current_time", "last_wall_time_update")
    @classmethod
    def validate_timezone_aware(cls, v: datetime) -> datetime:
        """Ensure datetime is timezone-aware."""
        if v.tzinfo is None:
            raise ValueError("Datetime must be timezone-aware (recommend UTC)")
        return v

    @property
    def mode(self) -> TimeMode:
        """Determine current time control mode based on state.

        Returns:
            Current TimeMode based on is_paused, auto_advance, and time_scale.
        """
        if self.is_paused:
            return TimeMode.PAUSED
        if not self.auto_advance:
            return TimeMode.MANUAL
        if self.time_scale == 1.0:
            return TimeMode.REAL_TIME
        if self.time_scale > 1.0:
            return TimeMode.FAST_FORWARD
        return TimeMode.SLOW_MOTION

    def calculate_advancement(self, wall_time_elapsed: timedelta) -> timedelta:
        """Calculate how much simulator time should advance for given wall time.

        Takes into account time_scale and is_paused state.

        Examples:
            - time_scale=1.0, wall_elapsed=10s → sim_advance=10s
            - time_scale=100.0, wall_elapsed=1s → sim_advance=100s
            - is_paused=True → sim_advance=0s (always)

        Args:
            wall_time_elapsed: Wall-clock time that has elapsed.

        Returns:
            Amount of simulator time to advance.
        """
        if self.is_paused:
            return timedelta(0)

        # Calculate scaled advancement
        total_seconds = wall_time_elapsed.total_seconds() * self.time_scale
        return timedelta(seconds=total_seconds)

    def advance(self, delta: timedelta) -> None:
        """Advance simulator time by the specified delta.

        Updates current_time and last_wall_time_update.
        Does NOT execute events - that's SimulationEngine's job.

        Args:
            delta: Amount of simulator time to advance.

        Raises:
            ValueError: If delta is negative or time is paused.
        """
        if delta < timedelta(0):
            raise ValueError("Cannot advance time backwards")

        if self.is_paused:
            raise ValueError("Cannot advance time while paused")

        self.current_time += delta
        self.last_wall_time_update = datetime.now(timezone.utc)

    def set_time(self, new_time: datetime) -> None:
        """Set simulator time to a specific value (time jump).

        Used for manual time setting via API or event-driven mode.
        Updates current_time and last_wall_time_update.

        Args:
            new_time: New simulator time to set.

        Raises:
            ValueError: If new_time is before current_time (no backwards jumps).
        """
        if new_time < self.current_time:
            raise ValueError(
                f"Cannot set time backwards: {new_time} < {self.current_time}"
            )

        if new_time.tzinfo is None:
            raise ValueError("new_time must be timezone-aware")

        self.current_time = new_time
        self.last_wall_time_update = datetime.now(timezone.utc)

    def pause(self) -> None:
        """Pause time advancement.

        Sets is_paused=True. Time will not advance until resume() is called.
        """
        self.is_paused = True

    def resume(self) -> None:
        """Resume time advancement from paused state.

        Sets is_paused=False and updates last_wall_time_update to now
        to prevent time jump when resuming.
        """
        self.is_paused = False
        self.last_wall_time_update = datetime.now(timezone.utc)

    def set_scale(self, scale: float) -> None:
        """Set time advancement scale.

        Args:
            scale: New time scale (must be > 0.0).

        Raises:
            ValueError: If scale <= 0.0.
        """
        if scale <= 0.0:
            raise ValueError(f"Time scale must be positive, got {scale}")

        self.time_scale = scale
        # Update wall time anchor to prevent unexpected jumps
        self.last_wall_time_update = datetime.now(timezone.utc)

    def get_elapsed_time(self, since: datetime) -> timedelta:
        """Calculate simulator time elapsed since a specific time.

        Args:
            since: Past simulator time to calculate from.

        Returns:
            Simulator time elapsed (current_time - since).

        Raises:
            ValueError: If since is in the future.
        """
        if since > self.current_time:
            raise ValueError(
                f"'since' time is in the future: {since} > {self.current_time}"
            )

        return self.current_time - since

    def format_time(self, format_str: Optional[str] = None) -> str:
        """Format current simulator time as a string.

        Args:
            format_str: Optional strftime format string (default: ISO 8601).

        Returns:
            Formatted time string.
        """
        if format_str is None:
            return self.current_time.isoformat()
        return self.current_time.strftime(format_str)

    def to_dict(self) -> dict:
        """Export time state as dictionary for API responses.

        Returns:
            Dictionary with all time state fields.
        """
        return {
            "current_time": self.current_time.isoformat(),
            "time_scale": self.time_scale,
            "is_paused": self.is_paused,
            "auto_advance": self.auto_advance,
            "mode": self.mode.value,
            "last_wall_time_update": self.last_wall_time_update.isoformat(),
        }

    def validate(self) -> list[str]:
        """Validate time state consistency.

        Checks:
            - time_scale > 0.0
            - current_time is timezone-aware
            - last_wall_time_update is timezone-aware
            - No logical inconsistencies

        Returns:
            List of validation errors (empty if valid).
        """
        errors = []

        # Check time_scale
        if self.time_scale <= 0.0:
            errors.append(f"time_scale must be positive, got {self.time_scale}")

        # Check timezone awareness (should be caught by validator, but double-check)
        if self.current_time.tzinfo is None:
            errors.append("current_time must be timezone-aware")

        if self.last_wall_time_update.tzinfo is None:
            errors.append("last_wall_time_update must be timezone-aware")

        # Check for logical consistency
        if self.auto_advance and self.is_paused:
            # This is actually valid - paused overrides auto_advance
            # Just a warning-level note, not an error
            pass

        return errors
