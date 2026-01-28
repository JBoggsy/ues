"""Access log models for API request logging.

This module provides models for tracking and querying API access logs.
All requests to authenticated endpoints are logged with details about
the request, the API key used, response status, and timing information.

Example usage:
    # Create an entry
    entry = AccessLogEntry(
        method="GET",
        path="/email/state",
        key_id="ues_abc123",
        key_name="Email Bot",
        status_code=200,
        duration_ms=15.3,
    )
    
    # Add to the log
    access_log = AccessLog(max_entries=10000)
    access_log.log(entry)
    
    # Query logs
    recent = access_log.query(since=datetime.now() - timedelta(hours=1))
    key_logs = access_log.query(key_id="ues_abc123", limit=50)
"""

from collections import deque
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def generate_log_id() -> str:
    """Generate a unique log entry identifier.
    
    Returns:
        A UUID string for the log entry.
    """
    return str(uuid4())


class AccessLogEntry(BaseModel):
    """A single API access log entry.
    
    Records details about an API request including who made it (key),
    what they accessed (method, path), the outcome (status_code), and
    performance metrics (duration_ms).
    
    Attributes:
        log_id: Unique identifier for this log entry.
        timestamp: When the request was received (UTC).
        method: HTTP method (GET, POST, DELETE, etc.).
        path: Request path (e.g., /email/state).
        key_id: The API key ID used for the request, or None for unauthenticated.
        key_name: The human-readable name of the API key, or None.
        status_code: HTTP response status code.
        duration_ms: Request processing time in milliseconds.
        client_ip: Client IP address, if available.
        user_agent: Client User-Agent header, if provided.
        error_detail: Error message for failed requests (4xx/5xx).
    
    Example:
        entry = AccessLogEntry(
            method="POST",
            path="/email/send",
            key_id="ues_abc123",
            key_name="Email Bot",
            status_code=200,
            duration_ms=45.2,
            client_ip="192.168.1.100",
        )
    """
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        frozen=False,  # Allow modification after creation (for timestamps)
    )
    
    log_id: str = Field(
        default_factory=generate_log_id,
        description="Unique identifier for this log entry"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the request was received (UTC)"
    )
    method: str = Field(
        description="HTTP method (GET, POST, DELETE, etc.)"
    )
    path: str = Field(
        description="Request path (e.g., /email/state)"
    )
    key_id: Optional[str] = Field(
        default=None,
        description="The API key ID used for the request, or None for unauthenticated"
    )
    key_name: Optional[str] = Field(
        default=None,
        description="The human-readable name of the API key, or None"
    )
    status_code: int = Field(
        description="HTTP response status code"
    )
    duration_ms: float = Field(
        ge=0,
        description="Request processing time in milliseconds"
    )
    client_ip: Optional[str] = Field(
        default=None,
        description="Client IP address, if available"
    )
    user_agent: Optional[str] = Field(
        default=None,
        description="Client User-Agent header, if provided"
    )
    error_detail: Optional[str] = Field(
        default=None,
        description="Error message for failed requests (4xx/5xx)"
    )
    
    @property
    def is_success(self) -> bool:
        """Check if the request was successful (2xx status)."""
        return 200 <= self.status_code < 300
    
    @property
    def is_error(self) -> bool:
        """Check if the request resulted in an error (4xx/5xx status)."""
        return self.status_code >= 400


