"""Unit tests for SimulatorTime.

GENERAL PATTERN TESTS: These test patterns apply to all time management classes
    - Instantiation tests verify proper initialization and validation
    - Mode determination tests verify correct TimeMode derivation from state
    - Serialization tests verify Pydantic round-trip compatibility
    - Fixture tests verify all pytest fixtures work correctly
    - Edge case tests verify handling of boundary values

SIMULATOR_TIME-SPECIFIC TESTS: These verify SimulatorTime-specific functionality
    - Timezone validation ensures all timestamps are timezone-aware
    - calculate_advancement() scaling logic with various time_scale values
    - advance() time progression with validation and side effects
    - set_time() time jumping with backwards prevention
    - pause/resume behavior and wall time anchor updates
    - set_scale() validation and wall time anchor updates
    - get_elapsed_time() calculation with validation
"""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from models.time import SimulatorTime, TimeMode
from tests.fixtures.core.times import (
    FAST_FORWARD_TIME,
    MANUAL_TIME,
    PAUSED_TIME,
    REAL_TIME,
    SLOW_MOTION_TIME,
    UTC_TIME,
    create_simulator_time,
)


class TestSimulatorTimeInstantiation:
    """GENERAL PATTERN: Test instantiation and validation."""

    def test_minimal_instantiation(self):
        """Test creating SimulatorTime with required fields only."""
        now = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        time_obj = SimulatorTime(
            current_time=now,
            last_wall_time_update=now,
        )

        assert time_obj.current_time == now
        assert time_obj.time_scale == 1.0  # default
        assert time_obj.is_paused is False  # default
        assert time_obj.auto_advance is False  # default
        assert time_obj.last_wall_time_update == now

    def test_full_instantiation(self):
        """Test creating SimulatorTime with all fields specified."""
        sim_time = datetime(2025, 3, 15, 14, 30, 0, tzinfo=timezone.utc)
        wall_time = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

        time_obj = SimulatorTime(
            current_time=sim_time,
            time_scale=10.0,
            is_paused=True,
            last_wall_time_update=wall_time,
            auto_advance=True,
        )

        assert time_obj.current_time == sim_time
        assert time_obj.time_scale == 10.0
        assert time_obj.is_paused is True
        assert time_obj.auto_advance is True
        assert time_obj.last_wall_time_update == wall_time

    def test_instantiation_with_factory(self):
        """Test instantiation using create_simulator_time factory."""
        time_obj = create_simulator_time(
            time_scale=5.0,
            is_paused=True,
        )

        assert time_obj.time_scale == 5.0
        assert time_obj.is_paused is True
        assert time_obj.current_time.tzinfo is not None


class TestSimulatorTimeValidation:
    """SIMULATOR_TIME-SPECIFIC: Test validation rules."""

    def test_timezone_aware_current_time_required(self):
        """Test that current_time must be timezone-aware."""
        naive_time = datetime(2025, 1, 15, 12, 0, 0)  # no tzinfo
        wall_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        with pytest.raises(ValidationError) as exc_info:
            SimulatorTime(
                current_time=naive_time,
                last_wall_time_update=wall_time,
            )

        assert "timezone-aware" in str(exc_info.value).lower()

    def test_timezone_aware_wall_time_required(self):
        """Test that last_wall_time_update must be timezone-aware."""
        sim_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        naive_time = datetime(2025, 1, 15, 12, 0, 0)  # no tzinfo

        with pytest.raises(ValidationError) as exc_info:
            SimulatorTime(
                current_time=sim_time,
                last_wall_time_update=naive_time,
            )

        assert "timezone-aware" in str(exc_info.value).lower()

    def test_time_scale_must_be_positive(self):
        """Test that time_scale must be > 0."""
        now = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        with pytest.raises(ValidationError) as exc_info:
            SimulatorTime(
                current_time=now,
                last_wall_time_update=now,
                time_scale=0.0,
            )

        assert "greater than 0" in str(exc_info.value).lower()

    def test_negative_time_scale_rejected(self):
        """Test that negative time_scale is rejected."""
        now = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        with pytest.raises(ValidationError) as exc_info:
            SimulatorTime(
                current_time=now,
                last_wall_time_update=now,
                time_scale=-1.0,
            )

        assert "greater than 0" in str(exc_info.value).lower()


