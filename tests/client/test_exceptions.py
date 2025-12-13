"""Unit tests for the UES client exception hierarchy.

This module tests the exception classes defined in client/exceptions.py.
The tests verify:

1. Exception hierarchy and inheritance relationships
2. Exception instantiation with required and optional attributes
3. String representations (__str__) for debugging/logging
4. Attribute accessibility after instantiation
5. Exception catching behavior (specific vs. broad catches)

The exception hierarchy being tested:
    UESClientError (base)
    ├── ConnectionError - Network/connection failures
    ├── TimeoutError - Request timeout
    └── APIError - Server returned an error response
        ├── ValidationError (HTTP 422)
        ├── NotFoundError (HTTP 404)
        ├── ConflictError (HTTP 409)
        └── ServerError (HTTP 5xx)
"""

import pytest

from client.exceptions import (
    UESClientError,
    ConnectionError,
    TimeoutError,
    APIError,
    ValidationError,
    NotFoundError,
    ConflictError,
    ServerError,
)


# =============================================================================
# UESClientError Tests (Base Exception)
# =============================================================================

class TestUESClientError:
    """Tests for the base UESClientError exception class.
    
    UESClientError is the root of the exception hierarchy. All other client
    exceptions inherit from it, allowing users to catch any client error
    with a single except clause.
    """
    
    def test_instantiation_with_message(self) -> None:
        """UESClientError can be instantiated with a message string.
        
        The message should be stored as an attribute and passed to the
        base Exception class.
        """
        error = UESClientError("Something went wrong")
        assert error.message == "Something went wrong"
    
    def test_str_returns_message(self) -> None:
        """String representation returns the message.
        
        This ensures the error is human-readable when printed or logged.
        """
        error = UESClientError("Test error message")
        assert str(error) == "Test error message"
    
    def test_inherits_from_exception(self) -> None:
        """UESClientError inherits from Python's built-in Exception.
        
        This ensures it can be caught with a bare `except Exception` clause
        and integrates properly with Python's exception handling.
        """
        error = UESClientError("Test")
        assert isinstance(error, Exception)
    
    def test_can_be_raised_and_caught(self) -> None:
        """UESClientError can be raised and caught like any exception."""
        with pytest.raises(UESClientError) as exc_info:
            raise UESClientError("Raised error")
        
        assert exc_info.value.message == "Raised error"


# =============================================================================
# ConnectionError Tests
# =============================================================================

class TestConnectionError:
    """Tests for the ConnectionError exception class.
    
    ConnectionError is raised when the client cannot establish a connection
    to the UES server. It includes optional attributes for the URL and the
    underlying cause of the failure.
    """
    
    def test_instantiation_with_message_only(self) -> None:
        """ConnectionError can be instantiated with just a message.
        
        URL and cause are optional attributes that default to None.
        """
        error = ConnectionError("Failed to connect")
        assert error.message == "Failed to connect"
        assert error.url is None
        assert error.cause is None
    
    def test_instantiation_with_all_attributes(self) -> None:
        """ConnectionError can include URL and underlying cause.
        
        This allows for more detailed error reporting when available.
        """
        cause = OSError("Network unreachable")
        error = ConnectionError(
            message="Connection failed",
            url="http://localhost:8000/api/test",
            cause=cause,
        )
        
        assert error.message == "Connection failed"
        assert error.url == "http://localhost:8000/api/test"
        assert error.cause is cause
    
    def test_str_without_url(self) -> None:
        """String representation without URL shows just the message."""
        error = ConnectionError("Failed to connect")
        assert str(error) == "Failed to connect"
    
    def test_str_with_url(self) -> None:
        """String representation with URL includes it in parentheses.
        
        This helps users identify which endpoint failed to connect.
        """
        error = ConnectionError(
            message="Connection refused",
            url="http://localhost:8000/api/time",
        )
        assert str(error) == "Connection refused (url: http://localhost:8000/api/time)"
    
    def test_inherits_from_ues_client_error(self) -> None:
        """ConnectionError inherits from UESClientError.
        
        This allows catching all client errors with a single except clause.
        """
        error = ConnectionError("Test")
        assert isinstance(error, UESClientError)
        assert isinstance(error, Exception)
    
    def test_can_catch_as_base_type(self) -> None:
        """ConnectionError can be caught as UESClientError.
        
        This demonstrates the hierarchical exception catching pattern.
        """
        with pytest.raises(UESClientError):
            raise ConnectionError("Test")


