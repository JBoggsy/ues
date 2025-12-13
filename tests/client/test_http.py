"""Unit tests for the UES client HTTP utilities.

This module tests the HTTP handling layer defined in client/_http.py.
The tests verify:

1. Helper Functions:
   - _parse_error_response: Extracting error info from various response formats
   - _raise_for_status: Mapping HTTP status codes to exception types
   - _calculate_backoff: Exponential backoff calculation for retries

2. HTTPClient (Synchronous):
   - Initialization with various configurations
   - Context manager support
   - Request methods (GET, POST, PUT, DELETE)
   - Error handling and exception mapping
   - Retry logic with exponential backoff
   - Query parameter filtering

3. AsyncHTTPClient (Asynchronous):
   - Same functionality as HTTPClient but async
   - Async context manager support
   - Async request methods

Note: These tests use httpx's mock transport to avoid real network calls.
"""

import pytest
import httpx

from client._http import (
    HTTPClient,
    AsyncHTTPClient,
    _parse_error_response,
    _raise_for_status,
    _calculate_backoff,
    RETRYABLE_STATUS_CODES,
    DEFAULT_RETRY_BACKOFF_BASE,
    DEFAULT_RETRY_BACKOFF_MAX,
)
from client.exceptions import (
    APIError,
    ConflictError,
    ConnectionError,
    NotFoundError,
    ServerError,
    TimeoutError,
    ValidationError,
)


# =============================================================================
# Helper Function Tests: _parse_error_response
# =============================================================================

class TestParseErrorResponse:
    """Tests for the _parse_error_response helper function.
    
    This function extracts structured error information from HTTP responses
    in various formats (FastAPI standard, custom formats, plain text).
    """
    
    def test_parse_fastapi_detail_string(self) -> None:
        """Parse FastAPI error with string detail.
        
        FastAPI's default error format uses {"detail": "message"}.
        """
        response = httpx.Response(
            status_code=400,
            json={"detail": "Invalid request"},
        )
        message, error_type, details = _parse_error_response(response)
        
        assert message == "Invalid request"
        assert error_type is None
        assert details is None
    
    def test_parse_fastapi_detail_with_type(self) -> None:
        """Parse FastAPI error with detail and type fields."""
        response = httpx.Response(
            status_code=409,
            json={
                "detail": "Simulation already running",
                "type": "conflict",
            },
        )
        message, error_type, details = _parse_error_response(response)
        
        assert message == "Simulation already running"
        assert error_type == "conflict"
    
    def test_parse_fastapi_validation_errors(self) -> None:
        """Parse FastAPI's validation error list format.
        
        FastAPI returns validation errors as a list in the detail field.
        """
        response = httpx.Response(
            status_code=422,
            json={
                "detail": [
                    {"loc": ["body", "email"], "msg": "invalid email format", "type": "value_error"},
                    {"loc": ["body", "name"], "msg": "field required", "type": "missing"},
                ]
            },
        )
        message, error_type, details = _parse_error_response(response)
        
        assert "email: invalid email format" in message
        assert "name: field required" in message
        assert error_type == "validation_error"
        assert details is not None
        assert "errors" in details
    
    def test_parse_detail_as_dict(self) -> None:
        """Parse error where detail is a nested dict with message."""
        response = httpx.Response(
            status_code=400,
            json={
                "detail": {
                    "message": "Custom error message",
                    "type": "custom_error",
                    "extra": "data",
                }
            },
        )
        message, error_type, details = _parse_error_response(response)
        
        assert message == "Custom error message"
        assert error_type == "custom_error"
    
    def test_parse_message_field(self) -> None:
        """Parse error with 'message' field instead of 'detail'."""
        response = httpx.Response(
            status_code=500,
            json={
                "message": "Internal error occurred",
                "type": "server_error",
                "details": {"trace_id": "abc123"},
            },
        )
        message, error_type, details = _parse_error_response(response)
        
        assert message == "Internal error occurred"
        assert error_type == "server_error"
        assert details == {"trace_id": "abc123"}
    
    def test_parse_error_field(self) -> None:
        """Parse error with 'error' field."""
        response = httpx.Response(
            status_code=400,
            json={
                "error": "Something went wrong",
                "type": "bad_request",
            },
        )
        message, error_type, details = _parse_error_response(response)
        
        assert message == "Something went wrong"
        assert error_type == "bad_request"
    
    def test_parse_plain_json_object(self) -> None:
        """Parse error that's a plain JSON object without standard fields."""
        response = httpx.Response(
            status_code=400,
            json={"foo": "bar", "baz": 123},
        )
        message, error_type, details = _parse_error_response(response)
        
        # Falls back to string representation of the object
        assert "foo" in message or "bar" in message
    
    def test_parse_plain_text_response(self) -> None:
        """Parse error with plain text body (not JSON)."""
        response = httpx.Response(
            status_code=500,
            text="Internal Server Error",
        )
        message, error_type, details = _parse_error_response(response)
        
        assert message == "Internal Server Error"
        assert error_type is None
        assert details is None
    
    def test_parse_empty_response(self) -> None:
        """Parse error with empty response body."""
        response = httpx.Response(
            status_code=404,
            text="",
        )
        message, error_type, details = _parse_error_response(response)
        
        assert "404" in message
        assert error_type is None