class TestSimulatorTimeModeProperty:
    """SIMULATOR_TIME-SPECIFIC: Test mode determination from state."""

    def test_mode_paused(self):
        """Test mode is PAUSED when is_paused=True."""
        time_obj = create_simulator_time(is_paused=True)

        assert time_obj.mode == TimeMode.PAUSED

    def test_mode_paused_overrides_other_settings(self):
        """Test PAUSED mode takes precedence over auto_advance and scale."""
        time_obj = create_simulator_time(
            is_paused=True,
            auto_advance=True,
            time_scale=100.0,
        )

        assert time_obj.mode == TimeMode.PAUSED

    def test_mode_manual(self):
        """Test mode is MANUAL when not paused and auto_advance=False."""
        time_obj = create_simulator_time(
            is_paused=False,
            auto_advance=False,
        )

        assert time_obj.mode == TimeMode.MANUAL

    def test_mode_real_time(self):
        """Test mode is REAL_TIME when auto_advance and scale=1.0."""
        time_obj = create_simulator_time(
            is_paused=False,
            auto_advance=True,
            time_scale=1.0,
        )

        assert time_obj.mode == TimeMode.REAL_TIME

    def test_mode_fast_forward(self):
        """Test mode is FAST_FORWARD when auto_advance and scale>1.0."""
        time_obj = create_simulator_time(
            is_paused=False,
            auto_advance=True,
            time_scale=100.0,
        )

        assert time_obj.mode == TimeMode.FAST_FORWARD

    def test_mode_slow_motion(self):
        """Test mode is SLOW_MOTION when auto_advance and scale<1.0."""
        time_obj = create_simulator_time(
            is_paused=False,
            auto_advance=True,
            time_scale=0.5,
        )

        assert time_obj.mode == TimeMode.SLOW_MOTION


class TestCalculateAdvancement:
    """SIMULATOR_TIME-SPECIFIC: Test calculate_advancement method."""

    def test_calculate_advancement_paused(self):
        """Test advancement is zero when paused."""
        time_obj = create_simulator_time(is_paused=True, time_scale=100.0)

        advancement = time_obj.calculate_advancement(timedelta(hours=1))

        assert advancement == timedelta(0)

    def test_calculate_advancement_real_time(self):
        """Test advancement matches wall time at 1x scale."""
        time_obj = create_simulator_time(time_scale=1.0)

        advancement = time_obj.calculate_advancement(timedelta(seconds=10))

        assert advancement == timedelta(seconds=10)

    def test_calculate_advancement_fast_forward(self):
        """Test advancement is scaled up for fast-forward."""
        time_obj = create_simulator_time(time_scale=100.0)

        advancement = time_obj.calculate_advancement(timedelta(seconds=1))

        assert advancement == timedelta(seconds=100)

    def test_calculate_advancement_slow_motion(self):
        """Test advancement is scaled down for slow-motion."""
        time_obj = create_simulator_time(time_scale=0.5)

        advancement = time_obj.calculate_advancement(timedelta(seconds=10))

        assert advancement == timedelta(seconds=5)

    def test_calculate_advancement_fractional_scale(self):
        """Test advancement with fractional scale."""
        time_obj = create_simulator_time(time_scale=2.5)

        advancement = time_obj.calculate_advancement(timedelta(seconds=4))

        assert advancement == timedelta(seconds=10)

    def test_calculate_advancement_preserves_microseconds(self):
        """Test that fractional seconds are preserved."""
        time_obj = create_simulator_time(time_scale=1.0)

        advancement = time_obj.calculate_advancement(
            timedelta(seconds=1, microseconds=500000)
        )

        assert advancement == timedelta(seconds=1, microseconds=500000)


