"""Integration tests for simulation hold endpoints.

Tests verify that the hold management endpoints correctly handle
acquiring, releasing, listing holds, and blocking time advancement.
"""

import pytest
from fastapi.testclient import TestClient

from ues.api.dependencies import get_simulation_engine
from ues.main import app


class TestPostSimulationHold:
    """Tests for POST /simulation/hold endpoint."""

    def test_acquire_hold_returns_success(self, client_with_engine):
        """Test that POST /simulation/hold returns a successful response."""
        client, engine = client_with_engine
        
        response = client.post("/simulation/hold", json={})
        
        assert response.status_code == 200
        data = response.json()
        assert "hold_id" in data
        assert data["hold_id"] is not None
        assert data["active_hold_count"] == 1

    def test_acquire_hold_with_reason(self, client_with_engine):
        """Test that POST /simulation/hold accepts reason parameter."""
        client, engine = client_with_engine
        
        response = client.post("/simulation/hold", json={
            "reason": "Generating LLM response",
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["reason"] == "Generating LLM response"

    def test_acquire_hold_with_timeout(self, client_with_engine):
        """Test that POST /simulation/hold accepts timeout_seconds parameter."""
        client, engine = client_with_engine
        
        response = client.post("/simulation/hold", json={
            "timeout_seconds": 60.0,
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["timeout_seconds"] == 60.0
        assert data["expires_at"] is not None

    def test_acquire_hold_with_agent_id(self, client_with_engine):
        """Test that POST /simulation/hold accepts agent_id parameter."""
        client, engine = client_with_engine
        
        response = client.post("/simulation/hold", json={
            "agent_id": "agent-123",
        })
        
        assert response.status_code == 200
        # agent_id is not returned in the response, but it's stored

    def test_acquire_multiple_holds(self, client_with_engine):
        """Test that multiple holds can be acquired."""
        client, engine = client_with_engine
        
        response1 = client.post("/simulation/hold", json={"reason": "Hold 1"})
        response2 = client.post("/simulation/hold", json={"reason": "Hold 2"})
        response3 = client.post("/simulation/hold", json={"reason": "Hold 3"})
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 200
        
        assert response1.json()["active_hold_count"] == 1
        assert response2.json()["active_hold_count"] == 2
        assert response3.json()["active_hold_count"] == 3

    def test_acquire_hold_includes_timestamps(self, client_with_engine):
        """Test that hold response includes acquired_at timestamp."""
        client, engine = client_with_engine
        
        response = client.post("/simulation/hold", json={})
        
        assert response.status_code == 200
        data = response.json()
        assert "acquired_at" in data
        assert data["acquired_at"] is not None


class TestPostSimulationRelease:
    """Tests for POST /simulation/release/{hold_id} endpoint."""

    def test_release_hold_returns_success(self, client_with_engine):
        """Test that releasing a hold returns success."""
        client, engine = client_with_engine
        
        # First acquire a hold
        acquire_response = client.post("/simulation/hold", json={})
        hold_id = acquire_response.json()["hold_id"]
        
        # Then release it
        response = client.post(f"/simulation/release/{hold_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["released"] is True
        assert data["hold_id"] == hold_id
        assert data["active_hold_count"] == 0

    def test_release_nonexistent_hold_returns_404(self, client_with_engine):
        """Test that releasing a nonexistent hold returns 404."""
        client, engine = client_with_engine
        
        response = client.post("/simulation/release/nonexistent-hold-id")
        
        assert response.status_code == 404

    def test_release_decrements_hold_count(self, client_with_engine):
        """Test that releasing a hold decrements the count."""
        client, engine = client_with_engine
        
        # Acquire multiple holds
        response1 = client.post("/simulation/hold", json={})
        response2 = client.post("/simulation/hold", json={})
        response3 = client.post("/simulation/hold", json={})
        
        hold_id = response2.json()["hold_id"]
        
        # Release one hold
        release_response = client.post(f"/simulation/release/{hold_id}")
        
        assert release_response.status_code == 200
        assert release_response.json()["active_hold_count"] == 2


class TestGetSimulationHolds:
    """Tests for GET /simulation/holds endpoint."""

    def test_list_holds_empty(self, client_with_engine):
        """Test that listing holds returns empty when no holds."""
        client, engine = client_with_engine
        
        response = client.get("/simulation/holds")
        
        assert response.status_code == 200
        data = response.json()
        assert data["holds"] == []
        assert data["active_count"] == 0

    def test_list_holds_returns_all(self, client_with_engine):
        """Test that listing holds returns all active holds."""
        client, engine = client_with_engine
        
        # Acquire some holds
        client.post("/simulation/hold", json={"reason": "Hold 1"})
        client.post("/simulation/hold", json={"reason": "Hold 2"})
        
        response = client.get("/simulation/holds")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["holds"]) == 2
        assert data["active_count"] == 2
        
        reasons = [h["reason"] for h in data["holds"]]
        assert "Hold 1" in reasons
        assert "Hold 2" in reasons

    def test_list_holds_includes_details(self, client_with_engine):
        """Test that hold details are included in response."""
        client, engine = client_with_engine
        
        client.post("/simulation/hold", json={
            "reason": "Test hold",
            "timeout_seconds": 120.0,
            "agent_id": "test-agent",
        })
        
        response = client.get("/simulation/holds")
        
        assert response.status_code == 200
        hold = response.json()["holds"][0]
        assert hold["reason"] == "Test hold"
        assert hold["timeout_seconds"] == 120.0
        assert hold["agent_id"] == "test-agent"
        assert "acquired_at" in hold


class TestHoldBlocksTimeAdvancement:
    """Tests that holds block time advancement operations."""

    def test_advance_time_blocked_by_hold(self, client_with_engine):
        """Test that advance_time returns 409 when hold is active."""
        client, engine = client_with_engine
        
        # Acquire a hold
        client.post("/simulation/hold", json={"reason": "Testing"})
        
        # Try to advance time
        response = client.post("/simulator/time/advance", json={"seconds": 10})
        
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data
        # Detail should contain hold information
        assert "active_holds" in data["detail"] or "blocked" in str(data["detail"]).lower()

    def test_set_time_blocked_by_hold(self, client_with_engine):
        """Test that set_time returns 409 when hold is active."""
        client, engine = client_with_engine
        
        # Acquire a hold
        client.post("/simulation/hold", json={})
        
        # Try to set time
        response = client.post("/simulator/time/set", json={
            "target_time": "2025-01-01T12:00:00+00:00",
        })
        
        assert response.status_code == 409

    def test_skip_to_next_blocked_by_hold(self, client_with_engine):
        """Test that skip-to-next returns 409 when hold is active."""
        client, engine = client_with_engine
        
        # Schedule an event so there's something to skip to
        client.post("/events", json={
            "modality": "email",
            "scheduled_time": "2099-01-01T00:00:01+00:00",
            "data": {
                "action": "receive",
                "message_id": "test@example.com",
                "subject": "Test",
                "from_address": "sender@example.com",
                "to_addresses": ["recipient@example.com"],
                "body": "Test body",
            },
        })
        
        # Acquire a hold
        client.post("/simulation/hold", json={})
        
        # Try to skip to next
        response = client.post("/simulator/time/skip-to-next")
        
        assert response.status_code == 409

    def test_advance_time_works_after_release(self, client_with_engine):
        """Test that advance_time works after hold is released."""
        client, engine = client_with_engine
        
        # Acquire a hold
        hold_response = client.post("/simulation/hold", json={})
        hold_id = hold_response.json()["hold_id"]
        
        # Release the hold
        client.post(f"/simulation/release/{hold_id}")
        
        # Now advance time should work
        response = client.post("/simulator/time/advance", json={"seconds": 10})
        
        assert response.status_code == 200

    def test_multiple_holds_all_must_be_released(self, client_with_engine):
        """Test that all holds must be released before time advancement."""
        client, engine = client_with_engine
        
        # Acquire multiple holds
        hold1_response = client.post("/simulation/hold", json={})
        hold2_response = client.post("/simulation/hold", json={})
        hold1_id = hold1_response.json()["hold_id"]
        hold2_id = hold2_response.json()["hold_id"]
        
        # Release only one hold
        client.post(f"/simulation/release/{hold1_id}")
        
        # Time advancement should still be blocked
        response = client.post("/simulator/time/advance", json={"seconds": 10})
        assert response.status_code == 409
        
        # Release the second hold
        client.post(f"/simulation/release/{hold2_id}")
        
        # Now it should work
        response = client.post("/simulator/time/advance", json={"seconds": 10})
        assert response.status_code == 200


class TestSimulationClearClearsHolds:
    """Tests that simulation clear clears all holds."""

    def test_clear_removes_all_holds(self, client_with_engine):
        """Test that /simulation/clear removes all active holds."""
        client, engine = client_with_engine
        
        # Acquire some holds
        client.post("/simulation/hold", json={})
        client.post("/simulation/hold", json={})
        
        # Verify holds exist
        holds_response = client.get("/simulation/holds")
        assert holds_response.json()["active_count"] == 2
        
        # Clear simulation
        client.post("/simulation/clear")
        
        # Verify holds are gone (simulation needs to be restarted after clear)
        client.post("/simulation/start", json={})
        holds_response = client.get("/simulation/holds")
        assert holds_response.json()["active_count"] == 0
