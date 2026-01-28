"""Middleware package for the UES API.

This package contains middleware components that process requests/responses
globally, before they reach route handlers.

Available middleware:
- AccessLoggingMiddleware: Logs all API requests with timing and auth info
"""

from ues.api.middleware.access_logging import (
    AccessLoggingMiddleware,
    get_access_log,
    initialize_access_log,
    shutdown_access_log,
)


__all__ = [
    "AccessLoggingMiddleware",
    "get_access_log",
    "initialize_access_log",
    "shutdown_access_log",
]