# =============================================================================
# TimeoutError Tests
# =============================================================================

class TestTimeoutError:
    """Tests for the TimeoutError exception class.
    
    TimeoutError is raised when a request takes longer than the configured
    timeout duration. It includes optional attributes for the timeout value
    and the URL that timed out.
    """
    
    def test_instantiation_with_message_only(self) -> None:
        """TimeoutError can be instantiated with just a message.
        
        Timeout value and URL are optional and default to None.
        """
        error = TimeoutError("Request timed out")
        assert error.message == "Request timed out"
        assert error.timeout is None
        assert error.url is None
    
    def test_instantiation_with_all_attributes(self) -> None:
        """TimeoutError can include timeout duration and URL."""
        error = TimeoutError(
            message="Request timed out",
            timeout=30.0,
            url="http://localhost:8000/api/events",
        )
        
        assert error.message == "Request timed out"
        assert error.timeout == 30.0
        assert error.url == "http://localhost:8000/api/events"
    
    def test_str_without_extras(self) -> None:
        """String representation without extras shows just the message."""
        error = TimeoutError("Timed out")
        assert str(error) == "Timed out"
    
    def test_str_with_timeout_only(self) -> None:
        """String representation with timeout includes it."""
        error = TimeoutError("Request timed out", timeout=30.0)
        assert str(error) == "Request timed out (timeout: 30.0s)"
    
    def test_str_with_url_only(self) -> None:
        """String representation with URL includes it."""
        error = TimeoutError("Request timed out", url="http://localhost:8000")
        assert str(error) == "Request timed out (url: http://localhost:8000)"
    
    def test_str_with_timeout_and_url(self) -> None:
        """String representation with both timeout and URL includes both."""
        error = TimeoutError(
            "Request timed out",
            timeout=30.0,
            url="http://localhost:8000/api/time",
        )
        assert str(error) == "Request timed out (timeout: 30.0s, url: http://localhost:8000/api/time)"
    
    def test_inherits_from_ues_client_error(self) -> None:
        """TimeoutError inherits from UESClientError."""
        error = TimeoutError("Test")
        assert isinstance(error, UESClientError)


# =============================================================================
# APIError Tests (Base API Exception)
# =============================================================================

class TestAPIError:
    """Tests for the APIError exception class.
    
    APIError is the base class for all server-returned error responses.
    It includes the HTTP status code, optional error type, details, and
    the raw response body for debugging.
    """
    
    def test_instantiation_with_required_attributes(self) -> None:
        """APIError requires message and status_code."""
        error = APIError(
            message="Server error occurred",
            status_code=500,
        )
        
        assert error.message == "Server error occurred"
        assert error.status_code == 500
        assert error.error_type is None
        assert error.details is None
        assert error.response_body is None
    
    def test_instantiation_with_all_attributes(self) -> None:
        """APIError can include error_type, details, and response_body."""
        details = {"field": "email", "reason": "invalid format"}
        response_body = {"error": "validation_failed", "details": details}
        
        error = APIError(
            message="Validation failed",
            status_code=422,
            error_type="validation_error",
            details=details,
            response_body=response_body,
        )
        
        assert error.message == "Validation failed"
        assert error.status_code == 422
        assert error.error_type == "validation_error"
        assert error.details == details
        assert error.response_body == response_body
    
    def test_str_without_error_type(self) -> None:
        """String representation without error_type shows status and message."""
        error = APIError("Not found", status_code=404)
        assert str(error) == "[HTTP 404] Not found"
    
    def test_str_with_error_type(self) -> None:
        """String representation with error_type includes it in brackets."""
        error = APIError(
            message="Resource not found",
            status_code=404,
            error_type="not_found",
        )
        assert str(error) == "[HTTP 404] [not_found] Resource not found"
    
    def test_inherits_from_ues_client_error(self) -> None:
        """APIError inherits from UESClientError."""
        error = APIError("Test", status_code=500)
        assert isinstance(error, UESClientError)
    
    def test_details_can_be_accessed_for_field_errors(self) -> None:
        """Details dict can contain field-level error information.
        
        This is useful for displaying validation errors to users.
        """
        details = {
            "to_addresses": ["At least one recipient required"],
            "subject": ["Subject cannot be empty"],
        }
        error = APIError(
            message="Validation failed",
            status_code=422,
            details=details,
        )
        
        assert "to_addresses" in error.details
        assert error.details["subject"] == ["Subject cannot be empty"]