class TestAdvance:
    """SIMULATOR_TIME-SPECIFIC: Test advance method."""

    def test_advance_updates_current_time(self):
        """Test that advance updates current_time."""
        start_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        time_obj = create_simulator_time(current_time=start_time)

        time_obj.advance(timedelta(hours=2))

        expected_time = datetime(2025, 1, 15, 14, 0, 0, tzinfo=timezone.utc)
        assert time_obj.current_time == expected_time

    def test_advance_updates_wall_time_update(self):
        """Test that advance updates last_wall_time_update."""
        time_obj = create_simulator_time()
        old_wall_time = time_obj.last_wall_time_update

        time_obj.advance(timedelta(seconds=1))

        # Wall time should be updated (will be slightly later)
        assert time_obj.last_wall_time_update >= old_wall_time

    def test_advance_with_zero_delta(self):
        """Test advancing by zero is allowed."""
        start_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        time_obj = create_simulator_time(current_time=start_time)

        time_obj.advance(timedelta(0))

        assert time_obj.current_time == start_time

    def test_advance_rejects_negative_delta(self):
        """Test that negative deltas are rejected."""
        time_obj = create_simulator_time()

        with pytest.raises(ValueError) as exc_info:
            time_obj.advance(timedelta(hours=-1))

        assert "backwards" in str(exc_info.value).lower()

    def test_advance_rejects_when_paused(self):
        """Test that advance raises error when paused."""
        time_obj = create_simulator_time(is_paused=True)

        with pytest.raises(ValueError) as exc_info:
            time_obj.advance(timedelta(seconds=1))

        assert "paused" in str(exc_info.value).lower()

    def test_advance_multiple_times(self):
        """Test multiple successive advances."""
        start_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        time_obj = create_simulator_time(current_time=start_time)

        time_obj.advance(timedelta(hours=1))
        time_obj.advance(timedelta(minutes=30))
        time_obj.advance(timedelta(seconds=45))

        expected = datetime(2025, 1, 15, 13, 30, 45, tzinfo=timezone.utc)
        assert time_obj.current_time == expected


class TestSetTime:
    """SIMULATOR_TIME-SPECIFIC: Test set_time method."""

    def test_set_time_updates_current_time(self):
        """Test that set_time updates current_time."""
        start_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        new_time = datetime(2025, 1, 15, 14, 0, 0, tzinfo=timezone.utc)
        time_obj = create_simulator_time(current_time=start_time)

        time_obj.set_time(new_time)

        assert time_obj.current_time == new_time

    def test_set_time_updates_wall_time_update(self):
        """Test that set_time updates last_wall_time_update."""
        start_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        new_time = datetime(2025, 1, 15, 14, 0, 0, tzinfo=timezone.utc)
        time_obj = create_simulator_time(current_time=start_time)
        old_wall_time = time_obj.last_wall_time_update

        time_obj.set_time(new_time)

        assert time_obj.last_wall_time_update >= old_wall_time

    def test_set_time_to_same_time(self):
        """Test setting time to current time is allowed."""
        current = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        time_obj = create_simulator_time(current_time=current)

        time_obj.set_time(current)

        assert time_obj.current_time == current

    def test_set_time_rejects_backwards_jump(self):
        """Test that backwards time jumps are rejected."""
        start_time = datetime(2025, 1, 15, 14, 0, 0, tzinfo=timezone.utc)
        past_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        time_obj = create_simulator_time(current_time=start_time)

        with pytest.raises(ValueError) as exc_info:
            time_obj.set_time(past_time)

        assert "backwards" in str(exc_info.value).lower()

    def test_set_time_rejects_naive_datetime(self):
        """Test that naive datetime is rejected."""
        start_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        time_obj = create_simulator_time(current_time=start_time)
        naive_time = datetime(2099, 1, 15, 14, 0, 0)  # no tzinfo, far future

        with pytest.raises(TypeError) as exc_info:
            time_obj.set_time(naive_time)

        assert "compare" in str(exc_info.value).lower()

    def test_set_time_large_jump(self):
        """Test setting time to far future."""
        start_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        future_time = datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        time_obj = create_simulator_time(current_time=start_time)

        time_obj.set_time(future_time)

        assert time_obj.current_time == future_time


class TestPauseResume:
    """SIMULATOR_TIME-SPECIFIC: Test pause and resume methods."""

    def test_pause_sets_is_paused(self):
        """Test that pause() sets is_paused to True."""
        time_obj = create_simulator_time(is_paused=False)

        time_obj.pause()

        assert time_obj.is_paused is True

    def test_pause_changes_mode_to_paused(self):
        """Test that pause() changes mode to PAUSED."""
        time_obj = create_simulator_time(auto_advance=True, time_scale=10.0)
        assert time_obj.mode == TimeMode.FAST_FORWARD

        time_obj.pause()

        assert time_obj.mode == TimeMode.PAUSED

    def test_pause_when_already_paused(self):
        """Test that pausing when already paused is safe."""
        time_obj = create_simulator_time(is_paused=True)

        time_obj.pause()

        assert time_obj.is_paused is True

    def test_resume_clears_is_paused(self):
        """Test that resume() sets is_paused to False."""
        time_obj = create_simulator_time(is_paused=True)

        time_obj.resume()

        assert time_obj.is_paused is False

    def test_resume_updates_wall_time(self):
        """Test that resume() updates last_wall_time_update."""
        time_obj = create_simulator_time(is_paused=True)
        old_wall_time = time_obj.last_wall_time_update

        time_obj.resume()

        # Wall time should be updated to prevent time jump
        assert time_obj.last_wall_time_update >= old_wall_time

    def test_resume_when_not_paused(self):
        """Test that resuming when not paused is safe."""
        time_obj = create_simulator_time(is_paused=False)

        time_obj.resume()

        assert time_obj.is_paused is False

    def test_pause_resume_cycle(self):
        """Test multiple pause/resume cycles."""
        time_obj = create_simulator_time(is_paused=False)

        time_obj.pause()
        assert time_obj.is_paused is True

        time_obj.resume()
        assert time_obj.is_paused is False

        time_obj.pause()
        assert time_obj.is_paused is True