# =============================================================================
# Helper Function Tests: _raise_for_status
# =============================================================================

class TestRaiseForStatus:
    """Tests for the _raise_for_status helper function.
    
    This function maps HTTP status codes to appropriate exception types
    and extracts error details from the response body.
    """
    
    def test_success_does_not_raise(self) -> None:
        """Successful responses (2xx) do not raise exceptions."""
        for status_code in [200, 201, 204]:
            response = httpx.Response(status_code=status_code)
            _raise_for_status(response)  # Should not raise
    
    def test_422_raises_validation_error(self) -> None:
        """HTTP 422 raises ValidationError."""
        response = httpx.Response(
            status_code=422,
            json={"detail": "Validation failed"},
        )
        
        with pytest.raises(ValidationError) as exc_info:
            _raise_for_status(response)
        
        assert exc_info.value.status_code == 422
        assert "Validation failed" in exc_info.value.message
    
    def test_404_raises_not_found_error(self) -> None:
        """HTTP 404 raises NotFoundError."""
        response = httpx.Response(
            status_code=404,
            json={"detail": "Event not found"},
        )
        
        with pytest.raises(NotFoundError) as exc_info:
            _raise_for_status(response)
        
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.message.lower()
    
    def test_409_raises_conflict_error(self) -> None:
        """HTTP 409 raises ConflictError."""
        response = httpx.Response(
            status_code=409,
            json={"detail": "Simulation already running"},
        )
        
        with pytest.raises(ConflictError) as exc_info:
            _raise_for_status(response)
        
        assert exc_info.value.status_code == 409
        assert "already running" in exc_info.value.message
    
    def test_500_raises_server_error(self) -> None:
        """HTTP 500 raises ServerError."""
        response = httpx.Response(
            status_code=500,
            json={"detail": "Internal server error"},
        )
        
        with pytest.raises(ServerError) as exc_info:
            _raise_for_status(response)
        
        assert exc_info.value.status_code == 500
    
    def test_502_raises_server_error(self) -> None:
        """HTTP 502 (Bad Gateway) raises ServerError."""
        response = httpx.Response(
            status_code=502,
            json={"detail": "Bad gateway"},
        )
        
        with pytest.raises(ServerError) as exc_info:
            _raise_for_status(response)
        
        assert exc_info.value.status_code == 502
    
    def test_503_raises_server_error(self) -> None:
        """HTTP 503 (Service Unavailable) raises ServerError."""
        response = httpx.Response(
            status_code=503,
            json={"detail": "Service unavailable"},
        )
        
        with pytest.raises(ServerError) as exc_info:
            _raise_for_status(response)
        
        assert exc_info.value.status_code == 503
    
    def test_other_4xx_raises_api_error(self) -> None:
        """Other 4xx codes raise generic APIError."""
        for status_code in [400, 401, 403, 405, 429]:
            response = httpx.Response(
                status_code=status_code,
                json={"detail": f"Error {status_code}"},
            )
            
            with pytest.raises(APIError) as exc_info:
                _raise_for_status(response)
            
            assert exc_info.value.status_code == status_code
    
    def test_response_body_is_preserved(self) -> None:
        """The raw response body is preserved in the exception."""
        body = {"detail": "Error", "extra": "data"}
        response = httpx.Response(status_code=400, json=body)
        
        with pytest.raises(APIError) as exc_info:
            _raise_for_status(response)
        
        assert exc_info.value.response_body == body


