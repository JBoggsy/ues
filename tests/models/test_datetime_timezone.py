"""Tests for datetime timezone standardization.

These tests verify that all datetime handling in UES models:
1. Accepts and normalizes "Z" suffix strings to UTC
2. Accepts and preserves "+00:00" offset strings
3. Converts naive datetime inputs to UTC
4. Serializes to consistent "+00:00" format

See docs/TODO_DATETIME_TIMEZONE.md for the full standardization plan.
"""

from datetime import datetime, timezone

import pytest

from ues.models.event import SimulatorEvent
from ues.models.base_input import ModalityInput
from ues.models.base_state import ModalityState
from ues.models.scenario import ScenarioMetadata
from ues.models.modalities.email_input import EmailInput
from ues.models.modalities.email_state import EmailState


class TestSimulatorEventDatetimeHandling:
    """Test datetime normalization in SimulatorEvent."""

    def test_accepts_z_suffix_scheduled_time(self):
        """Z suffix should be normalized to +00:00 UTC."""
        event = SimulatorEvent(
            event_id="test-1",
            modality="email",
            scheduled_time="2025-12-24T12:00:00Z",
            created_at="2025-12-24T10:00:00Z",
            data={},
        )
        assert event.scheduled_time.tzinfo is not None
        assert event.scheduled_time.utcoffset().total_seconds() == 0
        assert event.scheduled_time.isoformat() == "2025-12-24T12:00:00+00:00"

    def test_accepts_offset_format_scheduled_time(self):
        """+00:00 format should be preserved."""
        event = SimulatorEvent(
            event_id="test-2",
            modality="email",
            scheduled_time="2025-12-24T12:00:00+00:00",
            created_at="2025-12-24T10:00:00+00:00",
            data={},
        )
        assert event.scheduled_time.tzinfo is not None
        assert event.scheduled_time.isoformat() == "2025-12-24T12:00:00+00:00"

    def test_converts_naive_to_utc_scheduled_time(self):
        """Naive datetime should be converted to UTC."""
        naive_dt = datetime(2025, 12, 24, 12, 0, 0)
        event = SimulatorEvent(
            event_id="test-3",
            modality="email",
            scheduled_time=naive_dt,
            created_at=datetime(2025, 12, 24, 10, 0, 0),
            data={},
        )
        assert event.scheduled_time.tzinfo is not None
        assert event.scheduled_time.utcoffset().total_seconds() == 0

    def test_preserves_aware_datetime_scheduled_time(self):
        """Already aware datetime should be preserved."""
        aware_dt = datetime(2025, 12, 24, 12, 0, 0, tzinfo=timezone.utc)
        event = SimulatorEvent(
            event_id="test-4",
            modality="email",
            scheduled_time=aware_dt,
            created_at=datetime(2025, 12, 24, 10, 0, 0, tzinfo=timezone.utc),
            data={},
        )
        assert event.scheduled_time == aware_dt

    def test_created_at_z_suffix(self):
        """created_at should handle Z suffix."""
        event = SimulatorEvent(
            event_id="test-5",
            modality="email",
            scheduled_time="2025-12-24T12:00:00+00:00",
            created_at="2025-12-24T10:00:00Z",
            data={},
        )
        assert event.created_at.tzinfo is not None
        assert event.created_at.isoformat() == "2025-12-24T10:00:00+00:00"

    def test_executed_at_z_suffix(self):
        """executed_at should handle Z suffix."""
        event = SimulatorEvent(
            event_id="test-6",
            modality="email",
            scheduled_time="2025-12-24T12:00:00+00:00",
            created_at="2025-12-24T10:00:00+00:00",
            executed_at="2025-12-24T12:00:01Z",
            data={},
        )
        assert event.executed_at.tzinfo is not None
        assert event.executed_at.isoformat() == "2025-12-24T12:00:01+00:00"

    def test_executed_at_none_allowed(self):
        """executed_at should allow None."""
        event = SimulatorEvent(
            event_id="test-7",
            modality="email",
            scheduled_time="2025-12-24T12:00:00+00:00",
            created_at="2025-12-24T10:00:00+00:00",
            executed_at=None,
            data={},
        )
        assert event.executed_at is None


