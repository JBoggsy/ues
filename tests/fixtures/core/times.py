"""Fixtures for SimulatorTime."""

from datetime import datetime, timezone

from models.time import SimulatorTime, TimeMode


def create_simulator_time(
    current_time: datetime | None = None,
    time_scale: float = 1.0,
    is_paused: bool = False,
    auto_advance: bool = False,
    **kwargs,
) -> SimulatorTime:
    """Create a SimulatorTime with sensible defaults.

    Args:
        current_time: Current simulator time (defaults to now).
        time_scale: Time advancement multiplier (default: 1.0).
        is_paused: Whether time is frozen (default: False).
        auto_advance: Whether time auto-advances (default: False).
        **kwargs: Additional fields to override.

    Returns:
        SimulatorTime instance ready for testing.
    """
    now = datetime.now(timezone.utc)
    
    return SimulatorTime(
        current_time=current_time or now,
        time_scale=time_scale,
        is_paused=is_paused,
        last_wall_time_update=kwargs.get("last_wall_time_update", now),
        auto_advance=auto_advance,
    )


# Pre-built example constants
UTC_TIME = create_simulator_time(
    current_time=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
)

PAUSED_TIME = create_simulator_time(
    current_time=datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
    is_paused=True,
)

FAST_FORWARD_TIME = create_simulator_time(
    current_time=datetime(2025, 1, 15, 9, 0, 0, tzinfo=timezone.utc),
    time_scale=100.0,
    auto_advance=True,
)

SLOW_MOTION_TIME = create_simulator_time(
    current_time=datetime(2025, 1, 15, 14, 0, 0, tzinfo=timezone.utc),
    time_scale=0.5,
    auto_advance=True,
)

REAL_TIME = create_simulator_time(
    current_time=datetime(2025, 1, 15, 8, 0, 0, tzinfo=timezone.utc),
    time_scale=1.0,
    auto_advance=True,
)

MANUAL_TIME = create_simulator_time(
    current_time=datetime(2025, 1, 15, 16, 0, 0, tzinfo=timezone.utc),
    time_scale=1.0,
    auto_advance=False,
    is_paused=False,
)


# JSON fixtures for API testing
TIME_JSON_EXAMPLES = {
    "paused": {
        "current_time": "2025-01-15T10:00:00Z",
        "time_scale": 1.0,
        "is_paused": True,
        "last_wall_time_update": "2025-01-15T10:00:00Z",
        "auto_advance": False,
    },
    "fast_forward": {
        "current_time": "2025-01-15T09:00:00Z",
        "time_scale": 100.0,
        "is_paused": False,
        "last_wall_time_update": "2025-01-15T09:00:00Z",
        "auto_advance": True,
    },
}