# =============================================================================
# Helper Function Tests: _calculate_backoff
# =============================================================================

class TestCalculateBackoff:
    """Tests for the _calculate_backoff helper function.
    
    This function calculates exponential backoff delays for retry logic.
    """
    
    def test_first_attempt_uses_base(self) -> None:
        """First attempt (0) uses the base delay."""
        delay = _calculate_backoff(0)
        assert delay == DEFAULT_RETRY_BACKOFF_BASE
    
    def test_exponential_growth(self) -> None:
        """Delay grows exponentially with each attempt."""
        delay_0 = _calculate_backoff(0)  # 0.5
        delay_1 = _calculate_backoff(1)  # 1.0
        delay_2 = _calculate_backoff(2)  # 2.0
        delay_3 = _calculate_backoff(3)  # 4.0
        
        assert delay_1 == delay_0 * 2
        assert delay_2 == delay_1 * 2
        assert delay_3 == delay_2 * 2
    
    def test_capped_at_max(self) -> None:
        """Delay is capped at the maximum value."""
        # Attempt 10 would be 0.5 * 2^10 = 512 seconds without cap
        delay = _calculate_backoff(10)
        assert delay == DEFAULT_RETRY_BACKOFF_MAX
    
    def test_custom_base(self) -> None:
        """Custom base value is used in calculation."""
        delay = _calculate_backoff(0, base=1.0)
        assert delay == 1.0
        
        delay = _calculate_backoff(2, base=1.0)
        assert delay == 4.0  # 1.0 * 2^2
    
    def test_specific_values(self) -> None:
        """Verify specific expected values."""
        assert _calculate_backoff(0) == 0.5
        assert _calculate_backoff(1) == 1.0
        assert _calculate_backoff(2) == 2.0
        assert _calculate_backoff(3) == 4.0
        assert _calculate_backoff(4) == 8.0
        assert _calculate_backoff(5) == 16.0
        assert _calculate_backoff(6) == 30.0  # Capped


# =============================================================================
# HTTPClient Tests: Initialization
# =============================================================================

class TestHTTPClientInit:
    """Tests for HTTPClient initialization."""
    
    def test_default_initialization(self) -> None:
        """HTTPClient initializes with default values."""
        client = HTTPClient(base_url="http://localhost:8000")
        
        assert client.base_url == "http://localhost:8000"
        assert client.timeout == 30.0
        assert client.retry_enabled is False
        assert client.max_retries == 3
        
        client.close()
    
    def test_custom_initialization(self) -> None:
        """HTTPClient accepts custom configuration."""
        client = HTTPClient(
            base_url="http://api.example.com:9000",
            timeout=60.0,
            retry_enabled=True,
            max_retries=5,
        )
        
        assert client.base_url == "http://api.example.com:9000"
        assert client.timeout == 60.0
        assert client.retry_enabled is True
        assert client.max_retries == 5
        
        client.close()
    
    def test_base_url_trailing_slash_stripped(self) -> None:
        """Trailing slash is stripped from base_url."""
        client = HTTPClient(base_url="http://localhost:8000/")
        assert client.base_url == "http://localhost:8000"
        client.close()
    
    def test_context_manager(self) -> None:
        """HTTPClient supports context manager protocol."""
        with HTTPClient(base_url="http://localhost:8000") as client:
            assert isinstance(client, HTTPClient)
        # Client should be closed after exiting context