class AccessLog:
    """In-memory access log with configurable size limit.
    
    Stores access log entries in memory using a deque with a maximum size.
    When the limit is reached, oldest entries are automatically removed
    as new entries are added.
    
    The log supports querying by various filters and clearing all entries.
    
    Thread Safety:
        The current implementation is NOT thread-safe. For production use
        with multiple workers, consider using a thread-safe data structure
        or shared storage backend.
    
    Attributes:
        max_entries: Maximum number of entries to retain.
    
    Example:
        log = AccessLog(max_entries=10000)
        
        # Log a request
        log.log(AccessLogEntry(
            method="GET",
            path="/email/state",
            key_id="ues_abc123",
            key_name="Bot",
            status_code=200,
            duration_ms=10.5,
        ))
        
        # Query logs
        entries = log.query(key_id="ues_abc123", limit=100)
        
        # Get statistics
        print(f"Total entries: {log.count}")
        
        # Clear logs
        cleared = log.clear()
    """
    
    def __init__(self, max_entries: int = 10000):
        """Initialize an access log with a maximum entry limit.
        
        Args:
            max_entries: Maximum number of entries to retain (default: 10000).
                When this limit is reached, oldest entries are removed.
        
        Raises:
            ValueError: If max_entries is less than 1.
        """
        if max_entries < 1:
            raise ValueError("max_entries must be at least 1")
        
        self._max_entries = max_entries
        self._entries: deque[AccessLogEntry] = deque(maxlen=max_entries)
    
    @property
    def max_entries(self) -> int:
        """Get the maximum number of entries this log can hold."""
        return self._max_entries
    
    @property
    def count(self) -> int:
        """Get the current number of entries in the log."""
        return len(self._entries)
    
    @property
    def is_full(self) -> bool:
        """Check if the log is at its maximum capacity."""
        return len(self._entries) >= self._max_entries
    
    def log(self, entry: AccessLogEntry) -> None:
        """Add an entry to the log.
        
        If the log is at capacity, the oldest entry is removed to make room.
        
        Args:
            entry: The AccessLogEntry to add.
        """
        self._entries.append(entry)
    
    def query(
        self,
        key_id: Optional[str] = None,
        key_name: Optional[str] = None,
        path_prefix: Optional[str] = None,
        method: Optional[str] = None,
        status_code: Optional[int] = None,
        min_status_code: Optional[int] = None,
        max_status_code: Optional[int] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
        errors_only: bool = False,
    ) -> list[AccessLogEntry]:
        """Query log entries with filters.
        
        All filter parameters are optional and combined with AND logic.
        Results are returned in reverse chronological order (newest first).
        
        Args:
            key_id: Filter by exact API key ID.
            key_name: Filter by exact API key name.
            path_prefix: Filter by path prefix (e.g., "/email" matches "/email/state").
            method: Filter by HTTP method (case-insensitive).
            status_code: Filter by exact status code.
            min_status_code: Filter by minimum status code (inclusive).
            max_status_code: Filter by maximum status code (inclusive).
            since: Filter for entries on or after this timestamp (inclusive).
            until: Filter for entries before this timestamp (exclusive).
            limit: Maximum number of entries to return (default: 100).
            offset: Number of matching entries to skip (for pagination).
            errors_only: If True, only return error entries (4xx/5xx).
        
        Returns:
            List of matching AccessLogEntry objects, newest first.
        
        Example:
            # Get recent email endpoint errors
            errors = log.query(
                path_prefix="/email",
                errors_only=True,
                since=datetime.now(timezone.utc) - timedelta(hours=1),
                limit=50,
            )
        """
        if limit < 0:
            raise ValueError("limit must be non-negative")
        if offset < 0:
            raise ValueError("offset must be non-negative")
        
        # Normalize method to uppercase
        if method is not None:
            method = method.upper()
        
        # Filter entries (iterate in reverse for newest-first)
        results: list[AccessLogEntry] = []
        skipped = 0
        
        for entry in reversed(self._entries):
            # Apply filters
            if key_id is not None and entry.key_id != key_id:
                continue
            if key_name is not None and entry.key_name != key_name:
                continue
            if path_prefix is not None and not entry.path.startswith(path_prefix):
                continue
            if method is not None and entry.method.upper() != method:
                continue
            if status_code is not None and entry.status_code != status_code:
                continue
            if min_status_code is not None and entry.status_code < min_status_code:
                continue
            if max_status_code is not None and entry.status_code > max_status_code:
                continue
            if since is not None and entry.timestamp < since:
                continue
            if until is not None and entry.timestamp >= until:
                continue
            if errors_only and not entry.is_error:
                continue
            
            # Handle offset (pagination)
            if skipped < offset:
                skipped += 1
                continue
            
            results.append(entry)
            
            # Stop if we've reached the limit
            if len(results) >= limit:
                break
        
        return results
    
    def get_by_id(self, log_id: str) -> Optional[AccessLogEntry]:
        """Get a log entry by its ID.
        
        Args:
            log_id: The unique identifier of the log entry.
        
        Returns:
            The AccessLogEntry if found, None otherwise.
        """
        for entry in self._entries:
            if entry.log_id == log_id:
                return entry
        return None
    
    def clear(self) -> int:
        """Clear all entries from the log.
        
        Returns:
            The number of entries that were cleared.
        """
        count = len(self._entries)
        self._entries.clear()
        return count
    
    def get_statistics(self) -> dict:
        """Get aggregate statistics about the log.
        
        Returns:
            Dictionary with statistics including:
            - total_entries: Total number of entries
            - success_count: Number of 2xx responses
            - client_error_count: Number of 4xx responses
            - server_error_count: Number of 5xx responses
            - unique_keys: Number of distinct API keys
            - earliest_timestamp: Timestamp of oldest entry (if any)
            - latest_timestamp: Timestamp of newest entry (if any)
        """
        if not self._entries:
            return {
                "total_entries": 0,
                "success_count": 0,
                "client_error_count": 0,
                "server_error_count": 0,
                "unique_keys": 0,
                "earliest_timestamp": None,
                "latest_timestamp": None,
            }
        
        success_count = 0
        client_error_count = 0
        server_error_count = 0
        unique_keys: set[Optional[str]] = set()
        
        for entry in self._entries:
            if 200 <= entry.status_code < 300:
                success_count += 1
            elif 400 <= entry.status_code < 500:
                client_error_count += 1
            elif entry.status_code >= 500:
                server_error_count += 1
            
            unique_keys.add(entry.key_id)
        
        # Get timestamps (entries are in chronological order)
        earliest = self._entries[0].timestamp
        latest = self._entries[-1].timestamp
        
        return {
            "total_entries": len(self._entries),
            "success_count": success_count,
            "client_error_count": client_error_count,
            "server_error_count": server_error_count,
            "unique_keys": len(unique_keys),
            "earliest_timestamp": earliest,
            "latest_timestamp": latest,
        }
