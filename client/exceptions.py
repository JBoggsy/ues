"""Exception hierarchy for the UES API client.

This module defines all exceptions that can be raised by the UES client library.
The hierarchy is designed to allow catching specific error types or broader
categories as needed.

Exception Hierarchy:
    UESClientError (base)
    ├── ConnectionError - Network/connection failures
    ├── TimeoutError - Request timeout
    └── APIError - Server returned an error response
        ├── ValidationError (HTTP 422)
        ├── NotFoundError (HTTP 404)
        ├── ConflictError (HTTP 409)
        └── ServerError (HTTP 5xx)

Example:
    Catching specific errors::
    
        try:
            client.simulation.start()
        except ConflictError:
            # Simulation already running
            pass
        except ValidationError as e:
            print(f"Invalid request: {e.message}")
    
    Catching all API errors::
    
        try:
            client.email.send(...)
        except APIError as e:
            print(f"API error {e.status_code}: {e.message}")
    
    Catching all client errors::
    
        try:
            client.time.advance(seconds=100)
        except UESClientError as e:
            print(f"Client error: {e}")
"""

from typing import Any


class UESClientError(Exception):
    """Base exception for all UES client errors.
    
    All exceptions raised by the UES client library inherit from this class,
    making it easy to catch any client-related error.
    
    Attributes:
        message: Human-readable error description.
    """
    
    def __init__(self, message: str) -> None:
        """Initialize the exception.
        
        Args:
            message: Human-readable error description.
        """
        self.message = message
        super().__init__(message)
    
    def __str__(self) -> str:
        """Return string representation of the error."""
        return self.message


class ConnectionError(UESClientError):
    """Failed to connect to the UES server.
    
    Raised when the client cannot establish a connection to the server.
    This may be due to network issues, the server being down, or an
    incorrect base URL.
    
    Attributes:
        message: Human-readable error description.
        url: The URL that failed to connect.
        cause: The underlying exception that caused the connection failure.
    """
    
    def __init__(
        self,
        message: str,
        url: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize the exception.
        
        Args:
            message: Human-readable error description.
            url: The URL that failed to connect.
            cause: The underlying exception that caused the failure.
        """
        self.url = url
        self.cause = cause
        super().__init__(message)
    
    def __str__(self) -> str:
        """Return string representation including URL if available."""
        if self.url:
            return f"{self.message} (url: {self.url})"
        return self.message


class TimeoutError(UESClientError):
    """Request timed out.
    
    Raised when a request to the server takes longer than the configured
    timeout duration.
    
    Attributes:
        message: Human-readable error description.
        timeout: The timeout value in seconds.
        url: The URL that timed out.
    """
    
    def __init__(
        self,
        message: str,
        timeout: float | None = None,
        url: str | None = None,
    ) -> None:
        """Initialize the exception.
        
        Args:
            message: Human-readable error description.
            timeout: The timeout value in seconds.
            url: The URL that timed out.
        """
        self.timeout = timeout
        self.url = url
        super().__init__(message)
    
    def __str__(self) -> str:
        """Return string representation including timeout if available."""
        parts = [self.message]
        if self.timeout is not None:
            parts.append(f"timeout: {self.timeout}s")
        if self.url:
            parts.append(f"url: {self.url}")
        return " ".join(parts) if len(parts) == 1 else f"{parts[0]} ({', '.join(parts[1:])})"


class APIError(UESClientError):
    """Server returned an error response.
    
    Base class for all API-level errors. Raised when the server returns
    an HTTP error status code (4xx or 5xx).
    
    Attributes:
        message: Human-readable error message.
        status_code: HTTP status code from the server.
        error_type: Error type/code from the response body (if available).
        details: Additional error details from the response (if available).
        response_body: Raw response body for debugging.
    """
    
    def __init__(
        self,
        message: str,
        status_code: int,
        error_type: str | None = None,
        details: dict[str, Any] | None = None,
        response_body: Any = None,
    ) -> None:
        """Initialize the exception.
        
        Args:
            message: Human-readable error message.
            status_code: HTTP status code from the server.
            error_type: Error type/code from the response body.
            details: Additional error details from the response.
            response_body: Raw response body for debugging.
        """
        self.status_code = status_code
        self.error_type = error_type
        self.details = details
        self.response_body = response_body
        super().__init__(message)
    
    def __str__(self) -> str:
        """Return string representation including status code."""
        base = f"[HTTP {self.status_code}] {self.message}"
        if self.error_type:
            base = f"[HTTP {self.status_code}] [{self.error_type}] {self.message}"
        return base


class ValidationError(APIError):
    """Request validation failed (HTTP 422).
    
    Raised when the server rejects a request due to invalid data.
    The details attribute typically contains field-level validation errors.
    
    Example:
        try:
            client.email.send(to_addresses=[])  # Empty list not allowed
        except ValidationError as e:
            print(f"Validation failed: {e.message}")
            for field, errors in (e.details or {}).items():
                print(f"  {field}: {errors}")
    """
    
    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        response_body: Any = None,
    ) -> None:
        """Initialize the exception.
        
        Args:
            message: Human-readable error message.
            details: Field-level validation errors.
            response_body: Raw response body for debugging.
        """
        super().__init__(
            message=message,
            status_code=422,
            error_type="validation_error",
            details=details,
            response_body=response_body,
        )


class NotFoundError(APIError):
    """Resource not found (HTTP 404).
    
    Raised when the requested resource doesn't exist. This could be
    an unknown modality, event ID, or other resource identifier.
    
    Attributes:
        resource_type: The type of resource that wasn't found (if known).
        resource_id: The identifier that wasn't found (if known).
    """
    
    def __init__(
        self,
        message: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
        response_body: Any = None,
    ) -> None:
        """Initialize the exception.
        
        Args:
            message: Human-readable error message.
            resource_type: The type of resource that wasn't found.
            resource_id: The identifier that wasn't found.
            details: Additional error details.
            response_body: Raw response body for debugging.
        """
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(
            message=message,
            status_code=404,
            error_type="not_found",
            details=details,
            response_body=response_body,
        )


class ConflictError(APIError):
    """State conflict (HTTP 409).
    
    Raised when an operation cannot be performed due to the current
    state of the system. Common cases include:
    - Trying to start a simulation that's already running
    - Trying to advance time when simulation is stopped
    - Trying to undo when there's nothing to undo
    
    Example:
        try:
            client.time.advance(seconds=100)
        except ConflictError:
            # Simulation not running - start it first
            client.simulation.start()
            client.time.advance(seconds=100)
    """
    
    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        response_body: Any = None,
    ) -> None:
        """Initialize the exception.
        
        Args:
            message: Human-readable error message.
            details: Additional error details.
            response_body: Raw response body for debugging.
        """
        super().__init__(
            message=message,
            status_code=409,
            error_type="conflict",
            details=details,
            response_body=response_body,
        )


class ServerError(APIError):
    """Server-side error (HTTP 5xx).
    
    Raised when the server encounters an internal error. These errors
    are typically not recoverable by the client and indicate a bug
    or misconfiguration on the server side.
    
    If retry logic is enabled, these errors may be automatically retried.
    """
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
        response_body: Any = None,
    ) -> None:
        """Initialize the exception.
        
        Args:
            message: Human-readable error message.
            status_code: The specific 5xx status code (default: 500).
            details: Additional error details.
            response_body: Raw response body for debugging.
        """
        super().__init__(
            message=message,
            status_code=status_code,
            error_type="server_error",
            details=details,
            response_body=response_body,
        )