# =============================================================================
# HTTPClient Tests: Request Methods with Mocking
# =============================================================================

class TestHTTPClientRequests:
    """Tests for HTTPClient request methods.
    
    These tests use httpx's mock transport to avoid real network calls.
    """
    
    def test_get_request_success(self) -> None:
        """GET request returns parsed JSON response."""
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "GET"
            assert str(request.url).endswith("/api/test")
            return httpx.Response(200, json={"result": "success"})
        
        client = HTTPClient(base_url="http://localhost:8000")
        client._client = httpx.Client(
            base_url="http://localhost:8000",
            transport=httpx.MockTransport(handler),
        )
        
        result = client.get("/api/test")
        assert result == {"result": "success"}
        
        client.close()
    
    def test_get_with_query_params(self) -> None:
        """GET request includes query parameters."""
        def handler(request: httpx.Request) -> httpx.Response:
            assert "foo=bar" in str(request.url)
            assert "limit=10" in str(request.url)
            return httpx.Response(200, json={"data": []})
        
        client = HTTPClient(base_url="http://localhost:8000")
        client._client = httpx.Client(
            base_url="http://localhost:8000",
            transport=httpx.MockTransport(handler),
        )
        
        result = client.get("/api/items", params={"foo": "bar", "limit": 10})
        assert result == {"data": []}
        
        client.close()
    
    def test_get_filters_none_params(self) -> None:
        """GET request filters out None values from params."""
        def handler(request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            assert "foo=bar" in url_str
            assert "none_val" not in url_str
            return httpx.Response(200, json={})
        
        client = HTTPClient(base_url="http://localhost:8000")
        client._client = httpx.Client(
            base_url="http://localhost:8000",
            transport=httpx.MockTransport(handler),
        )
        
        client.get("/api/test", params={"foo": "bar", "none_val": None})
        client.close()
    
    def test_post_request_with_json_body(self) -> None:
        """POST request sends JSON body."""
        received_body = None
        
        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal received_body
            assert request.method == "POST"
            received_body = request.content
            return httpx.Response(201, json={"id": "new-123"})
        
        client = HTTPClient(base_url="http://localhost:8000")
        client._client = httpx.Client(
            base_url="http://localhost:8000",
            transport=httpx.MockTransport(handler),
        )
        
        result = client.post("/api/items", json={"name": "test", "value": 42})
        
        assert result == {"id": "new-123"}
        assert b"name" in received_body
        assert b"test" in received_body
        
        client.close()
    
    def test_put_request(self) -> None:
        """PUT request works correctly."""
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "PUT"
            return httpx.Response(200, json={"updated": True})
        
        client = HTTPClient(base_url="http://localhost:8000")
        client._client = httpx.Client(
            base_url="http://localhost:8000",
            transport=httpx.MockTransport(handler),
        )
        
        result = client.put("/api/items/123", json={"name": "updated"})
        assert result == {"updated": True}
        
        client.close()
    
    def test_delete_request(self) -> None:
        """DELETE request works correctly."""
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "DELETE"
            return httpx.Response(200, json={"deleted": True})
        
        client = HTTPClient(base_url="http://localhost:8000")
        client._client = httpx.Client(
            base_url="http://localhost:8000",
            transport=httpx.MockTransport(handler),
        )
        
        result = client.delete("/api/items/123")
        assert result == {"deleted": True}
        
        client.close()
    
    def test_empty_response_returns_none(self) -> None:
        """Empty response body returns None."""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(204, content=b"")
        
        client = HTTPClient(base_url="http://localhost:8000")
        client._client = httpx.Client(
            base_url="http://localhost:8000",
            transport=httpx.MockTransport(handler),
        )
        
        result = client.delete("/api/items/123")
        assert result is None
        
        client.close()


# =============================================================================
# HTTPClient Tests: Error Handling
# =============================================================================

class TestHTTPClientErrorHandling:
    """Tests for HTTPClient error handling."""
    
    def test_404_raises_not_found_error(self) -> None:
        """HTTP 404 response raises NotFoundError."""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"detail": "Not found"})
        
        client = HTTPClient(base_url="http://localhost:8000")
        client._client = httpx.Client(
            base_url="http://localhost:8000",
            transport=httpx.MockTransport(handler),
        )
        
        with pytest.raises(NotFoundError) as exc_info:
            client.get("/api/missing")
        
        assert exc_info.value.status_code == 404
        client.close()
    
    def test_422_raises_validation_error(self) -> None:
        """HTTP 422 response raises ValidationError."""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                422,
                json={"detail": [{"loc": ["body", "email"], "msg": "invalid"}]},
            )
        
        client = HTTPClient(base_url="http://localhost:8000")
        client._client = httpx.Client(
            base_url="http://localhost:8000",
            transport=httpx.MockTransport(handler),
        )
        
        with pytest.raises(ValidationError):
            client.post("/api/users", json={"email": "invalid"})
        
        client.close()
    
    def test_409_raises_conflict_error(self) -> None:
        """HTTP 409 response raises ConflictError."""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(409, json={"detail": "Conflict"})
        
        client = HTTPClient(base_url="http://localhost:8000")
        client._client = httpx.Client(
            base_url="http://localhost:8000",
            transport=httpx.MockTransport(handler),
        )
        
        with pytest.raises(ConflictError):
            client.post("/api/start")
        
        client.close()
    
    def test_500_raises_server_error(self) -> None:
        """HTTP 500 response raises ServerError."""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"detail": "Internal error"})
        
        client = HTTPClient(base_url="http://localhost:8000")
        client._client = httpx.Client(
            base_url="http://localhost:8000",
            transport=httpx.MockTransport(handler),
        )
        
        with pytest.raises(ServerError):
            client.get("/api/broken")
        
        client.close()
    
    def test_connection_error_raised(self) -> None:
        """Connection failure raises ConnectionError."""
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")
        
        client = HTTPClient(base_url="http://localhost:8000")
        client._client = httpx.Client(
            base_url="http://localhost:8000",
            transport=httpx.MockTransport(handler),
        )
        
        with pytest.raises(ConnectionError) as exc_info:
            client.get("/api/test")
        
        assert "localhost:8000" in exc_info.value.url
        client.close()
    
    def test_timeout_error_raised(self) -> None:
        """Timeout raises TimeoutError."""
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("Request timed out")
        
        client = HTTPClient(base_url="http://localhost:8000", timeout=5.0)
        client._client = httpx.Client(
            base_url="http://localhost:8000",
            transport=httpx.MockTransport(handler),
        )
        
        with pytest.raises(TimeoutError) as exc_info:
            client.get("/api/slow")
        
        assert exc_info.value.timeout == 5.0
        client.close()


