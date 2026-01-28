"""Access log query endpoints.

Provides REST API endpoints for querying and managing access logs.
These endpoints require authentication and appropriate permissions.

All endpoints are protected by API key authentication. The admin key created
at server startup has full access to all access log operations.

Endpoints:
    GET /access-logs - Query access log entries with filters
    GET /access-logs/stats - Get aggregate statistics
    POST /access-logs/clear - Clear all access log entries
"""

from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ues.api.auth import Permissions, require_permission
from ues.api.middleware import get_access_log
from ues.models.access_log import AccessLogEntry
from ues.models.api_key import APIKey


router = APIRouter(
    prefix="/access-logs",
    tags=["access-logs"],
)


# ============================================================================
# Response Models
# ============================================================================


class AccessLogEntryResponse(BaseModel):
    """Response model for a single access log entry.
    
    Attributes:
        log_id: Unique identifier for this log entry.
        timestamp: When the request was received (UTC).
        method: HTTP method (GET, POST, DELETE, etc.).
        path: Request path (e.g., /email/state).
        key_id: The API key ID used for the request, or null for unauthenticated.
        key_name: The human-readable name of the API key, or null.
        status_code: HTTP response status code.
        duration_ms: Request processing time in milliseconds.
        client_ip: Client IP address, if available.
        user_agent: Client User-Agent header, if provided.
        error_detail: Error message for failed requests (4xx/5xx).
        is_success: Whether the request was successful (2xx status).
        is_error: Whether the request resulted in an error (4xx/5xx status).
    """
    
    log_id: str = Field(description="Unique identifier for this log entry")
    timestamp: datetime = Field(description="When the request was received (UTC)")
    method: str = Field(description="HTTP method (GET, POST, DELETE, etc.)")
    path: str = Field(description="Request path (e.g., /email/state)")
    key_id: Optional[str] = Field(description="The API key ID used for the request")
    key_name: Optional[str] = Field(description="The human-readable name of the API key")
    status_code: int = Field(description="HTTP response status code")
    duration_ms: float = Field(description="Request processing time in milliseconds")
    client_ip: Optional[str] = Field(description="Client IP address")
    user_agent: Optional[str] = Field(description="Client User-Agent header")
    error_detail: Optional[str] = Field(description="Error message for failed requests")
    is_success: bool = Field(description="Whether the request was successful (2xx)")
    is_error: bool = Field(description="Whether the request resulted in an error (4xx/5xx)")
    
    @classmethod
    def from_entry(cls, entry: AccessLogEntry) -> "AccessLogEntryResponse":
        """Create a response from an AccessLogEntry.
        
        Args:
            entry: The AccessLogEntry to convert.
        
        Returns:
            An AccessLogEntryResponse instance.
        """
        return cls(
            log_id=entry.log_id,
            timestamp=entry.timestamp,
            method=entry.method,
            path=entry.path,
            key_id=entry.key_id,
            key_name=entry.key_name,
            status_code=entry.status_code,
            duration_ms=entry.duration_ms,
            client_ip=entry.client_ip,
            user_agent=entry.user_agent,
            error_detail=entry.error_detail,
            is_success=entry.is_success,
            is_error=entry.is_error,
        )


class QueryAccessLogsResponse(BaseModel):
    """Response model for querying access logs.
    
    Attributes:
        entries: List of matching access log entries.
        count: Number of entries returned.
        total_in_log: Total number of entries in the log (before filtering).
        limit: The limit that was applied.
        offset: The offset that was applied.
        has_more: Whether there are more entries matching the query.
    """
    
    entries: list[AccessLogEntryResponse] = Field(
        description="List of matching access log entries"
    )
    count: int = Field(description="Number of entries returned")
    total_in_log: int = Field(description="Total number of entries in the log")
    limit: int = Field(description="The limit that was applied")
    offset: int = Field(description="The offset that was applied")
    has_more: bool = Field(description="Whether there are more entries matching the query")


class AccessLogStatisticsResponse(BaseModel):
    """Response model for access log statistics.
    
    Attributes:
        total_entries: Total number of entries in the log.
        max_entries: Maximum number of entries the log can hold.
        success_count: Number of 2xx responses.
        client_error_count: Number of 4xx responses.
        server_error_count: Number of 5xx responses.
        unique_keys: Number of distinct API keys in the log.
        earliest_timestamp: Timestamp of oldest entry (if any).
        latest_timestamp: Timestamp of newest entry (if any).
        is_full: Whether the log is at maximum capacity.
    """
    
    total_entries: int = Field(description="Total number of entries in the log")
    max_entries: int = Field(description="Maximum number of entries the log can hold")
    success_count: int = Field(description="Number of 2xx responses")
    client_error_count: int = Field(description="Number of 4xx responses")
    server_error_count: int = Field(description="Number of 5xx responses")
    unique_keys: int = Field(description="Number of distinct API keys in the log")
    earliest_timestamp: Optional[datetime] = Field(
        description="Timestamp of oldest entry (if any)"
    )
    latest_timestamp: Optional[datetime] = Field(
        description="Timestamp of newest entry (if any)"
    )
    is_full: bool = Field(description="Whether the log is at maximum capacity")