class TestSetScale:
    """SIMULATOR_TIME-SPECIFIC: Test set_scale method."""

    def test_set_scale_updates_time_scale(self):
        """Test that set_scale updates time_scale."""
        time_obj = create_simulator_time(time_scale=1.0)

        time_obj.set_scale(10.0)

        assert time_obj.time_scale == 10.0

    def test_set_scale_updates_wall_time(self):
        """Test that set_scale updates last_wall_time_update."""
        time_obj = create_simulator_time()
        old_wall_time = time_obj.last_wall_time_update

        time_obj.set_scale(5.0)

        # Wall time should be updated to prevent unexpected jumps
        assert time_obj.last_wall_time_update >= old_wall_time

    def test_set_scale_changes_mode(self):
        """Test that changing scale changes mode."""
        time_obj = create_simulator_time(auto_advance=True, time_scale=1.0)
        assert time_obj.mode == TimeMode.REAL_TIME

        time_obj.set_scale(100.0)

        assert time_obj.mode == TimeMode.FAST_FORWARD

    def test_set_scale_to_slow_motion(self):
        """Test setting scale to slow motion."""
        time_obj = create_simulator_time(auto_advance=True, time_scale=10.0)

        time_obj.set_scale(0.5)

        assert time_obj.time_scale == 0.5
        assert time_obj.mode == TimeMode.SLOW_MOTION

    def test_set_scale_rejects_zero(self):
        """Test that scale=0 is rejected."""
        time_obj = create_simulator_time()

        with pytest.raises(ValueError) as exc_info:
            time_obj.set_scale(0.0)

        assert "positive" in str(exc_info.value).lower()

    def test_set_scale_rejects_negative(self):
        """Test that negative scale is rejected."""
        time_obj = create_simulator_time()

        with pytest.raises(ValueError) as exc_info:
            time_obj.set_scale(-1.0)

        assert "positive" in str(exc_info.value).lower()

    def test_set_scale_very_small(self):
        """Test setting very small positive scale."""
        time_obj = create_simulator_time()

        time_obj.set_scale(0.001)

        assert time_obj.time_scale == 0.001

    def test_set_scale_very_large(self):
        """Test setting very large scale."""
        time_obj = create_simulator_time()

        time_obj.set_scale(10000.0)

        assert time_obj.time_scale == 10000.0


class TestGetElapsedTime:
    """SIMULATOR_TIME-SPECIFIC: Test get_elapsed_time method."""

    def test_get_elapsed_time_basic(self):
        """Test basic elapsed time calculation."""
        current = datetime(2025, 1, 15, 14, 0, 0, tzinfo=timezone.utc)
        past = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        time_obj = create_simulator_time(current_time=current)

        elapsed = time_obj.get_elapsed_time(past)

        assert elapsed == timedelta(hours=2)

    def test_get_elapsed_time_zero(self):
        """Test elapsed time from current time is zero."""
        current = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        time_obj = create_simulator_time(current_time=current)

        elapsed = time_obj.get_elapsed_time(current)

        assert elapsed == timedelta(0)

    def test_get_elapsed_time_with_microseconds(self):
        """Test elapsed time calculation preserves microseconds."""
        current = datetime(2025, 1, 15, 12, 0, 1, 500000, tzinfo=timezone.utc)
        past = datetime(2025, 1, 15, 12, 0, 0, 0, tzinfo=timezone.utc)
        time_obj = create_simulator_time(current_time=current)

        elapsed = time_obj.get_elapsed_time(past)

        assert elapsed == timedelta(seconds=1, microseconds=500000)

    def test_get_elapsed_time_rejects_future(self):
        """Test that future time is rejected."""
        current = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        future = datetime(2025, 1, 15, 14, 0, 0, tzinfo=timezone.utc)
        time_obj = create_simulator_time(current_time=current)

        with pytest.raises(ValueError) as exc_info:
            time_obj.get_elapsed_time(future)

        assert "future" in str(exc_info.value).lower()

    def test_get_elapsed_time_long_duration(self):
        """Test elapsed time over long duration."""
        current = datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        past = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        time_obj = create_simulator_time(current_time=current)

        elapsed = time_obj.get_elapsed_time(past)

        # 365 days minus 1 second
        expected = timedelta(days=365, seconds=-1)
        assert elapsed == expected