# =============================================================================
# HTTPClient Tests: Retry Logic
# =============================================================================

class TestHTTPClientRetry:
    """Tests for HTTPClient retry logic."""
    
    def test_no_retry_by_default(self) -> None:
        """Retry is disabled by default - errors are raised immediately."""
        attempts = 0
        
        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            return httpx.Response(503, json={"detail": "Unavailable"})
        
        client = HTTPClient(base_url="http://localhost:8000")
        client._client = httpx.Client(
            base_url="http://localhost:8000",
            transport=httpx.MockTransport(handler),
        )
        
        with pytest.raises(ServerError):
            client.get("/api/test")
        
        assert attempts == 1
        client.close()
    
    def test_retry_on_503_when_enabled(self) -> None:
        """503 responses are retried when retry is enabled."""
        attempts = 0
        
        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                return httpx.Response(503, json={"detail": "Unavailable"})
            return httpx.Response(200, json={"result": "success"})
        
        client = HTTPClient(
            base_url="http://localhost:8000",
            retry_enabled=True,
            max_retries=3,
        )
        client._client = httpx.Client(
            base_url="http://localhost:8000",
            transport=httpx.MockTransport(handler),
        )
        
        result = client.get("/api/test")
        
        assert result == {"result": "success"}
        assert attempts == 3  # 2 failures + 1 success
        client.close()
    
    def test_retry_on_502_when_enabled(self) -> None:
        """502 responses are retried when retry is enabled."""
        attempts = 0
        
        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                return httpx.Response(502, json={"detail": "Bad gateway"})
            return httpx.Response(200, json={"ok": True})
        
        client = HTTPClient(
            base_url="http://localhost:8000",
            retry_enabled=True,
            max_retries=3,
        )
        client._client = httpx.Client(
            base_url="http://localhost:8000",
            transport=httpx.MockTransport(handler),
        )
        
        result = client.get("/api/test")
        assert result == {"ok": True}
        assert attempts == 2
        client.close()
    
    def test_retry_on_504_when_enabled(self) -> None:
        """504 responses are retried when retry is enabled."""
        attempts = 0
        
        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                return httpx.Response(504, json={"detail": "Gateway timeout"})
            return httpx.Response(200, json={"ok": True})
        
        client = HTTPClient(
            base_url="http://localhost:8000",
            retry_enabled=True,
            max_retries=3,
        )
        client._client = httpx.Client(
            base_url="http://localhost:8000",
            transport=httpx.MockTransport(handler),
        )
        
        result = client.get("/api/test")
        assert result == {"ok": True}
        assert attempts == 2
        client.close()
    
    def test_no_retry_on_400(self) -> None:
        """400 errors are NOT retried (client errors are not transient)."""
        attempts = 0
        
        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            return httpx.Response(400, json={"detail": "Bad request"})
        
        client = HTTPClient(
            base_url="http://localhost:8000",
            retry_enabled=True,
            max_retries=3,
        )
        client._client = httpx.Client(
            base_url="http://localhost:8000",
            transport=httpx.MockTransport(handler),
        )
        
        with pytest.raises(APIError):
            client.get("/api/test")
        
        assert attempts == 1  # No retries
        client.close()
    
    def test_no_retry_on_500(self) -> None:
        """500 errors are NOT retried (only 502, 503, 504 are transient)."""
        attempts = 0
        
        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            return httpx.Response(500, json={"detail": "Internal error"})
        
        client = HTTPClient(
            base_url="http://localhost:8000",
            retry_enabled=True,
            max_retries=3,
        )
        client._client = httpx.Client(
            base_url="http://localhost:8000",
            transport=httpx.MockTransport(handler),
        )
        
        with pytest.raises(ServerError):
            client.get("/api/test")
        
        assert attempts == 1  # No retries
        client.close()
    
    def test_max_retries_exhausted(self) -> None:
        """Error raised after max retries exhausted."""
        attempts = 0
        
        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            return httpx.Response(503, json={"detail": "Always unavailable"})
        
        client = HTTPClient(
            base_url="http://localhost:8000",
            retry_enabled=True,
            max_retries=2,
        )
        client._client = httpx.Client(
            base_url="http://localhost:8000",
            transport=httpx.MockTransport(handler),
        )
        
        with pytest.raises(ServerError):
            client.get("/api/test")
        
        # Initial attempt + 2 retries = 3 total
        assert attempts == 3
        client.close()
    
    def test_retry_on_connection_error(self) -> None:
        """Connection errors are retried when retry is enabled."""
        attempts = 0
        
        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise httpx.ConnectError("Connection refused")
            return httpx.Response(200, json={"connected": True})
        
        client = HTTPClient(
            base_url="http://localhost:8000",
            retry_enabled=True,
            max_retries=3,
        )
        client._client = httpx.Client(
            base_url="http://localhost:8000",
            transport=httpx.MockTransport(handler),
        )
        
        result = client.get("/api/test")
        
        assert result == {"connected": True}
        assert attempts == 2
        client.close()
    
    def test_retry_on_timeout_error(self) -> None:
        """Timeout errors are retried when retry is enabled."""
        attempts = 0
        
        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise httpx.TimeoutException("Timed out")
            return httpx.Response(200, json={"ok": True})
        
        client = HTTPClient(
            base_url="http://localhost:8000",
            retry_enabled=True,
            max_retries=3,
        )
        client._client = httpx.Client(
            base_url="http://localhost:8000",
            transport=httpx.MockTransport(handler),
        )
        
        result = client.get("/api/test")
        
        assert result == {"ok": True}
        assert attempts == 2
        client.close()


