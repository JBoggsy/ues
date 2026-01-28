"""Access logging middleware for the UES API.

This middleware logs all API requests to an in-memory access log, capturing:
- Request method and path
- API key information (if authenticated)
- Response status code
- Request duration
- Client information (IP, User-Agent)

The middleware integrates with the authentication system to capture key info
that has been set on request.state by the auth dependencies.

Example usage:
    from fastapi import FastAPI
    from ues.api.middleware import AccessLoggingMiddleware, initialize_access_log
    
    app = FastAPI()
    
    # Initialize the access log (typically in lifespan)
    initialize_access_log(max_entries=10000)
    
    # Add the middleware (should be after CORS for proper timing)
    app.add_middleware(AccessLoggingMiddleware)
"""

import logging
import time
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ues.models.access_log import AccessLog, AccessLogEntry


logger = logging.getLogger(__name__)


# =============================================================================
# Global Access Log Instance
# =============================================================================


_access_log: Optional[AccessLog] = None


def get_access_log() -> AccessLog:
    """Get the global access log instance.
    
    Returns:
        The global AccessLog instance.
    
    Raises:
        RuntimeError: If the access log hasn't been initialized.
    """
    global _access_log
    
    if _access_log is None:
        raise RuntimeError(
            "Access log not initialized. Call initialize_access_log() first."
        )
    
    return _access_log


def initialize_access_log(max_entries: int = 10000) -> AccessLog:
    """Initialize the global access log.
    
    This should be called once when the FastAPI app starts up, before
    the middleware processes any requests.
    
    Args:
        max_entries: Maximum number of entries to retain (default: 10000).
    
    Returns:
        The initialized AccessLog instance.
    """
    global _access_log
    
    _access_log = AccessLog(max_entries=max_entries)
    logger.info(f"Access log initialized with max_entries={max_entries}")
    
    return _access_log


def shutdown_access_log() -> None:
    """Shut down the global access log.
    
    This should be called when the FastAPI app shuts down.
    Clears all entries and releases the log instance.
    """
    global _access_log
    
    if _access_log is not None:
        entry_count = _access_log.count
        _access_log.clear()
        logger.info(f"Access log shutdown, cleared {entry_count} entries")
    
    _access_log = None


# =============================================================================
# Paths to Skip Logging
# =============================================================================


# Paths that should not be logged (health checks, docs, etc.)
# These are typically high-frequency or non-authenticated endpoints
SKIP_PATHS = frozenset({
    "/",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    # WebSocket connections are logged separately if needed
    "/ws",
})

# Path prefixes to skip (e.g., static files if any)
SKIP_PATH_PREFIXES = (
    "/docs/",  # FastAPI docs assets
    "/redoc/",  # ReDoc assets
)


def should_skip_logging(path: str) -> bool:
    """Determine if a request path should skip access logging.
    
    Args:
        path: The request path.
    
    Returns:
        True if the path should be skipped, False otherwise.
    """
    if path in SKIP_PATHS:
        return True
    
    for prefix in SKIP_PATH_PREFIXES:
        if path.startswith(prefix):
            return True
    
    return False


# =============================================================================
# Access Logging Middleware
# =============================================================================


class AccessLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs all API requests to the access log.
    
    This middleware:
    1. Records the request start time
    2. Passes the request to the next handler
    3. Captures the response status code
    4. Extracts API key info from request.state (set by auth dependencies)
    5. Creates an AccessLogEntry and adds it to the global access log
    
    The middleware should be added after CORS middleware so that CORS
    preflight requests are handled properly.
    
    Attributes:
        skip_paths: Set of exact paths to skip logging.
    
    Example:
        app = FastAPI()
        app.add_middleware(AccessLoggingMiddleware)
        
        # Then in routes, the auth dependency sets request.state:
        # request.state.api_key_id = key.key_id
        # request.state.api_key_name = key.name
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process a request and log it to the access log.
        
        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or route handler.
        
        Returns:
            The HTTP response from the handler.
        """
        # Check if we should skip logging this path
        path = request.url.path
        if should_skip_logging(path):
            return await call_next(request)
        
        # Record start time
        start_time = time.perf_counter()
        
        # Initialize response variable
        response: Optional[Response] = None
        error_detail: Optional[str] = None
        
        try:
            # Call the next handler
            response = await call_next(request)
            return response
        
        except Exception as exc:
            # Capture exception details for logging
            error_detail = str(exc)
            raise
        
        finally:
            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            # Get API key info from request.state (set by auth dependency)
            key_id = getattr(request.state, "api_key_id", None)
            key_name = getattr(request.state, "api_key_name", None)
            
            # Get client information
            client_ip = None
            if request.client:
                client_ip = request.client.host
            
            user_agent = request.headers.get("user-agent")
            
            # Determine status code
            status_code = 500  # Default to server error if no response
            if response is not None:
                status_code = response.status_code
            
            # Capture error detail for failed responses
            if status_code >= 400 and error_detail is None:
                # Try to get error detail from response headers or body
                # Note: We can't easily read response body here without issues
                error_detail = None  # Would need response body streaming
            
            # Create and log the entry
            try:
                access_log = get_access_log()
                
                entry = AccessLogEntry(
                    method=request.method,
                    path=path,
                    key_id=key_id,
                    key_name=key_name,
                    status_code=status_code,
                    duration_ms=duration_ms,
                    client_ip=client_ip,
                    user_agent=user_agent,
                    error_detail=error_detail,
                )
                
                access_log.log(entry)
                
            except RuntimeError:
                # Access log not initialized - this shouldn't happen in normal
                # operation, but we don't want to fail requests over logging
                logger.warning("Access log not initialized, skipping request logging")
            except Exception as log_exc:
                # Don't let logging failures affect request processing
                logger.exception(f"Failed to log access: {log_exc}")