# =============================================================================
# ValidationError Tests
# =============================================================================

class TestValidationError:
    """Tests for the ValidationError exception class.
    
    ValidationError is raised when the server rejects a request due to
    invalid data (HTTP 422). It has a fixed status_code and error_type,
    and typically contains field-level validation errors in details.
    """
    
    def test_instantiation_with_message_only(self) -> None:
        """ValidationError can be instantiated with just a message.
        
        Status code is automatically set to 422.
        """
        error = ValidationError("Invalid request data")
        
        assert error.message == "Invalid request data"
        assert error.status_code == 422
        assert error.error_type == "validation_error"
        assert error.details is None
    
    def test_instantiation_with_details(self) -> None:
        """ValidationError can include field-level error details."""
        details = {
            "to_addresses": ["At least one recipient is required"],
            "body_text": ["Message body cannot be empty"],
        }
        error = ValidationError(
            message="Request validation failed",
            details=details,
        )
        
        assert error.status_code == 422
        assert error.details == details
    
    def test_instantiation_with_response_body(self) -> None:
        """ValidationError can include the raw response body for debugging."""
        response_body = {"detail": [{"loc": ["body", "email"], "msg": "invalid"}]}
        error = ValidationError(
            message="Validation failed",
            response_body=response_body,
        )
        
        assert error.response_body == response_body
    
    def test_inherits_from_api_error(self) -> None:
        """ValidationError inherits from APIError.
        
        This allows catching it as either ValidationError or APIError.
        """
        error = ValidationError("Test")
        assert isinstance(error, APIError)
        assert isinstance(error, UESClientError)
    
    def test_status_code_is_always_422(self) -> None:
        """ValidationError always has status_code 422.
        
        This is the HTTP standard status code for validation errors.
        """
        error = ValidationError("Test")
        assert error.status_code == 422
    
    def test_error_type_is_always_validation_error(self) -> None:
        """ValidationError always has error_type 'validation_error'."""
        error = ValidationError("Test")
        assert error.error_type == "validation_error"
    
    def test_str_format(self) -> None:
        """String representation follows APIError format."""
        error = ValidationError("Invalid email format")
        assert str(error) == "[HTTP 422] [validation_error] Invalid email format"


# =============================================================================
# NotFoundError Tests
# =============================================================================