# =============================================================================
# AsyncHTTPClient Tests
# =============================================================================

class TestAsyncHTTPClientInit:
    """Tests for AsyncHTTPClient initialization."""
    
    def test_default_initialization(self) -> None:
        """AsyncHTTPClient initializes with default values."""
        client = AsyncHTTPClient(base_url="http://localhost:8000")
        
        assert client.base_url == "http://localhost:8000"
        assert client.timeout == 30.0
        assert client.retry_enabled is False
        assert client.max_retries == 3
    
    def test_custom_initialization(self) -> None:
        """AsyncHTTPClient accepts custom configuration."""
        client = AsyncHTTPClient(
            base_url="http://api.example.com",
            timeout=60.0,
            retry_enabled=True,
            max_retries=5,
        )
        
        assert client.base_url == "http://api.example.com"
        assert client.timeout == 60.0
        assert client.retry_enabled is True
        assert client.max_retries == 5
    
    def test_base_url_trailing_slash_stripped(self) -> None:
        """Trailing slash is stripped from base_url."""
        client = AsyncHTTPClient(base_url="http://localhost:8000/")
        assert client.base_url == "http://localhost:8000"


class TestAsyncHTTPClientRequests:
    """Tests for AsyncHTTPClient request methods."""
    
    async def test_async_context_manager(self) -> None:
        """AsyncHTTPClient supports async context manager."""
        async with AsyncHTTPClient(base_url="http://localhost:8000") as client:
            assert isinstance(client, AsyncHTTPClient)
    
    async def test_async_get_request(self) -> None:
        """Async GET request returns parsed JSON response."""
        async def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "GET"
            return httpx.Response(200, json={"async": True})
        
        client = AsyncHTTPClient(base_url="http://localhost:8000")
        client._client = httpx.AsyncClient(
            base_url="http://localhost:8000",
            transport=httpx.MockTransport(handler),
        )
        
        result = await client.get("/api/test")
        assert result == {"async": True}
        
        await client.close()
    
    async def test_async_post_request(self) -> None:
        """Async POST request sends JSON body."""
        async def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "POST"
            return httpx.Response(201, json={"created": True})
        
        client = AsyncHTTPClient(base_url="http://localhost:8000")
        client._client = httpx.AsyncClient(
            base_url="http://localhost:8000",
            transport=httpx.MockTransport(handler),
        )
        
        result = await client.post("/api/items", json={"name": "test"})
        assert result == {"created": True}
        
        await client.close()
    
    async def test_async_put_request(self) -> None:
        """Async PUT request works correctly."""
        async def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "PUT"
            return httpx.Response(200, json={"updated": True})
        
        client = AsyncHTTPClient(base_url="http://localhost:8000")
        client._client = httpx.AsyncClient(
            base_url="http://localhost:8000",
            transport=httpx.MockTransport(handler),
        )
        
        result = await client.put("/api/items/1", json={"name": "updated"})
        assert result == {"updated": True}
        
        await client.close()
    
    async def test_async_delete_request(self) -> None:
        """Async DELETE request works correctly."""
        async def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "DELETE"
            return httpx.Response(200, json={"deleted": True})
        
        client = AsyncHTTPClient(base_url="http://localhost:8000")
        client._client = httpx.AsyncClient(
            base_url="http://localhost:8000",
            transport=httpx.MockTransport(handler),
        )
        
        result = await client.delete("/api/items/1")
        assert result == {"deleted": True}
        
        await client.close()


