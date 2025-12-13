"""Internal HTTP handling utilities for the UES client.

This module provides the low-level HTTP communication layer used by all
sub-clients. It handles:
- Making HTTP requests (sync and async)
- Response parsing and error handling
- Retry logic with exponential backoff
- Connection management

This is an internal module and should not be imported directly by users.
"""

import time
from typing import Any, Literal

import httpx

from client.exceptions import (
    APIError,
    ConflictError,
    ConnectionError,
    NotFoundError,
    ServerError,
    TimeoutError,
    ValidationError,
)


# HTTP methods supported by the client
HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE"]

# Status codes that trigger automatic retry (when retry is enabled)
RETRYABLE_STATUS_CODES = {502, 503, 504}

# Default backoff settings for retry logic
DEFAULT_RETRY_BACKOFF_BASE = 0.5  # seconds
DEFAULT_RETRY_BACKOFF_MAX = 30.0  # seconds


def _parse_error_response(response: httpx.Response) -> tuple[str, str | None, dict | None]:
    """Parse an error response to extract message, type, and details.
    
    Attempts to parse the response body as JSON and extract structured
    error information. Falls back to the raw response text if parsing fails.
    
    Args:
        response: The HTTP response to parse.
    
    Returns:
        A tuple of (message, error_type, details).
    """
    try:
        body = response.json()
        
        # Handle FastAPI's standard error format
        if isinstance(body, dict):
            # Check for "detail" key (FastAPI's default)
            detail = body.get("detail")
            if isinstance(detail, str):
                return detail, body.get("type"), body.get("details")
            elif isinstance(detail, list):
                # Validation errors come as a list
                messages = [
                    f"{err.get('loc', ['unknown'])[-1]}: {err.get('msg', 'invalid')}"
                    for err in detail
                ]
                return "; ".join(messages), "validation_error", {"errors": detail}
            elif isinstance(detail, dict):
                return detail.get("message", str(detail)), detail.get("type"), detail
            
            # Check for "message" key
            if "message" in body:
                return body["message"], body.get("type"), body.get("details")
            
            # Check for "error" key
            if "error" in body:
                return body["error"], body.get("type"), body.get("details")
        
        # Fallback to string representation
        return str(body), None, None
        
    except Exception:
        # If JSON parsing fails, use the response text
        text = response.text.strip()
        if text:
            return text, None, None
        return f"HTTP {response.status_code} error", None, None


def _raise_for_status(response: httpx.Response) -> None:
    """Raise an appropriate exception for error status codes.
    
    Maps HTTP status codes to the appropriate exception types and
    extracts error details from the response body.
    
    Args:
        response: The HTTP response to check.
    
    Raises:
        ValidationError: For HTTP 422 responses.
        NotFoundError: For HTTP 404 responses.
        ConflictError: For HTTP 409 responses.
        ServerError: For HTTP 5xx responses.
        APIError: For other HTTP 4xx responses.
    """
    if response.is_success:
        return
    
    message, error_type, details = _parse_error_response(response)
    status_code = response.status_code
    
    # Try to get raw body for debugging
    try:
        response_body = response.json()
    except Exception:
        response_body = response.text
    
    # Map status codes to exception types
    if status_code == 422:
        raise ValidationError(
            message=message,
            details=details,
            response_body=response_body,
        )
    elif status_code == 404:
        raise NotFoundError(
            message=message,
            details=details,
            response_body=response_body,
        )
    elif status_code == 409:
        raise ConflictError(
            message=message,
            details=details,
            response_body=response_body,
        )
    elif status_code >= 500:
        raise ServerError(
            message=message,
            status_code=status_code,
            details=details,
            response_body=response_body,
        )
    else:
        raise APIError(
            message=message,
            status_code=status_code,
            error_type=error_type,
            details=details,
            response_body=response_body,
        )


def _calculate_backoff(attempt: int, base: float = DEFAULT_RETRY_BACKOFF_BASE) -> float:
    """Calculate exponential backoff delay for retry attempts.
    
    Uses exponential backoff with jitter: base * 2^attempt
    Capped at DEFAULT_RETRY_BACKOFF_MAX seconds.
    
    Args:
        attempt: The retry attempt number (0-indexed).
        base: Base delay in seconds.
    
    Returns:
        The delay in seconds before the next retry.
    """
    delay = base * (2 ** attempt)
    return min(delay, DEFAULT_RETRY_BACKOFF_MAX)


