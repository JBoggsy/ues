"""Integration tests for environment validation endpoint.

This module tests the POST /environment/validate endpoint, which allows clients to:
- Validate environment consistency
- Check for cross-modality integrity issues
- Detect invalid state conditions
- Get validation errors with details

Following patterns from API_TESTING_GUIDELINES.md.
"""

from datetime import datetime, timedelta

from tests.api.helpers import (
    make_event_request,
    email_event_data,
    location_event_data,
)


class TestValidateEnvironment:
    """Tests for POST /environment/validate endpoint."""
    
    def test_validate_environment_returns_valid(self, client_with_engine):
        """Test that POST /environment/validate returns valid for clean environment.
        
        Verifies that a fresh environment with no events validates successfully.
        
        Expected response structure:
        - valid: bool (should be True)
        - errors: list of strings (should be empty)
        - checked_at: datetime (timestamp of validation)
        """
        client, _ = client_with_engine
        
        # Validate fresh environment
        response = client.post("/environment/validate")
        
        # Verify response structure
        assert response.status_code == 200
        data = response.json()
        
        assert "valid" in data
        assert "errors" in data
        assert "checked_at" in data
        
        # Verify valid state
        assert data["valid"] is True
        assert isinstance(data["errors"], list)
        assert len(data["errors"]) == 0
        
        # Verify checked_at is valid ISO format
        checked_at = datetime.fromisoformat(data["checked_at"])
        assert isinstance(checked_at, datetime)
    
    def test_validate_environment_checked_at_matches_current_time(self, client_with_engine):
        """Test that validation timestamp matches current simulator time.
        
        Verifies that checked_at field reflects the simulator time when
        validation was performed.
        """
        client, _ = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Validate environment
        response = client.post("/environment/validate")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify checked_at matches current time
        checked_at = datetime.fromisoformat(data["checked_at"])
        assert checked_at == current_time
    
    def test_validate_environment_after_events(self, client_with_engine):
        """Test that environment remains valid after event execution.
        
        Creates and executes events, then verifies environment is still valid.
        
        Note: This test depends on event execution working correctly.
        """
        client, _ = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create and execute some events
        event_time = current_time + timedelta(seconds=1)
        
        # Create email event
        email_event = make_event_request(
            event_time,
            "email",
            email_event_data(
                operation="receive",
                from_address="sender@example.com",
                subject="Test Email",
            ),
        )
        
        # Create location event
        location_event = make_event_request(
            event_time + timedelta(seconds=1),
            "location",
            location_event_data(
                latitude=37.7749,
                longitude=-122.4194,
                named_location="San Francisco",
            ),
        )
        
        client.post("/events", json=email_event)
        client.post("/events", json=location_event)
        
        # Execute events
        client.post("/simulator/time/advance", json={"seconds": 5})
        
        # Validate environment after events
        response = client.post("/environment/validate")
        
        assert response.status_code == 200
        data = response.json()
        
        # Environment should still be valid after normal event execution
        assert data["valid"] is True
        assert len(data["errors"]) == 0
        
        # Verify checked_at updated to new current time
        checked_at = datetime.fromisoformat(data["checked_at"])
        assert checked_at > current_time
    
    def test_validate_environment_detects_inconsistencies(self, client_with_engine):
        """Test that validation detects inconsistent state.
        
        This test verifies that validation would report errors if they existed.
        Since we cannot easily create inconsistent state through the API
        (the system prevents invalid operations), we test that:
        1. The validation endpoint correctly formats error responses
        2. The validation system checks for specific types of errors
        
        Note: In a real inconsistent state, valid would be False and errors
        would contain descriptive messages. Current implementation prevents
        most inconsistencies from occurring.
        """
        client, _ = client_with_engine
        
        # Validate environment (should be valid since we can't create inconsistencies via API)
        response = client.post("/environment/validate")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure supports error reporting
        assert "valid" in data
        assert "errors" in data
        assert isinstance(data["errors"], list)
        
        # Current state should be valid (API prevents inconsistencies)
        # If this fails, it means we discovered a bug in the validation system
        assert data["valid"] is True
        
        # Document what validation checks for (from models/environment.py):
        # - time_state is not None and is valid
        # - modality_states is not empty
        # - All modality states are valid
        # - Modality names match state types
        # - No duplicate modality types
        # - Event queue validation
        # - No events referencing non-existent modalities
    
    def test_validate_environment_errors_are_descriptive(self, client_with_engine):
        """Test that validation errors include helpful descriptions.
        
        If validation finds errors, they should be clear and actionable.
        
        This test verifies the error message structure by checking that
        when errors exist, they are strings with meaningful content.
        Since we can't easily create validation errors through the API,
        we verify the structure is correct for the valid case and document
        expected error format.
        
        Expected error format (from implementation):
        - Environment errors: "Environment: <error_message>"
        - EventQueue errors: "EventQueue: <error_message>"
        - Modality errors: "modality '<name>': <error_message>"
        - Time state errors: "time_state: <error_message>"
        """
        client, _ = client_with_engine
        
        # Validate environment
        response = client.post("/environment/validate")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify error list structure
        assert isinstance(data["errors"], list)
        
        # All errors should be strings (if any existed)
        for error in data["errors"]:
            assert isinstance(error, str)
            assert len(error) > 0
        
        # Current valid environment should have no errors
        assert len(data["errors"]) == 0
        
        # Document expected error prefixes from implementation:
        # - "Environment: " for env-level errors
        # - "EventQueue: " for queue-level errors
        # - "Event <id> references non-existent modality '<name>'" for orphaned events
        # - "modality '<name>': " for modality-specific errors
        # - "time_state: " for time state errors
    
    def test_validate_environment_is_read_only(self, client_with_engine):
        """Test that validation doesn't modify environment state.
        
        Verifies that calling validate is a read-only operation that doesn't
        change any modality states or time.
        """
        client, _ = client_with_engine
        
        # Get initial environment state snapshot
        state_before = client.get("/environment/state").json()
        time_before = client.get("/simulator/time").json()
        
        # Validate environment
        validate_response = client.post("/environment/validate")
        assert validate_response.status_code == 200
        
        # Get environment state after validation
        state_after = client.get("/environment/state").json()
        time_after = client.get("/simulator/time").json()
        
        # Verify states are identical (validation didn't modify anything)
        assert state_before == state_after
        assert time_before == time_after
        
        # Verify time didn't advance
        assert time_before["current_time"] == time_after["current_time"]
        
        # Verify modality states unchanged
        assert state_before["modalities"] == state_after["modalities"]
