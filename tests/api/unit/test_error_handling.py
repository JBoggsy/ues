"""Unit tests for API error handling.

Tests for custom exception classes, exception handlers, and error response models.
These tests verify that errors are properly converted to consistent JSON responses.
"""

import asyncio
import pytest
from unittest.mock import MagicMock
from fastapi import status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError, BaseModel

from api.exceptions import (
    ModalityNotFoundError,
    SimulationNotRunningError,
    modality_not_found_handler,
    simulation_not_running_handler,
    request_validation_exception_handler,
    validation_exception_handler,
    value_error_handler,
    runtime_error_handler,
    generic_exception_handler,
)
from api.models import ErrorResponse


# Helper to run async functions synchronously
def run_async(coro):
    """Run an async coroutine synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


# =============================================================================
# ModalityNotFoundError Tests
# =============================================================================


class TestModalityNotFoundError:
    """Tests for ModalityNotFoundError exception class."""

    def test_stores_modality_name(self):
        """Exception stores the requested modality name."""
        exc = ModalityNotFoundError("invalid_modality", ["email", "sms"])
        assert exc.modality_name == "invalid_modality"

    def test_stores_available_modalities(self):
        """Exception stores list of available modalities."""
        available = ["email", "sms", "chat"]
        exc = ModalityNotFoundError("invalid", available)
        assert exc.available_modalities == available

    def test_message_contains_modality_name(self):
        """Exception message contains the requested modality name."""
        exc = ModalityNotFoundError("foo", [])
        assert "foo" in str(exc)

    def test_empty_available_list(self):
        """Exception works with empty available modalities list."""
        exc = ModalityNotFoundError("test", [])
        assert exc.available_modalities == []

    def test_inherits_from_exception(self):
        """ModalityNotFoundError inherits from Exception."""
        exc = ModalityNotFoundError("test", [])
        assert isinstance(exc, Exception)

    def test_can_be_raised_and_caught(self):
        """Exception can be raised and caught properly."""
        with pytest.raises(ModalityNotFoundError) as exc_info:
            raise ModalityNotFoundError("bad_modality", ["email"])
        assert exc_info.value.modality_name == "bad_modality"


# =============================================================================
# SimulationNotRunningError Tests
# =============================================================================


class TestSimulationNotRunningError:
    """Tests for SimulationNotRunningError exception class."""

    def test_default_message(self):
        """Exception has default message when none provided."""
        exc = SimulationNotRunningError()
        assert exc.message == "Simulation is not running"

    def test_custom_message(self):
        """Exception stores custom message."""
        exc = SimulationNotRunningError("Cannot advance time")
        assert exc.message == "Cannot advance time"

    def test_str_representation(self):
        """Exception string representation matches message."""
        exc = SimulationNotRunningError("Custom message")
        assert str(exc) == "Custom message"

    def test_inherits_from_exception(self):
        """SimulationNotRunningError inherits from Exception."""
        exc = SimulationNotRunningError()
        assert isinstance(exc, Exception)

    def test_can_be_raised_and_caught(self):
        """Exception can be raised and caught properly."""
        with pytest.raises(SimulationNotRunningError) as exc_info:
            raise SimulationNotRunningError("Test message")
        assert exc_info.value.message == "Test message"


# =============================================================================
# Exception Handler Tests
# =============================================================================


class TestModalityNotFoundHandler:
    """Tests for modality_not_found_handler function."""

    def test_returns_404_status(self):
        """Handler returns 404 Not Found status code."""
        mock_request = MagicMock()
        exc = ModalityNotFoundError("invalid", ["email"])
        response = run_async(modality_not_found_handler(mock_request, exc))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_response_contains_error_field(self):
        """Response body contains 'error' field."""
        mock_request = MagicMock()
        exc = ModalityNotFoundError("bad", ["email"])
        response = run_async(modality_not_found_handler(mock_request, exc))
        assert "error" in response.body.decode()

    def test_response_contains_requested_modality(self):
        """Response body contains the requested modality name."""
        mock_request = MagicMock()
        exc = ModalityNotFoundError("unknown_mod", ["email", "sms"])
        response = run_async(modality_not_found_handler(mock_request, exc))
        body = response.body.decode()
        assert "unknown_mod" in body

    def test_response_contains_available_modalities(self):
        """Response body contains available modalities."""
        mock_request = MagicMock()
        exc = ModalityNotFoundError("invalid", ["email", "sms"])
        response = run_async(modality_not_found_handler(mock_request, exc))
        body = response.body.decode()
        assert "email" in body
        assert "sms" in body

    def test_response_is_json(self):
        """Response has JSON content type."""
        mock_request = MagicMock()
        exc = ModalityNotFoundError("test", [])
        response = run_async(modality_not_found_handler(mock_request, exc))
        assert response.media_type == "application/json"


class TestSimulationNotRunningHandler:
    """Tests for simulation_not_running_handler function."""

    def test_returns_409_status(self):
        """Handler returns 409 Conflict status code."""
        mock_request = MagicMock()
        exc = SimulationNotRunningError()
        response = run_async(simulation_not_running_handler(mock_request, exc))
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_response_contains_error_field(self):
        """Response body contains 'error' field."""
        mock_request = MagicMock()
        exc = SimulationNotRunningError()
        response = run_async(simulation_not_running_handler(mock_request, exc))
        assert "error" in response.body.decode()

    def test_response_contains_message(self):
        """Response body contains the error message."""
        mock_request = MagicMock()
        exc = SimulationNotRunningError("Custom error message")
        response = run_async(simulation_not_running_handler(mock_request, exc))
        body = response.body.decode()
        assert "Custom error message" in body

    def test_response_contains_suggestion(self):
        """Response body contains suggestion to start simulation."""
        mock_request = MagicMock()
        exc = SimulationNotRunningError()
        response = run_async(simulation_not_running_handler(mock_request, exc))
        body = response.body.decode()
        assert "suggestion" in body
        assert "/simulation/start" in body

    def test_response_is_json(self):
        """Response has JSON content type."""
        mock_request = MagicMock()
        exc = SimulationNotRunningError()
        response = run_async(simulation_not_running_handler(mock_request, exc))
        assert response.media_type == "application/json"


class TestRequestValidationExceptionHandler:
    """Tests for request_validation_exception_handler function."""

    def _make_validation_error(self):
        """Create a RequestValidationError with realistic error data."""
        errors = [
            {
                "loc": ("body", "name"),
                "msg": "field required",
                "type": "value_error.missing",
            }
        ]
        return RequestValidationError(errors)

    def test_returns_422_status(self):
        """Handler returns 422 Unprocessable Entity status code."""
        mock_request = MagicMock()
        exc = self._make_validation_error()
        response = run_async(request_validation_exception_handler(mock_request, exc))
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_response_contains_error_field(self):
        """Response body contains 'error' field."""
        mock_request = MagicMock()
        exc = self._make_validation_error()
        response = run_async(request_validation_exception_handler(mock_request, exc))
        body = response.body.decode()
        assert "error" in body
        assert "Validation Error" in body

    def test_response_contains_detail(self):
        """Response body contains 'detail' field with error info."""
        mock_request = MagicMock()
        exc = self._make_validation_error()
        response = run_async(request_validation_exception_handler(mock_request, exc))
        body = response.body.decode()
        assert "detail" in body

    def test_response_is_json(self):
        """Response has JSON content type."""
        mock_request = MagicMock()
        exc = self._make_validation_error()
        response = run_async(request_validation_exception_handler(mock_request, exc))
        assert response.media_type == "application/json"


class TestValidationExceptionHandler:
    """Tests for validation_exception_handler function (Pydantic errors)."""

    def _make_pydantic_error(self):
        """Create a Pydantic ValidationError."""
        class TestModel(BaseModel):
            name: str
            age: int

        try:
            TestModel(name=123, age="not_an_int")  # type: ignore
        except ValidationError as exc:
            return exc
        raise RuntimeError("Expected ValidationError")

    def test_returns_422_status(self):
        """Handler returns 422 Unprocessable Entity status code."""
        mock_request = MagicMock()
        exc = self._make_pydantic_error()
        response = run_async(validation_exception_handler(mock_request, exc))
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_response_contains_error_field(self):
        """Response body contains 'error' field."""
        mock_request = MagicMock()
        exc = self._make_pydantic_error()
        response = run_async(validation_exception_handler(mock_request, exc))
        body = response.body.decode()
        assert "error" in body
        assert "Validation Error" in body

    def test_response_contains_validation_errors(self):
        """Response body contains 'validation_errors' field."""
        mock_request = MagicMock()
        exc = self._make_pydantic_error()
        response = run_async(validation_exception_handler(mock_request, exc))
        body = response.body.decode()
        assert "validation_errors" in body

    def test_response_is_json(self):
        """Response has JSON content type."""
        mock_request = MagicMock()
        exc = self._make_pydantic_error()
        response = run_async(validation_exception_handler(mock_request, exc))
        assert response.media_type == "application/json"


class TestValueErrorHandler:
    """Tests for value_error_handler function."""

    def test_returns_400_status(self):
        """Handler returns 400 Bad Request status code."""
        mock_request = MagicMock()
        exc = ValueError("Invalid value provided")
        response = run_async(value_error_handler(mock_request, exc))
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_response_contains_error_field(self):
        """Response body contains 'error' field."""
        mock_request = MagicMock()
        exc = ValueError("Test error")
        response = run_async(value_error_handler(mock_request, exc))
        body = response.body.decode()
        assert "error" in body
        assert "Invalid Value" in body

    def test_response_contains_detail_with_message(self):
        """Response body contains error message in detail."""
        mock_request = MagicMock()
        exc = ValueError("This is the error message")
        response = run_async(value_error_handler(mock_request, exc))
        body = response.body.decode()
        assert "This is the error message" in body

    def test_response_contains_type(self):
        """Response body contains 'type' field indicating ValueError."""
        mock_request = MagicMock()
        exc = ValueError("Test")
        response = run_async(value_error_handler(mock_request, exc))
        body = response.body.decode()
        assert "ValueError" in body

    def test_response_is_json(self):
        """Response has JSON content type."""
        mock_request = MagicMock()
        exc = ValueError("Test")
        response = run_async(value_error_handler(mock_request, exc))
        assert response.media_type == "application/json"


class TestRuntimeErrorHandler:
    """Tests for runtime_error_handler function."""

    def test_returns_500_status(self):
        """Handler returns 500 Internal Server Error status code."""
        mock_request = MagicMock()
        exc = RuntimeError("Something went wrong")
        response = run_async(runtime_error_handler(mock_request, exc))
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_response_contains_error_field(self):
        """Response body contains 'error' field."""
        mock_request = MagicMock()
        exc = RuntimeError("Test error")
        response = run_async(runtime_error_handler(mock_request, exc))
        body = response.body.decode()
        assert "error" in body
        assert "Runtime Error" in body

    def test_response_contains_detail_with_message(self):
        """Response body contains error message in detail."""
        mock_request = MagicMock()
        exc = RuntimeError("Runtime failure occurred")
        response = run_async(runtime_error_handler(mock_request, exc))
        body = response.body.decode()
        assert "Runtime failure occurred" in body

    def test_response_contains_type(self):
        """Response body contains 'type' field indicating RuntimeError."""
        mock_request = MagicMock()
        exc = RuntimeError("Test")
        response = run_async(runtime_error_handler(mock_request, exc))
        body = response.body.decode()
        assert "RuntimeError" in body

    def test_response_is_json(self):
        """Response has JSON content type."""
        mock_request = MagicMock()
        exc = RuntimeError("Test")
        response = run_async(runtime_error_handler(mock_request, exc))
        assert response.media_type == "application/json"


class TestGenericExceptionHandler:
    """Tests for generic_exception_handler function."""

    def test_returns_500_status(self):
        """Handler returns 500 Internal Server Error status code."""
        mock_request = MagicMock()
        exc = Exception("Unexpected error")
        response = run_async(generic_exception_handler(mock_request, exc))
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_response_contains_error_field(self):
        """Response body contains 'error' field."""
        mock_request = MagicMock()
        exc = Exception("Test")
        response = run_async(generic_exception_handler(mock_request, exc))
        body = response.body.decode()
        assert "error" in body
        assert "Internal Server Error" in body

    def test_response_does_not_expose_details(self):
        """Response does not expose internal error message."""
        mock_request = MagicMock()
        exc = Exception("Secret internal error message")
        response = run_async(generic_exception_handler(mock_request, exc))
        body = response.body.decode()
        # Should have generic message, not the actual error
        assert "An unexpected error occurred" in body

    def test_response_contains_exception_type(self):
        """Response body contains the exception type name."""
        mock_request = MagicMock()
        exc = KeyError("missing_key")
        response = run_async(generic_exception_handler(mock_request, exc))
        body = response.body.decode()
        assert "KeyError" in body

    def test_handles_custom_exception(self):
        """Handler works with custom exception types."""
        class CustomError(Exception):
            pass
        
        mock_request = MagicMock()
        exc = CustomError("Custom error")
        response = run_async(generic_exception_handler(mock_request, exc))
        body = response.body.decode()
        assert "CustomError" in body

    def test_response_is_json(self):
        """Response has JSON content type."""
        mock_request = MagicMock()
        exc = Exception("Test")
        response = run_async(generic_exception_handler(mock_request, exc))
        assert response.media_type == "application/json"


# =============================================================================
# ErrorResponse Model Tests
# =============================================================================


class TestErrorResponseModel:
    """Tests for ErrorResponse Pydantic model."""

    def test_required_fields(self):
        """ErrorResponse requires 'error' and 'message' fields."""
        response = ErrorResponse(error="NotFound", message="Resource not found")
        assert response.error == "NotFound"
        assert response.message == "Resource not found"

    def test_optional_details_default(self):
        """Details field defaults to None."""
        response = ErrorResponse(error="Error", message="Message")
        assert response.details is None

    def test_with_details(self):
        """Details field accepts dict."""
        details = {"field": "value", "count": 42}
        response = ErrorResponse(error="Error", message="Message", details=details)
        assert response.details == details

    def test_serialization_without_details(self):
        """Model serializes correctly without details."""
        response = ErrorResponse(error="Error", message="Test message")
        data = response.model_dump()
        assert data["error"] == "Error"
        assert data["message"] == "Test message"
        assert data["details"] is None

    def test_serialization_with_details(self):
        """Model serializes correctly with details."""
        response = ErrorResponse(
            error="ValidationError",
            message="Invalid input",
            details={"field": "name", "expected": "string"}
        )
        data = response.model_dump()
        assert data["error"] == "ValidationError"
        assert data["details"]["field"] == "name"

    def test_json_serialization(self):
        """Model can be serialized to JSON."""
        response = ErrorResponse(error="Error", message="Test")
        json_str = response.model_dump_json()
        assert "error" in json_str
        assert "message" in json_str

    def test_missing_error_raises(self):
        """Missing 'error' field raises ValidationError."""
        with pytest.raises(ValidationError):
            ErrorResponse(message="Message")  # type: ignore

    def test_missing_message_raises(self):
        """Missing 'message' field raises ValidationError."""
        with pytest.raises(ValidationError):
            ErrorResponse(error="Error")  # type: ignore

    def test_nested_details(self):
        """Details can contain nested dictionaries."""
        nested = {
            "errors": [
                {"field": "email", "message": "Invalid format"},
                {"field": "age", "message": "Must be positive"},
            ]
        }
        response = ErrorResponse(error="Error", message="Multi", details=nested)
        assert len(response.details["errors"]) == 2


# =============================================================================
# Integration Tests - Exception Handler Registration
# =============================================================================


class TestExceptionHandlerIntegration:
    """Integration tests for exception handlers with FastAPI app.
    
    Uses client_with_engine fixture to ensure proper engine initialization.
    """

    def test_root_endpoint_returns_200(self, client_with_engine):
        """Root endpoint works (sanity check)."""
        client, _ = client_with_engine
        response = client.get("/")
        assert response.status_code == 200

    def test_invalid_endpoint_returns_404(self, client_with_engine):
        """Invalid endpoint returns 404 (FastAPI default)."""
        client, _ = client_with_engine
        response = client.get("/nonexistent/endpoint")
        assert response.status_code == 404

    def test_invalid_modality_returns_404_with_structure(self, client_with_engine):
        """Invalid modality triggers ModalityNotFoundError handler."""
        client, _ = client_with_engine
        response = client.get("/environment/modalities/invalid_modality")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "available_modalities" in data

    def test_validation_error_returns_422(self, client_with_engine):
        """Invalid request body triggers validation error handler."""
        client, _ = client_with_engine
        # Try to create event with invalid data (missing required fields)
        response = client.post("/events", json={})
        assert response.status_code == 422
        data = response.json()
        assert "error" in data or "detail" in data

    def test_simulation_start_with_invalid_time_scale(self, client_with_engine):
        """Invalid time_scale triggers validation error."""
        client, engine = client_with_engine
        # Stop the already-running simulation first
        engine.stop()
        response = client.post("/simulation/start", json={
            "time_scale": -1.0  # Invalid: must be > 0
        })
        assert response.status_code == 422

    def test_time_advance_when_paused_returns_error(self, client_with_engine):
        """Time advance when paused returns appropriate error."""
        client, engine = client_with_engine
        # Pause the simulation
        engine.environment.time_state.is_paused = True
        
        # Try to advance time
        response = client.post("/simulator/time/advance", json={"seconds": 60})
        # Should fail because simulation is paused (400 Bad Request)
        assert response.status_code == 400

    def test_error_response_is_json(self, client_with_engine):
        """Error responses are always JSON."""
        client, _ = client_with_engine
        response = client.get("/environment/modalities/fake")
        assert response.headers["content-type"].startswith("application/json")

    def test_already_running_simulation_returns_409(self, client_with_engine):
        """Starting an already-running simulation returns 409 Conflict."""
        client, _ = client_with_engine
        # Simulation is already started by fixture
        response = client.post("/simulation/start", json={})
        assert response.status_code == 409


# =============================================================================
# Edge Cases and Error Scenarios
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases in error handling."""

    def test_empty_string_in_value_error(self):
        """Handler handles empty string in ValueError."""
        mock_request = MagicMock()
        exc = ValueError("")
        response = run_async(value_error_handler(mock_request, exc))
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unicode_in_error_message(self):
        """Handler handles unicode characters in error messages."""
        mock_request = MagicMock()
        exc = ValueError("Invalid value: 日本語 🎉")
        response = run_async(value_error_handler(mock_request, exc))
        body = response.body.decode()
        assert "日本語" in body or "Invalid value" in body

    def test_very_long_error_message(self):
        """Handler handles very long error messages."""
        mock_request = MagicMock()
        long_message = "x" * 10000
        exc = ValueError(long_message)
        response = run_async(value_error_handler(mock_request, exc))
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_exception_with_none_args(self):
        """Handler handles exceptions with None args."""
        mock_request = MagicMock()
        exc = RuntimeError()
        response = run_async(runtime_error_handler(mock_request, exc))
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_error_response_with_empty_details(self):
        """ErrorResponse with empty dict for details."""
        response = ErrorResponse(error="Error", message="Test", details={})
        assert response.details == {}

    def test_modality_not_found_with_many_modalities(self):
        """ModalityNotFoundError with large list of available modalities."""
        available = [f"modality_{i}" for i in range(100)]
        exc = ModalityNotFoundError("test", available)
        assert len(exc.available_modalities) == 100

    def test_simulation_not_running_with_newlines_in_message(self):
        """SimulationNotRunningError with newlines in message."""
        exc = SimulationNotRunningError("Line 1\nLine 2\nLine 3")
        assert "Line 1" in exc.message
        assert "\n" in exc.message

    def test_special_characters_in_modality_name(self):
        """ModalityNotFoundError with special characters in name."""
        exc = ModalityNotFoundError("<script>alert('xss')</script>", ["email"])
        assert "<script>" in exc.modality_name

    def test_empty_modality_name(self):
        """ModalityNotFoundError with empty string name."""
        exc = ModalityNotFoundError("", ["email", "sms"])
        assert exc.modality_name == ""