class TestNotFoundError:
    """Tests for the NotFoundError exception class.
    
    NotFoundError is raised when a requested resource doesn't exist (HTTP 404).
    It includes optional attributes for the resource type and ID that weren't
    found, making error messages more informative.
    """
    
    def test_instantiation_with_message_only(self) -> None:
        """NotFoundError can be instantiated with just a message."""
        error = NotFoundError("Resource not found")
        
        assert error.message == "Resource not found"
        assert error.status_code == 404
        assert error.error_type == "not_found"
        assert error.resource_type is None
        assert error.resource_id is None
    
    def test_instantiation_with_resource_info(self) -> None:
        """NotFoundError can include resource type and ID.
        
        This helps identify exactly which resource was not found.
        """
        error = NotFoundError(
            message="Event not found",
            resource_type="event",
            resource_id="evt_123456",
        )
        
        assert error.resource_type == "event"
        assert error.resource_id == "evt_123456"
    
    def test_instantiation_with_all_attributes(self) -> None:
        """NotFoundError can include all optional attributes."""
        error = NotFoundError(
            message="Modality not found",
            resource_type="modality",
            resource_id="unknown_modality",
            details={"available": ["email", "sms", "calendar"]},
            response_body={"error": "not_found"},
        )
        
        assert error.resource_type == "modality"
        assert error.resource_id == "unknown_modality"
        assert error.details == {"available": ["email", "sms", "calendar"]}
    
    def test_inherits_from_api_error(self) -> None:
        """NotFoundError inherits from APIError."""
        error = NotFoundError("Test")
        assert isinstance(error, APIError)
        assert isinstance(error, UESClientError)
    
    def test_status_code_is_always_404(self) -> None:
        """NotFoundError always has status_code 404."""
        error = NotFoundError("Test")
        assert error.status_code == 404
    
    def test_str_format(self) -> None:
        """String representation follows APIError format."""
        error = NotFoundError("Event evt_123 not found")
        assert str(error) == "[HTTP 404] [not_found] Event evt_123 not found"


# =============================================================================
# ConflictError Tests
# =============================================================================

class TestConflictError:
    """Tests for the ConflictError exception class.
    
    ConflictError is raised when an operation cannot be performed due to
    the current system state (HTTP 409). Common scenarios:
    - Starting a simulation that's already running
    - Advancing time when simulation is stopped
    - Undoing when there's nothing to undo
    """
    
    def test_instantiation_with_message_only(self) -> None:
        """ConflictError can be instantiated with just a message."""
        error = ConflictError("Simulation already running")
        
        assert error.message == "Simulation already running"
        assert error.status_code == 409
        assert error.error_type == "conflict"
    
    def test_instantiation_with_details(self) -> None:
        """ConflictError can include details about the conflict."""
        error = ConflictError(
            message="Cannot advance time",
            details={"current_state": "stopped", "required_state": "running"},
        )
        
        assert error.details == {
            "current_state": "stopped",
            "required_state": "running",
        }
    
    def test_inherits_from_api_error(self) -> None:
        """ConflictError inherits from APIError."""
        error = ConflictError("Test")
        assert isinstance(error, APIError)
        assert isinstance(error, UESClientError)
    
    def test_status_code_is_always_409(self) -> None:
        """ConflictError always has status_code 409."""
        error = ConflictError("Test")
        assert error.status_code == 409
    
    def test_error_type_is_always_conflict(self) -> None:
        """ConflictError always has error_type 'conflict'."""
        error = ConflictError("Test")
        assert error.error_type == "conflict"
    
    def test_str_format(self) -> None:
        """String representation follows APIError format."""
        error = ConflictError("Simulation not running")
        assert str(error) == "[HTTP 409] [conflict] Simulation not running"
    
    def test_common_scenario_simulation_already_running(self) -> None:
        """Test common scenario: trying to start already-running simulation."""
        error = ConflictError(
            message="Simulation is already running",
            details={"action": "start", "current_state": "running"},
        )
        
        assert error.status_code == 409
        assert "already running" in error.message
    
    def test_common_scenario_nothing_to_undo(self) -> None:
        """Test common scenario: trying to undo with empty history."""
        error = ConflictError(
            message="Nothing to undo",
            details={"undo_stack_size": 0},
        )
        
        assert error.status_code == 409
        assert error.details["undo_stack_size"] == 0


# =============================================================================
# ServerError Tests
# =============================================================================