class ClearAccessLogsResponse(BaseModel):
    """Response model for clearing access logs.
    
    Attributes:
        cleared_count: Number of entries that were cleared.
        message: Human-readable success message.
    """
    
    cleared_count: int = Field(description="Number of entries that were cleared")
    message: str = Field(description="Human-readable success message")


# ============================================================================
# Route Handlers
# ============================================================================


@router.get(
    "",
    response_model=QueryAccessLogsResponse,
    summary="Query access logs",
    description="""
Query access log entries with optional filters.

All filters are optional and combined with AND logic. Results are returned
in reverse chronological order (newest first).

**Pagination**: Use `limit` and `offset` for pagination. The response includes
`has_more` to indicate if more entries match the query.

**Filtering**:
- `key_id`: Filter by exact API key ID
- `key_name`: Filter by exact API key name
- `path_prefix`: Filter by path prefix (e.g., "/email" matches "/email/state")
- `method`: Filter by HTTP method (case-insensitive)
- `status_code`: Filter by exact status code
- `min_status_code` / `max_status_code`: Filter by status code range
- `since` / `until`: Filter by timestamp range
- `errors_only`: Only return error responses (4xx/5xx)
""",
)
async def query_access_logs(
    _: Annotated[APIKey, Depends(require_permission(Permissions.LOGS_READ))],
    key_id: Optional[str] = Query(None, description="Filter by exact API key ID"),
    key_name: Optional[str] = Query(None, description="Filter by exact API key name"),
    path_prefix: Optional[str] = Query(
        None, description="Filter by path prefix (e.g., '/email')"
    ),
    method: Optional[str] = Query(
        None, description="Filter by HTTP method (case-insensitive)"
    ),
    status_code: Optional[int] = Query(None, description="Filter by exact status code"),
    min_status_code: Optional[int] = Query(
        None, description="Filter by minimum status code (inclusive)"
    ),
    max_status_code: Optional[int] = Query(
        None, description="Filter by maximum status code (inclusive)"
    ),
    since: Optional[datetime] = Query(
        None, description="Filter for entries on or after this timestamp"
    ),
    until: Optional[datetime] = Query(
        None, description="Filter for entries before this timestamp"
    ),
    errors_only: bool = Query(False, description="Only return error responses (4xx/5xx)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum entries to return"),
    offset: int = Query(0, ge=0, description="Number of entries to skip"),
) -> QueryAccessLogsResponse:
    """Query access log entries with filters.
    
    Returns a paginated list of access log entries matching the specified
    filters, ordered by timestamp (newest first).
    """
    access_log = get_access_log()
    
    # Query with limit + 1 to detect if there are more results
    entries = access_log.query(
        key_id=key_id,
        key_name=key_name,
        path_prefix=path_prefix,
        method=method,
        status_code=status_code,
        min_status_code=min_status_code,
        max_status_code=max_status_code,
        since=since,
        until=until,
        errors_only=errors_only,
        limit=limit + 1,  # Fetch one extra to check for more
        offset=offset,
    )
    
    # Check if there are more results
    has_more = len(entries) > limit
    if has_more:
        entries = entries[:limit]  # Remove the extra entry
    
    return QueryAccessLogsResponse(
        entries=[AccessLogEntryResponse.from_entry(e) for e in entries],
        count=len(entries),
        total_in_log=access_log.count,
        limit=limit,
        offset=offset,
        has_more=has_more,
    )


@router.get(
    "/stats",
    response_model=AccessLogStatisticsResponse,
    summary="Get access log statistics",
    description="""
Get aggregate statistics about the access log.

Returns counts of success/error responses, unique API keys, timestamp
range, and capacity information.
""",
)
async def get_access_log_statistics(
    _: Annotated[APIKey, Depends(require_permission(Permissions.LOGS_READ))],
) -> AccessLogStatisticsResponse:
    """Get aggregate statistics about the access log."""
    access_log = get_access_log()
    stats = access_log.get_statistics()
    
    return AccessLogStatisticsResponse(
        total_entries=stats["total_entries"],
        max_entries=access_log.max_entries,
        success_count=stats["success_count"],
        client_error_count=stats["client_error_count"],
        server_error_count=stats["server_error_count"],
        unique_keys=stats["unique_keys"],
        earliest_timestamp=stats["earliest_timestamp"],
        latest_timestamp=stats["latest_timestamp"],
        is_full=access_log.is_full,
    )


@router.post(
    "/clear",
    response_model=ClearAccessLogsResponse,
    summary="Clear all access logs",
    description="""
Clear all entries from the access log.

**Warning**: This operation is irreversible. All log entries will be permanently deleted.

Returns the number of entries that were cleared.
""",
)
async def clear_access_logs(
    _: Annotated[APIKey, Depends(require_permission(Permissions.LOGS_CLEAR))],
) -> ClearAccessLogsResponse:
    """Clear all access log entries.
    
    Permanently removes all entries from the access log. This operation
    cannot be undone.
    """
    access_log = get_access_log()
    cleared_count = access_log.clear()
    
    return ClearAccessLogsResponse(
        cleared_count=cleared_count,
        message=f"Successfully cleared {cleared_count} access log entries",
    )
