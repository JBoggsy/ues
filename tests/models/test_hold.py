"""Unit tests for the Hold model and HoldManager.

Tests verify hold creation, expiration, management, and error handling.
"""

import time
from datetime import datetime, timedelta, timezone

import pytest

from models.hold import Hold, HoldError, HoldManager


class TestHold:
    """Tests for the Hold model."""

    def test_hold_instantiation_with_defaults(self):
        """Test that Hold can be instantiated with default values."""
        hold = Hold()
        
        assert hold.hold_id is not None
        assert len(hold.hold_id) > 0
        assert hold.reason is None
        assert hold.timeout_seconds is None
        assert hold.agent_id is None
        assert hold.acquired_at is not None

    def test_hold_instantiation_with_custom_values(self):
        """Test that Hold can be instantiated with custom values."""
        hold = Hold(
            reason="Testing hold",
            timeout_seconds=60.0,
            agent_id="agent-123",
        )
        
        assert hold.reason == "Testing hold"
        assert hold.timeout_seconds == 60.0
        assert hold.agent_id == "agent-123"

    def test_hold_expires_at_with_timeout(self):
        """Test that expires_at is calculated correctly when timeout is set."""
        hold = Hold(timeout_seconds=60.0)
        
        assert hold.expires_at is not None
        expected_expiry = hold.acquired_at + timedelta(seconds=60.0)
        assert abs((hold.expires_at - expected_expiry).total_seconds()) < 1

    def test_hold_expires_at_without_timeout(self):
        """Test that expires_at is None when no timeout is set."""
        hold = Hold(timeout_seconds=None)
        
        assert hold.expires_at is None

    def test_hold_is_expired_returns_false_when_no_timeout(self):
        """Test that is_expired returns False when no timeout is set."""
        hold = Hold(timeout_seconds=None)
        
        assert hold.is_expired() is False

    def test_hold_is_expired_returns_false_when_not_expired(self):
        """Test that is_expired returns False before timeout."""
        hold = Hold(timeout_seconds=3600.0)  # 1 hour
        
        assert hold.is_expired() is False

    def test_hold_is_expired_returns_true_when_expired(self):
        """Test that is_expired returns True after timeout."""
        # Create hold with a past acquired_at time
        past_time = datetime.now(timezone.utc) - timedelta(seconds=100)
        hold = Hold(
            timeout_seconds=60.0,
            acquired_at=past_time,
        )
        
        assert hold.is_expired() is True

    def test_hold_unique_ids(self):
        """Test that each Hold gets a unique ID."""
        holds = [Hold() for _ in range(10)]
        hold_ids = [h.hold_id for h in holds]
        
        assert len(hold_ids) == len(set(hold_ids))


