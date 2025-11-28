"""Integration tests for POST /simulator/time/set-scale endpoint.

Tests verify that the time scale endpoint correctly modifies the rate at which
simulation time passes relative to real time (for auto-advance mode).
"""

from datetime import datetime

import pytest


class TestPostTimeSetScale:
    """Tests for POST /simulator/time/set-scale endpoint."""
    
    def test_set_scale_changes_time_scale(self, client_with_engine):
        """Test that POST /simulator/time/set-scale modifies time scale."""
        client, _ = client_with_engine
        
        # Set time scale to 2.0 (2x speed)
        response = client.post(
            "/simulator/time/set-scale",
            json={"scale": 2.0}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["time_scale"] == 2.0
        
        # Verify state reflects new scale
        state_response = client.get("/simulator/time")
        assert state_response.json()["time_scale"] == 2.0
    
    def test_set_scale_rejects_zero(self, client_with_engine):
        """Test that POST /simulator/time/set-scale rejects zero scale."""
        client, _ = client_with_engine
        
        # Try to set scale to 0.0
        response = client.post(
            "/simulator/time/set-scale",
            json={"scale": 0.0}
        )
        
        # Should reject with 422 validation error
        assert response.status_code == 422
    
    def test_set_scale_rejects_negative(self, client_with_engine):
        """Test that POST /simulator/time/set-scale rejects negative scale."""
        client, _ = client_with_engine
        
        # Try to set scale to negative value
        response = client.post(
            "/simulator/time/set-scale",
            json={"scale": -1.0}
        )
        
        # Should reject with 422 validation error
        assert response.status_code == 422
    
    def test_set_scale_accepts_fractional_values(self, client_with_engine):
        """Test that POST /simulator/time/set-scale accepts slow-motion values."""
        client, _ = client_with_engine
        
        # Set scale to 0.5 (half speed / slow motion)
        response = client.post(
            "/simulator/time/set-scale",
            json={"scale": 0.5}
        )
        
        # Should succeed
        assert response.status_code == 200
        assert response.json()["time_scale"] == 0.5
        
        # Verify state
        state_response = client.get("/simulator/time")
        assert state_response.json()["time_scale"] == 0.5
    
    def test_set_scale_with_very_large_values(self, client_with_engine):
        """Test that POST /simulator/time/set-scale accepts very large scale values."""
        client, _ = client_with_engine
        
        # Set scale to 1000.0 (1000x speed)
        response = client.post(
            "/simulator/time/set-scale",
            json={"scale": 1000.0}
        )
        
        # Should succeed
        assert response.status_code == 200
        assert response.json()["time_scale"] == 1000.0
    
    def test_set_scale_with_very_small_values(self, client_with_engine):
        """Test that POST /simulator/time/set-scale accepts very small positive values."""
        client, _ = client_with_engine
        
        # Set scale to 0.01 (1% speed / extreme slow motion)
        response = client.post(
            "/simulator/time/set-scale",
            json={"scale": 0.01}
        )
        
        # Should succeed
        assert response.status_code == 200
        assert response.json()["time_scale"] == 0.01
    
    def test_set_scale_persists_across_pause_resume(self, client_with_engine):
        """Test that POST /simulator/time/set-scale persists through pause/resume."""
        client, _ = client_with_engine
        
        # Set scale to 5.0
        response = client.post(
            "/simulator/time/set-scale",
            json={"scale": 5.0}
        )
        assert response.status_code == 200
        
        # Pause
        pause_response = client.post("/simulator/time/pause")
        assert pause_response.status_code == 200
        
        # Verify scale is still 5.0
        state_after_pause = client.get("/simulator/time")
        assert state_after_pause.json()["time_scale"] == 5.0
        
        # Resume
        resume_response = client.post("/simulator/time/resume")
        assert resume_response.status_code == 200
        
        # Verify scale is still 5.0
        state_after_resume = client.get("/simulator/time")
        assert state_after_resume.json()["time_scale"] == 5.0
    
    def test_set_scale_multiple_times(self, client_with_engine):
        """Test that POST /simulator/time/set-scale can be called multiple times."""
        client, _ = client_with_engine
        
        # Set to 2.0
        response1 = client.post("/simulator/time/set-scale", json={"scale": 2.0})
        assert response1.status_code == 200
        assert response1.json()["time_scale"] == 2.0
        
        # Set to 10.0
        response2 = client.post("/simulator/time/set-scale", json={"scale": 10.0})
        assert response2.status_code == 200
        assert response2.json()["time_scale"] == 10.0
        
        # Set to 0.5
        response3 = client.post("/simulator/time/set-scale", json={"scale": 0.5})
        assert response3.status_code == 200
        assert response3.json()["time_scale"] == 0.5
        
        # Verify final state
        state_response = client.get("/simulator/time")
        assert state_response.json()["time_scale"] == 0.5
    
    def test_set_scale_validates_missing_field(self, client_with_engine):
        """Test that POST /simulator/time/set-scale requires scale field."""
        client, _ = client_with_engine
        
        # Try request with missing scale field
        response = client.post("/simulator/time/set-scale", json={})
        
        # Should reject with validation error
        assert response.status_code == 422
        assert "scale" in response.json()["detail"][0]["loc"]
    
    def test_set_scale_validates_null_value(self, client_with_engine):
        """Test that POST /simulator/time/set-scale rejects null scale value."""
        client, _ = client_with_engine
        
        # Try request with null scale
        response = client.post(
            "/simulator/time/set-scale",
            json={"scale": None}
        )
        
        # Should reject with validation error
        assert response.status_code == 422
    
    def test_set_scale_to_one_returns_to_realtime(self, client_with_engine):
        """Test that setting scale to 1.0 returns to real-time mode."""
        client, _ = client_with_engine
        
        # Set to fast-forward
        client.post("/simulator/time/set-scale", json={"scale": 100.0})
        
        # Return to real-time
        response = client.post("/simulator/time/set-scale", json={"scale": 1.0})
        
        assert response.status_code == 200
        assert response.json()["time_scale"] == 1.0
        
        # Verify state
        state_response = client.get("/simulator/time")
        assert state_response.json()["time_scale"] == 1.0