class TestServerError:
    """Tests for the ServerError exception class.
    
    ServerError is raised when the server encounters an internal error
    (HTTP 5xx). These errors are typically not recoverable by the client
    and indicate a server-side issue.
    """
    
    def test_instantiation_with_message_only(self) -> None:
        """ServerError can be instantiated with just a message.
        
        Status code defaults to 500.
        """
        error = ServerError("Internal server error")
        
        assert error.message == "Internal server error"
        assert error.status_code == 500
        assert error.error_type == "server_error"
    
    def test_instantiation_with_custom_status_code(self) -> None:
        """ServerError can have different 5xx status codes.
        
        Common codes: 500 (Internal), 502 (Bad Gateway), 503 (Unavailable),
        504 (Gateway Timeout).
        """
        error_502 = ServerError("Bad gateway", status_code=502)
        error_503 = ServerError("Service unavailable", status_code=503)
        error_504 = ServerError("Gateway timeout", status_code=504)
        
        assert error_502.status_code == 502
        assert error_503.status_code == 503
        assert error_504.status_code == 504
    
    def test_instantiation_with_all_attributes(self) -> None:
        """ServerError can include details and response body."""
        error = ServerError(
            message="Database connection failed",
            status_code=503,
            details={"database": "primary", "retry_after": 30},
            response_body={"error": "database_unavailable"},
        )
        
        assert error.details == {"database": "primary", "retry_after": 30}
        assert error.response_body == {"error": "database_unavailable"}
    
    def test_inherits_from_api_error(self) -> None:
        """ServerError inherits from APIError."""
        error = ServerError("Test")
        assert isinstance(error, APIError)
        assert isinstance(error, UESClientError)
    
    def test_error_type_is_always_server_error(self) -> None:
        """ServerError always has error_type 'server_error'."""
        error = ServerError("Test", status_code=503)
        assert error.error_type == "server_error"
    
    def test_str_format(self) -> None:
        """String representation follows APIError format."""
        error = ServerError("Internal error", status_code=500)
        assert str(error) == "[HTTP 500] [server_error] Internal error"


# =============================================================================
# Exception Hierarchy Tests
# =============================================================================

class TestExceptionHierarchy:
    """Tests verifying the exception inheritance hierarchy.
    
    These tests ensure that exceptions can be caught at various levels
    of specificity, from catching a single exception type to catching
    all client errors with UESClientError.
    """
    
    def test_all_exceptions_inherit_from_ues_client_error(self) -> None:
        """All client exceptions inherit from UESClientError.
        
        This allows catching any client error with a single except clause.
        """
        exceptions = [
            ConnectionError("test"),
            TimeoutError("test"),
            APIError("test", status_code=400),
            ValidationError("test"),
            NotFoundError("test"),
            ConflictError("test"),
            ServerError("test"),
        ]
        
        for exc in exceptions:
            assert isinstance(exc, UESClientError), f"{type(exc).__name__} should inherit from UESClientError"
    
    def test_api_error_subclasses_inherit_from_api_error(self) -> None:
        """ValidationError, NotFoundError, ConflictError, ServerError inherit from APIError."""
        api_exceptions = [
            ValidationError("test"),
            NotFoundError("test"),
            ConflictError("test"),
            ServerError("test"),
        ]
        
        for exc in api_exceptions:
            assert isinstance(exc, APIError), f"{type(exc).__name__} should inherit from APIError"
    
    def test_connection_and_timeout_not_api_errors(self) -> None:
        """ConnectionError and TimeoutError are NOT APIError subclasses.
        
        These represent client-side failures, not server responses.
        """
        assert not isinstance(ConnectionError("test"), APIError)
        assert not isinstance(TimeoutError("test"), APIError)
    
    def test_catch_specific_before_general(self) -> None:
        """Specific exceptions can be caught before general ones.
        
        This demonstrates the recommended pattern for exception handling.
        """
        caught_type = None
        
        try:
            raise ValidationError("Invalid data")
        except ValidationError:
            caught_type = "ValidationError"
        except APIError:
            caught_type = "APIError"
        except UESClientError:
            caught_type = "UESClientError"
        
        assert caught_type == "ValidationError"
    
    def test_catch_api_error_catches_subclasses(self) -> None:
        """Catching APIError catches all its subclasses."""
        subclass_exceptions = [
            ValidationError("test"),
            NotFoundError("test"),
            ConflictError("test"),
            ServerError("test"),
        ]
        
        for exc in subclass_exceptions:
            with pytest.raises(APIError):
                raise exc
    
    def test_catch_ues_client_error_catches_all(self) -> None:
        """Catching UESClientError catches all client exceptions."""
        all_exceptions = [
            ConnectionError("test"),
            TimeoutError("test"),
            APIError("test", status_code=400),
            ValidationError("test"),
            NotFoundError("test"),
            ConflictError("test"),
            ServerError("test"),
        ]
        
        for exc in all_exceptions:
            with pytest.raises(UESClientError):
                raise exc