class TestAsyncHTTPClientErrorHandling:
    """Tests for AsyncHTTPClient error handling."""
    
    async def test_async_404_raises_not_found(self) -> None:
        """Async 404 response raises NotFoundError."""
        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"detail": "Not found"})
        
        client = AsyncHTTPClient(base_url="http://localhost:8000")
        client._client = httpx.AsyncClient(
            base_url="http://localhost:8000",
            transport=httpx.MockTransport(handler),
        )
        
        with pytest.raises(NotFoundError):
            await client.get("/api/missing")
        
        await client.close()
    
    async def test_async_connection_error(self) -> None:
        """Async connection failure raises ConnectionError."""
        async def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")
        
        client = AsyncHTTPClient(base_url="http://localhost:8000")
        client._client = httpx.AsyncClient(
            base_url="http://localhost:8000",
            transport=httpx.MockTransport(handler),
        )
        
        with pytest.raises(ConnectionError):
            await client.get("/api/test")
        
        await client.close()
    
    async def test_async_timeout_error(self) -> None:
        """Async timeout raises TimeoutError."""
        async def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("Timed out")
        
        client = AsyncHTTPClient(base_url="http://localhost:8000", timeout=5.0)
        client._client = httpx.AsyncClient(
            base_url="http://localhost:8000",
            transport=httpx.MockTransport(handler),
        )
        
        with pytest.raises(TimeoutError) as exc_info:
            await client.get("/api/slow")
        
        assert exc_info.value.timeout == 5.0
        await client.close()