class TestSimulatorTimeSerialization:
    """GENERAL PATTERN: Test Pydantic serialization."""

    def test_serialization_to_dict(self):
        """Test serialization to dictionary."""
        now = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        time_obj = SimulatorTime(
            current_time=now,
            time_scale=10.0,
            is_paused=True,
            last_wall_time_update=now,
            auto_advance=True,
        )

        data = time_obj.model_dump()

        assert data["time_scale"] == 10.0
        assert data["is_paused"] is True
        assert data["auto_advance"] is True

    def test_serialization_round_trip(self):
        """Test serialize and deserialize preserves data."""
        now = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        original = SimulatorTime(
            current_time=now,
            time_scale=5.5,
            is_paused=False,
            last_wall_time_update=now,
            auto_advance=True,
        )

        data = original.model_dump()
        restored = SimulatorTime.model_validate(data)

        assert restored.current_time == original.current_time
        assert restored.time_scale == original.time_scale
        assert restored.is_paused == original.is_paused
        assert restored.auto_advance == original.auto_advance

    def test_serialization_mode_not_included(self):
        """Test that mode property is not serialized (computed)."""
        time_obj = create_simulator_time(is_paused=True)

        data = time_obj.model_dump()

        # mode is a computed property, not stored
        assert "mode" not in data


class TestSimulatorTimeFromFixtures:
    """GENERAL PATTERN: Test that all fixtures work correctly."""

    def test_utc_time_fixture(self):
        """Test UTC_TIME fixture."""
        assert UTC_TIME.current_time.tzinfo is not None
        assert UTC_TIME.time_scale == 1.0
        assert UTC_TIME.is_paused is False

    def test_paused_time_fixture(self):
        """Test PAUSED_TIME fixture."""
        assert PAUSED_TIME.is_paused is True
        assert PAUSED_TIME.mode == TimeMode.PAUSED

    def test_fast_forward_time_fixture(self):
        """Test FAST_FORWARD_TIME fixture."""
        assert FAST_FORWARD_TIME.time_scale == 100.0
        assert FAST_FORWARD_TIME.auto_advance is True
        assert FAST_FORWARD_TIME.mode == TimeMode.FAST_FORWARD

    def test_slow_motion_time_fixture(self):
        """Test SLOW_MOTION_TIME fixture."""
        assert SLOW_MOTION_TIME.time_scale == 0.5
        assert SLOW_MOTION_TIME.auto_advance is True
        assert SLOW_MOTION_TIME.mode == TimeMode.SLOW_MOTION

    def test_real_time_fixture(self):
        """Test REAL_TIME fixture."""
        assert REAL_TIME.time_scale == 1.0
        assert REAL_TIME.auto_advance is True
        assert REAL_TIME.mode == TimeMode.REAL_TIME

    def test_manual_time_fixture(self):
        """Test MANUAL_TIME fixture."""
        assert MANUAL_TIME.auto_advance is False
        assert MANUAL_TIME.is_paused is False
        assert MANUAL_TIME.mode == TimeMode.MANUAL