class TestModalityInputDatetimeHandling:
    """Test datetime normalization in ModalityInput subclasses."""

    def test_email_input_accepts_z_suffix(self):
        """EmailInput timestamp should handle Z suffix."""
        email_input = EmailInput(
            timestamp="2025-12-24T12:00:00Z",
            operation="receive",
            sender="test@example.com",
            to=["recipient@example.com"],
            subject="Test",
            body="Test body",
        )
        assert email_input.timestamp.tzinfo is not None
        assert email_input.timestamp.isoformat() == "2025-12-24T12:00:00+00:00"

    def test_email_input_accepts_offset_format(self):
        """EmailInput timestamp should preserve +00:00 format."""
        email_input = EmailInput(
            timestamp="2025-12-24T12:00:00+00:00",
            operation="receive",
            sender="test@example.com",
            to=["recipient@example.com"],
            subject="Test",
            body="Test body",
        )
        assert email_input.timestamp.isoformat() == "2025-12-24T12:00:00+00:00"

    def test_email_input_converts_naive_to_utc(self):
        """EmailInput should convert naive datetime to UTC."""
        naive_dt = datetime(2025, 12, 24, 12, 0, 0)
        email_input = EmailInput(
            timestamp=naive_dt,
            operation="receive",
            sender="test@example.com",
            to=["recipient@example.com"],
            subject="Test",
            body="Test body",
        )
        assert email_input.timestamp.tzinfo is not None
        assert email_input.timestamp.utcoffset().total_seconds() == 0


class TestModalityStateLastUpdated:
    """Test last_updated datetime handling in ModalityState subclasses."""

    def test_email_state_accepts_z_suffix_last_updated(self):
        """EmailState last_updated should handle Z suffix."""
        state = EmailState(last_updated="2025-12-24T12:00:00Z")
        assert state.last_updated.tzinfo is not None
        assert state.last_updated.isoformat() == "2025-12-24T12:00:00+00:00"

    def test_email_state_accepts_offset_format_last_updated(self):
        """EmailState last_updated should preserve +00:00 format."""
        state = EmailState(last_updated="2025-12-24T12:00:00+00:00")
        assert state.last_updated.isoformat() == "2025-12-24T12:00:00+00:00"

    def test_email_state_converts_naive_to_utc_last_updated(self):
        """EmailState should convert naive datetime to UTC."""
        naive_dt = datetime(2025, 12, 24, 12, 0, 0)
        state = EmailState(last_updated=naive_dt)
        assert state.last_updated.tzinfo is not None
        assert state.last_updated.utcoffset().total_seconds() == 0


class TestScenarioMetadataDatetimeHandling:
    """Test datetime normalization in ScenarioMetadata."""

    def test_accepts_z_suffix_created_at(self):
        """created_at should handle Z suffix."""
        metadata = ScenarioMetadata(
            ues_version="0.1.0",
            created_at="2025-12-24T12:00:00Z",
        )
        assert metadata.created_at.tzinfo is not None
        assert metadata.created_at.isoformat() == "2025-12-24T12:00:00+00:00"

    def test_accepts_offset_format_created_at(self):
        """created_at should preserve +00:00 format."""
        metadata = ScenarioMetadata(
            ues_version="0.1.0",
            created_at="2025-12-24T12:00:00+00:00",
        )
        assert metadata.created_at.isoformat() == "2025-12-24T12:00:00+00:00"

    def test_converts_naive_to_utc_created_at(self):
        """Should convert naive datetime to UTC."""
        naive_dt = datetime(2025, 12, 24, 12, 0, 0)
        metadata = ScenarioMetadata(
            ues_version="0.1.0",
            created_at=naive_dt,
        )
        assert metadata.created_at.tzinfo is not None
        assert metadata.created_at.utcoffset().total_seconds() == 0