class HTTPClient:
    """Synchronous HTTP client for making API requests.
    
    Wraps httpx.Client with error handling, retry logic, and
    convenience methods for the UES API.
    
    Attributes:
        base_url: The base URL for all API requests.
        timeout: Request timeout in seconds.
        retry_enabled: Whether to retry on transient failures.
        max_retries: Maximum number of retry attempts.
    """
    
    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        retry_enabled: bool = False,
        max_retries: int = 3,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        """Initialize the HTTP client.
        
        Args:
            base_url: The base URL for all API requests.
            timeout: Request timeout in seconds.
            retry_enabled: Whether to retry on transient failures.
            max_retries: Maximum number of retry attempts.
            transport: Custom transport (e.g., ASGITransport for testing).
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retry_enabled = retry_enabled
        self.max_retries = max_retries
        
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            transport=transport,
        )
    
    def close(self) -> None:
        """Close the HTTP client and release resources."""
        self._client.close()
    
    def __enter__(self) -> "HTTPClient":
        """Enter context manager."""
        return self
    
    def __exit__(self, *args: Any) -> None:
        """Exit context manager and close client."""
        self.close()
    
    def request(
        self,
        method: HttpMethod,
        path: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        """Make an HTTP request and return the parsed JSON response.
        
        Handles error responses by raising appropriate exceptions.
        Supports automatic retry on transient failures if enabled.
        
        Args:
            method: The HTTP method (GET, POST, etc.).
            path: The URL path (will be appended to base_url).
            params: Query parameters to include in the URL.
            json: JSON body to send with the request.
        
        Returns:
            The parsed JSON response body, or None for empty responses.
        
        Raises:
            ConnectionError: If the connection fails.
            TimeoutError: If the request times out.
            APIError: If the server returns an error response.
        """
        url = f"{self.base_url}{path}"
        
        # Filter out None values from params
        if params:
            params = {k: v for k, v in params.items() if v is not None}
        
        last_exception: Exception | None = None
        attempts = self.max_retries + 1 if self.retry_enabled else 1
        
        for attempt in range(attempts):
            try:
                response = self._client.request(
                    method=method,
                    url=path,
                    params=params,
                    json=json,
                )
                
                # Check if we should retry on this status code
                if (
                    self.retry_enabled
                    and response.status_code in RETRYABLE_STATUS_CODES
                    and attempt < attempts - 1
                ):
                    delay = _calculate_backoff(attempt)
                    time.sleep(delay)
                    continue
                
                _raise_for_status(response)
                
                # Return parsed JSON or None for empty responses
                if response.content:
                    return response.json()
                return None
                
            except httpx.ConnectError as e:
                last_exception = ConnectionError(
                    message=f"Failed to connect to {url}",
                    url=url,
                    cause=e,
                )
                if not self.retry_enabled or attempt >= attempts - 1:
                    raise last_exception from e
                delay = _calculate_backoff(attempt)
                time.sleep(delay)
                
            except httpx.TimeoutException as e:
                last_exception = TimeoutError(
                    message=f"Request to {url} timed out",
                    timeout=self.timeout,
                    url=url,
                )
                if not self.retry_enabled or attempt >= attempts - 1:
                    raise last_exception from e
                delay = _calculate_backoff(attempt)
                time.sleep(delay)
        
        # Should not reach here, but raise last exception if we do
        if last_exception:
            raise last_exception
        raise RuntimeError("Unexpected error in request retry loop")
    
    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Make a GET request.
        
        Args:
            path: The URL path.
            params: Query parameters.
        
        Returns:
            The parsed JSON response.
        """
        return self.request("GET", path, params=params)
    
    def post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Make a POST request.
        
        Args:
            path: The URL path.
            json: JSON body to send.
            params: Query parameters.
        
        Returns:
            The parsed JSON response.
        """
        return self.request("POST", path, params=params, json=json)
    
    def put(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Make a PUT request.
        
        Args:
            path: The URL path.
            json: JSON body to send.
            params: Query parameters.
        
        Returns:
            The parsed JSON response.
        """
        return self.request("PUT", path, params=params, json=json)
    
    def delete(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Make a DELETE request.
        
        Args:
            path: The URL path.
            params: Query parameters.
        
        Returns:
            The parsed JSON response.
        """
        return self.request("DELETE", path, params=params)


class AsyncHTTPClient:
    """Asynchronous HTTP client for making API requests.
    
    Wraps httpx.AsyncClient with error handling, retry logic, and
    convenience methods for the UES API.
    
    Attributes:
        base_url: The base URL for all API requests.
        timeout: Request timeout in seconds.
        retry_enabled: Whether to retry on transient failures.
        max_retries: Maximum number of retry attempts.
    """
    
    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        retry_enabled: bool = False,
        max_retries: int = 3,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """Initialize the async HTTP client.
        
        Args:
            base_url: The base URL for all API requests.
            timeout: Request timeout in seconds.
            retry_enabled: Whether to retry on transient failures.
            max_retries: Maximum number of retry attempts.
            transport: Custom transport (e.g., ASGITransport for testing).
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retry_enabled = retry_enabled
        self.max_retries = max_retries
        
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            transport=transport,
        )
    
    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        await self._client.aclose()
    
    async def __aenter__(self) -> "AsyncHTTPClient":
        """Enter async context manager."""
        return self
    
    async def __aexit__(self, *args: Any) -> None:
        """Exit async context manager and close client."""
        await self.close()
    
    async def request(
        self,
        method: HttpMethod,
        path: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        """Make an async HTTP request and return the parsed JSON response.
        
        Handles error responses by raising appropriate exceptions.
        Supports automatic retry on transient failures if enabled.
        
        Args:
            method: The HTTP method (GET, POST, etc.).
            path: The URL path (will be appended to base_url).
            params: Query parameters to include in the URL.
            json: JSON body to send with the request.
        
        Returns:
            The parsed JSON response body, or None for empty responses.
        
        Raises:
            ConnectionError: If the connection fails.
            TimeoutError: If the request times out.
            APIError: If the server returns an error response.
        """
        import asyncio
        
        url = f"{self.base_url}{path}"
        
        # Filter out None values from params
        if params:
            params = {k: v for k, v in params.items() if v is not None}
        
        last_exception: Exception | None = None
        attempts = self.max_retries + 1 if self.retry_enabled else 1
        
        for attempt in range(attempts):
            try:
                response = await self._client.request(
                    method=method,
                    url=path,
                    params=params,
                    json=json,
                )
                
                # Check if we should retry on this status code
                if (
                    self.retry_enabled
                    and response.status_code in RETRYABLE_STATUS_CODES
                    and attempt < attempts - 1
                ):
                    delay = _calculate_backoff(attempt)
                    await asyncio.sleep(delay)
                    continue
                
                _raise_for_status(response)
                
                # Return parsed JSON or None for empty responses
                if response.content:
                    return response.json()
                return None
                
            except httpx.ConnectError as e:
                last_exception = ConnectionError(
                    message=f"Failed to connect to {url}",
                    url=url,
                    cause=e,
                )
                if not self.retry_enabled or attempt >= attempts - 1:
                    raise last_exception from e
                delay = _calculate_backoff(attempt)
                await asyncio.sleep(delay)
                
            except httpx.TimeoutException as e:
                last_exception = TimeoutError(
                    message=f"Request to {url} timed out",
                    timeout=self.timeout,
                    url=url,
                )
                if not self.retry_enabled or attempt >= attempts - 1:
                    raise last_exception from e
                delay = _calculate_backoff(attempt)
                await asyncio.sleep(delay)
        
        # Should not reach here, but raise last exception if we do
        if last_exception:
            raise last_exception
        raise RuntimeError("Unexpected error in request retry loop")
    
    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Make an async GET request.
        
        Args:
            path: The URL path.
            params: Query parameters.
        
        Returns:
            The parsed JSON response.
        """
        return await self.request("GET", path, params=params)
    
    async def post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Make an async POST request.
        
        Args:
            path: The URL path.
            json: JSON body to send.
            params: Query parameters.
        
        Returns:
            The parsed JSON response.
        """
        return await self.request("POST", path, params=params, json=json)
    
    async def put(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Make an async PUT request.
        
        Args:
            path: The URL path.
            json: JSON body to send.
            params: Query parameters.
        
        Returns:
            The parsed JSON response.
        """
        return await self.request("PUT", path, params=params, json=json)
    
    async def delete(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Make an async DELETE request.
        
        Args:
            path: The URL path.
            params: Query parameters.
        
        Returns:
            The parsed JSON response.
        """
        return await self.request("DELETE", path, params=params)