class TestAsyncHTTPClientRetry:
    """Tests for AsyncHTTPClient retry logic."""
    
    async def test_async_retry_on_503(self) -> None:
        """Async 503 responses are retried when enabled."""
        attempts = 0
        
        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                return httpx.Response(503, json={"detail": "Unavailable"})
            return httpx.Response(200, json={"ok": True})
        
        client = AsyncHTTPClient(
            base_url="http://localhost:8000",
            retry_enabled=True,
            max_retries=3,
        )
        client._client = httpx.AsyncClient(
            base_url="http://localhost:8000",
            transport=httpx.MockTransport(handler),
        )
        
        result = await client.get("/api/test")
        
        assert result == {"ok": True}
        assert attempts == 2
        await client.close()
    
    async def test_async_max_retries_exhausted(self) -> None:
        """Async error raised after max retries exhausted."""
        attempts = 0
        
        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            return httpx.Response(503, json={"detail": "Always unavailable"})
        
        client = AsyncHTTPClient(
            base_url="http://localhost:8000",
            retry_enabled=True,
            max_retries=2,
        )
        client._client = httpx.AsyncClient(
            base_url="http://localhost:8000",
            transport=httpx.MockTransport(handler),
        )
        
        with pytest.raises(ServerError):
            await client.get("/api/test")
        
        assert attempts == 3  # Initial + 2 retries
        await client.close()


# =============================================================================
# Retryable Status Codes Constant Tests
# =============================================================================

class TestRetryableStatusCodes:
    """Tests verifying the retryable status codes constant."""
    
    def test_502_is_retryable(self) -> None:
        """HTTP 502 (Bad Gateway) is in the retryable set."""
        assert 502 in RETRYABLE_STATUS_CODES
    
    def test_503_is_retryable(self) -> None:
        """HTTP 503 (Service Unavailable) is in the retryable set."""
        assert 503 in RETRYABLE_STATUS_CODES
    
    def test_504_is_retryable(self) -> None:
        """HTTP 504 (Gateway Timeout) is in the retryable set."""
        assert 504 in RETRYABLE_STATUS_CODES
    
    def test_500_is_not_retryable(self) -> None:
        """HTTP 500 (Internal Server Error) is NOT retryable.
        
        500 errors typically indicate bugs, not transient failures.
        """
        assert 500 not in RETRYABLE_STATUS_CODES
    
    def test_4xx_not_retryable(self) -> None:
        """4xx client errors are NOT retryable."""
        for code in [400, 401, 403, 404, 409, 422, 429]:
            assert code not in RETRYABLE_STATUS_CODES