class TestSimulatorTimeEdgeCases:
    """GENERAL PATTERN: Test edge cases and boundary conditions."""

    def test_extremely_large_time_scale(self):
        """Test with extremely large time scale."""
        time_obj = create_simulator_time(time_scale=1e10)

        advancement = time_obj.calculate_advancement(timedelta(microseconds=1))

        # 1 microsecond * 1e10 = 10000 seconds
        assert advancement == timedelta(seconds=10000)

    def test_extremely_small_time_scale(self):
        """Test with extremely small time scale."""
        time_obj = create_simulator_time(time_scale=1e-10)

        advancement = time_obj.calculate_advancement(timedelta(days=1))

        # Very small advancement
        assert advancement.total_seconds() < 0.01

    def test_advance_by_microseconds(self):
        """Test advancing by very small amounts."""
        start_time = datetime(2025, 1, 15, 12, 0, 0, 0, tzinfo=timezone.utc)
        time_obj = create_simulator_time(current_time=start_time)

        time_obj.advance(timedelta(microseconds=1))

        expected = datetime(2025, 1, 15, 12, 0, 0, 1, tzinfo=timezone.utc)
        assert time_obj.current_time == expected

    def test_advance_by_large_duration(self):
        """Test advancing by very large duration."""
        start_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        time_obj = create_simulator_time(current_time=start_time)

        # Advance by 1000 days
        time_obj.advance(timedelta(days=1000))

        # 1000 days from 2025-01-01 is 2027-09-28
        expected = datetime(2027, 9, 28, 0, 0, 0, tzinfo=timezone.utc)
        assert time_obj.current_time == expected

    def test_set_time_across_year_boundary(self):
        """Test setting time across year boundary."""
        start_time = datetime(2025, 12, 31, 23, 0, 0, tzinfo=timezone.utc)
        new_time = datetime(2026, 1, 1, 1, 0, 0, tzinfo=timezone.utc)
        time_obj = create_simulator_time(current_time=start_time)

        time_obj.set_time(new_time)

        assert time_obj.current_time == new_time


class TestSimulatorTimeIntegration:
    """GENERAL PATTERN: Test integration scenarios."""

    def test_pause_advance_resume_cycle(self):
        """Test complete pause/advance/resume workflow."""
        start_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        time_obj = create_simulator_time(current_time=start_time, is_paused=False)

        # Pause
        time_obj.pause()
        assert time_obj.mode == TimeMode.PAUSED

        # Try to advance while paused (should fail)
        with pytest.raises(ValueError):
            time_obj.advance(timedelta(hours=1))

        # Resume and advance
        time_obj.resume()
        time_obj.advance(timedelta(hours=1))

        expected = datetime(2025, 1, 15, 13, 0, 0, tzinfo=timezone.utc)
        assert time_obj.current_time == expected

    def test_scale_change_during_simulation(self):
        """Test changing time scale during simulation."""
        time_obj = create_simulator_time(
            auto_advance=True,
            time_scale=1.0,
        )

        # Start in real-time mode
        assert time_obj.mode == TimeMode.REAL_TIME
        advancement1 = time_obj.calculate_advancement(timedelta(seconds=10))
        assert advancement1 == timedelta(seconds=10)

        # Change to fast-forward
        time_obj.set_scale(100.0)
        assert time_obj.mode == TimeMode.FAST_FORWARD
        advancement2 = time_obj.calculate_advancement(timedelta(seconds=10))
        assert advancement2 == timedelta(seconds=1000)

        # Change to slow-motion
        time_obj.set_scale(0.5)
        assert time_obj.mode == TimeMode.SLOW_MOTION
        advancement3 = time_obj.calculate_advancement(timedelta(seconds=10))
        assert advancement3 == timedelta(seconds=5)

    def test_mixed_advance_and_set_time(self):
        """Test mixing advance() and set_time() calls."""
        start_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        time_obj = create_simulator_time(current_time=start_time)

        # Advance by 1 hour
        time_obj.advance(timedelta(hours=1))
        assert time_obj.current_time == datetime(
            2025, 1, 15, 13, 0, 0, tzinfo=timezone.utc
        )

        # Jump to 16:00
        time_obj.set_time(datetime(2025, 1, 15, 16, 0, 0, tzinfo=timezone.utc))
        assert time_obj.current_time == datetime(
            2025, 1, 15, 16, 0, 0, tzinfo=timezone.utc
        )

        # Advance by 30 minutes
        time_obj.advance(timedelta(minutes=30))
        assert time_obj.current_time == datetime(
            2025, 1, 15, 16, 30, 0, tzinfo=timezone.utc
        )

    def test_elapsed_time_tracking_across_operations(self):
        """Test tracking elapsed time across various operations."""
        start_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        reference_time = start_time
        time_obj = create_simulator_time(current_time=start_time)

        # Check initial elapsed
        assert time_obj.get_elapsed_time(reference_time) == timedelta(0)

        # Advance and check
        time_obj.advance(timedelta(hours=2))
        assert time_obj.get_elapsed_time(reference_time) == timedelta(hours=2)

        # Set time and check
        time_obj.set_time(datetime(2025, 1, 15, 16, 0, 0, tzinfo=timezone.utc))
        assert time_obj.get_elapsed_time(reference_time) == timedelta(hours=4)

        # Pause doesn't affect elapsed time
        time_obj.pause()
        assert time_obj.get_elapsed_time(reference_time) == timedelta(hours=4)