class TestHoldManager:
    """Tests for the HoldManager."""

    def test_holdmanager_instantiation(self):
        """Test that HoldManager can be instantiated."""
        manager = HoldManager()
        
        assert manager.active_holds == {}
        assert manager.default_timeout_seconds == 300.0

    def test_acquire_returns_hold_id(self):
        """Test that acquire returns a hold ID."""
        manager = HoldManager()
        
        hold_id = manager.acquire(reason="Test")
        
        assert hold_id is not None
        assert len(hold_id) > 0

    def test_acquire_stores_hold(self):
        """Test that acquire stores the hold in active_holds."""
        manager = HoldManager()
        
        hold_id = manager.acquire(reason="Test reason")
        
        assert hold_id in manager.active_holds
        hold = manager.active_holds[hold_id]
        assert hold.reason == "Test reason"

    def test_acquire_uses_default_timeout(self):
        """Test that acquire uses default timeout when none specified."""
        manager = HoldManager(default_timeout_seconds=120.0)
        
        hold_id = manager.acquire()
        hold = manager.get_hold(hold_id)
        
        assert hold.timeout_seconds == 120.0

    def test_acquire_uses_custom_timeout(self):
        """Test that acquire uses custom timeout when specified."""
        manager = HoldManager(default_timeout_seconds=120.0)
        
        hold_id = manager.acquire(timeout_seconds=60.0)
        hold = manager.get_hold(hold_id)
        
        assert hold.timeout_seconds == 60.0

    def test_acquire_no_timeout_when_disabled(self):
        """Test that acquire can create hold without timeout."""
        manager = HoldManager(default_timeout_seconds=None)
        
        hold_id = manager.acquire()
        hold = manager.get_hold(hold_id)
        
        assert hold.timeout_seconds is None

    def test_release_removes_hold(self):
        """Test that release removes the hold."""
        manager = HoldManager()
        hold_id = manager.acquire()
        
        released = manager.release(hold_id)
        
        assert released is True
        assert hold_id not in manager.active_holds

    def test_release_returns_false_for_unknown_hold(self):
        """Test that release returns False for unknown hold ID."""
        manager = HoldManager()
        
        released = manager.release("nonexistent-hold-id")
        
        assert released is False

    def test_get_hold_returns_hold(self):
        """Test that get_hold returns the hold."""
        manager = HoldManager()
        hold_id = manager.acquire(reason="Test")
        
        hold = manager.get_hold(hold_id)
        
        assert hold is not None
        assert hold.hold_id == hold_id
        assert hold.reason == "Test"

    def test_get_hold_returns_none_for_unknown(self):
        """Test that get_hold returns None for unknown hold ID."""
        manager = HoldManager()
        
        hold = manager.get_hold("nonexistent")
        
        assert hold is None

    def test_list_holds_returns_all_active(self):
        """Test that list_holds returns all active holds."""
        manager = HoldManager()
        
        hold_id1 = manager.acquire(reason="Hold 1")
        hold_id2 = manager.acquire(reason="Hold 2")
        hold_id3 = manager.acquire(reason="Hold 3")
        
        holds = manager.list_holds()
        
        assert len(holds) == 3
        hold_ids = [h.hold_id for h in holds]
        assert hold_id1 in hold_ids
        assert hold_id2 in hold_ids
        assert hold_id3 in hold_ids

    def test_has_active_holds_returns_false_when_empty(self):
        """Test that has_active_holds returns False when no holds."""
        manager = HoldManager()
        
        assert manager.has_active_holds() is False

    def test_has_active_holds_returns_true_when_holds_exist(self):
        """Test that has_active_holds returns True when holds exist."""
        manager = HoldManager()
        manager.acquire()
        
        assert manager.has_active_holds() is True

    def test_active_hold_count_returns_correct_count(self):
        """Test that active_hold_count returns correct count."""
        manager = HoldManager()
        
        assert manager.active_hold_count() == 0
        
        manager.acquire()
        assert manager.active_hold_count() == 1
        
        manager.acquire()
        assert manager.active_hold_count() == 2

    def test_clear_all_removes_all_holds(self):
        """Test that clear_all removes all holds."""
        manager = HoldManager()
        manager.acquire()
        manager.acquire()
        manager.acquire()
        
        count = manager.clear_all()
        
        assert count == 3
        assert manager.active_hold_count() == 0

    def test_expired_holds_are_cleaned_up(self):
        """Test that expired holds are automatically cleaned up."""
        manager = HoldManager()
        
        # Create an expired hold by manipulating acquired_at
        hold = Hold(
            timeout_seconds=0.001,  # Very short timeout
            acquired_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        manager.active_holds[hold.hold_id] = hold
        
        # Should be cleaned up on next check
        assert manager.has_active_holds() is False
        assert manager.active_hold_count() == 0


class TestHoldError:
    """Tests for the HoldError exception."""

    def test_hold_error_instantiation(self):
        """Test that HoldError can be instantiated."""
        holds = [Hold(reason="Test hold")]
        error = HoldError(holds)
        
        assert error.active_holds == holds
        assert "1 active hold" in str(error)

    def test_hold_error_message_with_reasons(self):
        """Test that HoldError message includes reasons."""
        holds = [
            Hold(reason="Generating response"),
            Hold(reason="Processing email"),
        ]
        error = HoldError(holds)
        
        message = str(error)
        assert "Generating response" in message
        assert "Processing email" in message

    def test_hold_error_custom_message(self):
        """Test that HoldError accepts custom message."""
        holds = [Hold()]
        error = HoldError(holds, message="Custom error message")
        
        assert str(error) == "Custom error message"

    def test_hold_error_multiple_holds(self):
        """Test that HoldError handles multiple holds."""
        holds = [Hold() for _ in range(5)]
        error = HoldError(holds)
        
        assert "5 active hold" in str(error)