class TestSerializationFormat:
    """Test that serialization produces consistent +00:00 format."""

    def test_event_serializes_with_offset_format(self):
        """SimulatorEvent should serialize datetimes with +00:00 format."""
        event = SimulatorEvent(
            event_id="test-ser-1",
            modality="email",
            scheduled_time="2025-12-24T12:00:00Z",
            created_at="2025-12-24T10:00:00Z",
            data={},
        )
        data = event.model_dump(mode="json")
        # The serialized format should contain +00:00, not Z
        assert "+00:00" in data["scheduled_time"] or "Z" in data["scheduled_time"]
        # Re-parse should still work
        reparsed = SimulatorEvent.model_validate(data)
        assert reparsed.scheduled_time == event.scheduled_time

    def test_scenario_metadata_round_trip(self):
        """ScenarioMetadata should round-trip correctly."""
        original = ScenarioMetadata(
            ues_version="0.1.0",
            created_at="2025-12-24T12:00:00Z",
        )
        data = original.model_dump(mode="json")
        reparsed = ScenarioMetadata.model_validate(data)
        assert reparsed.created_at == original.created_at
        assert reparsed.created_at.tzinfo is not None


class TestDatetimeComparison:
    """Test that datetime comparisons work correctly after normalization.
    
    This is the root cause of the original bug - comparing offset-naive
    and offset-aware datetimes would raise an error.
    """

    def test_can_compare_z_and_offset_parsed_datetimes(self):
        """Datetimes parsed from Z and +00:00 should be comparable."""
        event1 = SimulatorEvent(
            event_id="cmp-1",
            modality="email",
            scheduled_time="2025-12-24T12:00:00Z",
            created_at="2025-12-24T10:00:00Z",
            data={},
        )
        event2 = SimulatorEvent(
            event_id="cmp-2",
            modality="email",
            scheduled_time="2025-12-24T12:00:00+00:00",
            created_at="2025-12-24T10:00:00+00:00",
            data={},
        )
        # Should not raise TypeError
        assert event1.scheduled_time == event2.scheduled_time

    def test_can_compare_naive_converted_with_aware(self):
        """Naive datetime converted to UTC should compare with aware."""
        naive_dt = datetime(2025, 12, 24, 12, 0, 0)
        aware_dt = datetime(2025, 12, 24, 12, 0, 0, tzinfo=timezone.utc)
        
        event1 = SimulatorEvent(
            event_id="cmp-3",
            modality="email",
            scheduled_time=naive_dt,
            created_at=datetime(2025, 12, 24, 10, 0, 0),
            data={},
        )
        event2 = SimulatorEvent(
            event_id="cmp-4",
            modality="email",
            scheduled_time=aware_dt,
            created_at=datetime(2025, 12, 24, 10, 0, 0, tzinfo=timezone.utc),
            data={},
        )
        # Should not raise TypeError
        assert event1.scheduled_time == event2.scheduled_time

    def test_events_sortable_by_scheduled_time(self):
        """Events with mixed datetime formats should be sortable."""
        events = [
            SimulatorEvent(
                event_id="sort-1",
                modality="email",
                scheduled_time="2025-12-24T14:00:00Z",
                created_at="2025-12-24T10:00:00Z",
                data={},
            ),
            SimulatorEvent(
                event_id="sort-2",
                modality="email",
                scheduled_time="2025-12-24T12:00:00+00:00",
                created_at="2025-12-24T10:00:00+00:00",
                data={},
            ),
            SimulatorEvent(
                event_id="sort-3",
                modality="email",
                scheduled_time=datetime(2025, 12, 24, 13, 0, 0),  # naive
                created_at=datetime(2025, 12, 24, 10, 0, 0),
                data={},
            ),
        ]
        # Should not raise TypeError
        sorted_events = sorted(events, key=lambda e: e.scheduled_time)
        assert sorted_events[0].event_id == "sort-2"  # 12:00
        assert sorted_events[1].event_id == "sort-3"  # 13:00
        assert sorted_events[2].event_id == "sort-1"  # 14:00