# =============================================================================
# Real-World Usage Pattern Tests
# =============================================================================

class TestUsagePatterns:
    """Tests demonstrating real-world exception handling patterns.
    
    These tests serve as documentation for how the exception hierarchy
    should be used in practice.
    """
    
    def test_pattern_handle_network_errors_separately(self) -> None:
        """Pattern: Handle network errors separately from API errors.
        
        Network errors (ConnectionError, TimeoutError) require different
        handling than API errors - typically retrying or alerting about
        connectivity issues.
        """
        def simulate_network_error():
            raise ConnectionError("Server unreachable", url="http://localhost:8000")
        
        network_error_handled = False
        api_error_handled = False
        
        try:
            simulate_network_error()
        except (ConnectionError, TimeoutError) as e:
            network_error_handled = True
            # In practice: retry, check connectivity, alert user
        except APIError as e:
            api_error_handled = True
        
        assert network_error_handled
        assert not api_error_handled
    
    def test_pattern_handle_conflict_with_recovery(self) -> None:
        """Pattern: Handle ConflictError with recovery action.
        
        ConflictError often indicates the operation can succeed if
        preconditions are met (e.g., start simulation before advancing time).
        """
        simulation_started = False
        time_advanced = False
        
        def advance_time():
            nonlocal simulation_started
            if not simulation_started:
                raise ConflictError("Simulation not running")
            return True
        
        def start_simulation():
            nonlocal simulation_started
            simulation_started = True
        
        # First attempt fails, recovery action, second attempt succeeds
        try:
            time_advanced = advance_time()
        except ConflictError:
            start_simulation()
            time_advanced = advance_time()
        
        assert simulation_started
        assert time_advanced
    
    def test_pattern_extract_validation_details(self) -> None:
        """Pattern: Extract field-level errors from ValidationError.
        
        ValidationError.details typically contains a dict mapping field
        names to error messages, useful for form validation feedback.
        """
        error = ValidationError(
            message="Request validation failed",
            details={
                "to_addresses": ["At least one recipient is required"],
                "subject": ["Subject cannot exceed 200 characters"],
            },
        )
        
        # In practice: display errors next to form fields
        field_errors = error.details or {}
        assert "to_addresses" in field_errors
        assert len(field_errors["to_addresses"]) == 1
        assert "recipient" in field_errors["to_addresses"][0].lower()
    
    def test_pattern_log_api_errors_with_context(self) -> None:
        """Pattern: Log API errors with full context for debugging.
        
        APIError includes status_code, error_type, details, and
        response_body for comprehensive error logging.
        """
        error = APIError(
            message="Something went wrong",
            status_code=500,
            error_type="internal_error",
            details={"trace_id": "abc123"},
            response_body={"error": "internal", "trace_id": "abc123"},
        )
        
        # In practice: log all available information
        log_message = (
            f"API Error: {error.message} "
            f"(status={error.status_code}, type={error.error_type}, "
            f"details={error.details})"
        )
        
        assert "500" in log_message
        assert "internal_error" in log_message
        assert "abc123" in log_message
    
    def test_pattern_identify_missing_resource(self) -> None:
        """Pattern: Identify which resource was not found.
        
        NotFoundError can include resource_type and resource_id for
        specific error messages or recovery logic.
        """
        error = NotFoundError(
            message="Event not found",
            resource_type="event",
            resource_id="evt_nonexistent",
        )
        
        # In practice: provide specific guidance based on resource type
        if error.resource_type == "event":
            suggestion = f"Event '{error.resource_id}' may have been cancelled or expired"
        elif error.resource_type == "modality":
            suggestion = f"Modality '{error.resource_id}' is not available"
        else:
            suggestion = "The requested resource does not exist"
        
        assert "evt_nonexistent" in suggestion
