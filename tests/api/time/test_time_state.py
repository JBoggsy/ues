"""Integration tests for GET /simulator/time endpoint.

Tests verify that the time state endpoint correctly returns current simulation
time, time scale, pause state, and auto-advance settings.
"""

from datetime import datetime

import pytest


class TestGetTime:
    """Tests for GET /simulator/time endpoint."""
    
    def test_get_time_returns_current_state(self, client_with_engine):
        """Test that GET /simulator/time returns the current time state."""
        client, engine = client_with_engine
        
        # Get time via API
        response = client.get("/simulator/time")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Check all expected fields are present
        assert "current_time" in data
        assert "time_scale" in data
        assert "is_paused" in data
        assert "auto_advance" in data
        
        # Verify data matches engine state
        assert data["time_scale"] == 1.0
        assert data["is_paused"] is False
        assert data["auto_advance"] is False
        
        # Verify time is parseable and timezone-aware
        current_time = datetime.fromisoformat(data["current_time"])
        assert current_time.tzinfo is not None
    
    def test_get_time_reflects_engine_state(self, client_with_engine):
        """Test that GET /simulator/time reflects actual engine state changes."""
        client, engine = client_with_engine
        
        # Get initial time
        initial_response = client.get("/simulator/time")
        initial_data = initial_response.json()
        initial_time = datetime.fromisoformat(initial_data["current_time"])
        
        # Advance time via API
        advance_response = client.post(
            "/simulator/time/advance",
            json={"seconds": 3600}  # Advance 1 hour
        )
        assert advance_response.status_code == 200
        
        # Get time again
        updated_response = client.get("/simulator/time")
        updated_data = updated_response.json()
        updated_time = datetime.fromisoformat(updated_data["current_time"])
        
        # Verify time advanced by 1 hour
        time_diff = updated_time - initial_time
        assert abs(time_diff.total_seconds() - 3600) < 1  # Allow 1 second tolerance
    
    def test_get_time_when_paused(self, client_with_engine):
        """Test that GET /simulator/time correctly shows paused state."""
        client, engine = client_with_engine
        
        # Pause the simulation
        pause_response = client.post("/simulator/time/pause")
        assert pause_response.status_code == 200
        
        # Get time state
        response = client.get("/simulator/time")
        data = response.json()
        
        # Verify is_paused is True
        assert data["is_paused"] is True
    
    def test_get_time_with_modified_time_scale(self, client_with_engine):
        """Test that GET /simulator/time reflects time scale changes."""
        client, engine = client_with_engine
        
        # Set time scale to 2.0
        scale_response = client.post(
            "/simulator/time/set-scale",
            json={"scale": 2.0}
        )
        assert scale_response.status_code == 200
        
        # Get time state
        response = client.get("/simulator/time")
        data = response.json()
        
        # Verify time_scale is 2.0
        assert data["time_scale"] == 2.0
    
    def test_get_time_returns_consistent_format(self, client_with_engine):
        """Test that GET /simulator/time always returns ISO 8601 formatted times."""
        client, engine = client_with_engine
        
        # Get time multiple times
        for _ in range(3):
            response = client.get("/simulator/time")
            assert response.status_code == 200
            data = response.json()
            
            # Verify ISO 8601 format by parsing
            time_str = data["current_time"]
            parsed_time = datetime.fromisoformat(time_str)
            
            # Verify timezone awareness
            assert parsed_time.tzinfo is not None
            
            # Verify we can round-trip the format
            assert parsed_time.isoformat() == time_str or \
                   parsed_time.isoformat().replace('+00:00', 'Z') == time_str
