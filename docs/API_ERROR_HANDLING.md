# API Error Handling Guidelines

This document defines the standard error handling patterns for all UES API endpoints.

## HTTP Status Code Standards

Follow REST conventions for HTTP status codes:

### 2xx Success
- **200 OK**: Request succeeded, response contains data
- **201 Created**: Resource successfully created (future use for POST endpoints)
- **204 No Content**: Request succeeded, no response body needed

### 4xx Client Errors
- **400 Bad Request**: Client violated business rules or preconditions (AFTER Pydantic validation passes)
  - Examples: simulation not running, invalid time jump (backwards), event already executed
- **404 Not Found**: Requested resource doesn't exist
  - Examples: no pending events, event ID not found, modality not found
- **409 Conflict**: Request conflicts with the current state of the resource
  - Examples: simulation already running, cannot delete already-executed event
- **422 Unprocessable Entity**: Request failed Pydantic/structural validation
  - Examples: malformed datetime, missing required fields, invalid field types, out-of-range values

### 5xx Server Errors
- **500 Internal Server Error**: Unexpected server-side failure
  - Examples: unhandled exceptions, database errors, internal bugs

## Distinguishing 400 vs 422

This is an important distinction:

| Status | When to Use | Example |
|--------|-------------|---------|
| **422** | Pydantic validation fails (before business logic runs) | Missing field, wrong type, constraint violation (e.g., latitude > 90) |
| **400** | Business logic rejects valid data (after Pydantic passes) | Simulation not running, time travel backwards, paused state |
| **409** | State conflict prevents operation | Already running, already executed |

**Rule of thumb**: If Pydantic raises `ValidationError`, return 422. If your code raises `ValueError` after validation, return 400.

## Exception Handling Pattern

All endpoints should follow this consistent pattern:

```python
from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

@router.post("/endpoint")
async def endpoint_handler(request: RequestModel, engine: SimulationEngineDep):
    """Endpoint description."""
    try:
        # Perform operation (may create Pydantic models internally)
        result = engine.some_operation(...)
        
        # Return success response
        return ResponseModel(...)
        
    except ValidationError as e:
        # Pydantic validation failed - return 422
        raise HTTPException(
            status_code=422,
            detail=f"Validation error: {str(e)}",
        )
    except ValueError as e:
        # Business rule violations (after Pydantic validation passes)
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except KeyError as e:
        # Not found errors: missing resources
        raise HTTPException(
            status_code=404,
            detail=f"Resource not found: {str(e)}",
        )
    except HTTPException:
        # Re-raise HTTPExceptions (from nested calls)
        raise
    except Exception as e:
        # Unexpected server errors
        raise HTTPException(
            status_code=500,
            detail=f"Failed to perform operation: {str(e)}",
        )
```

**Note**: For state conflicts (e.g., simulation already running), use 409:
```python
if engine.is_running:
    raise HTTPException(status_code=409, detail="Simulation is already running")
```

## Common Error Scenarios

### ValueError → 400 Bad Request
Used when the client violates business rules or preconditions:

```python
# Simulation not running
if not self.is_running:
    raise ValueError("Cannot advance time: simulation is not running")

# Invalid time range
if new_time < current_time:
    raise ValueError("Cannot travel backwards in time")

# Negative duration
if delta <= timedelta(0):
    raise ValueError(f"Time delta must be positive, got {delta}")
```

### KeyError / Custom Not Found → 404 Not Found
Used when a requested resource doesn't exist:

```python
# No events in queue
if not pending_events:
    raise HTTPException(
        status_code=404,
        detail="No pending events in queue"
    )

# Event ID not found
try:
    event = event_queue.get_event(event_id)
except KeyError:
    raise HTTPException(
        status_code=404,
        detail=f"Event {event_id} not found"
    )
```

### Unexpected Exceptions → 500 Internal Server Error
Used for bugs, database errors, or other unexpected failures:

```python
except Exception as e:
    # Log for debugging
    logger.error(f"Unexpected error in endpoint: {str(e)}", exc_info=True)
    
    raise HTTPException(
        status_code=500,
        detail=f"Internal server error: {str(e)}"
    )
```

## Error Response Format

### Standard Format

Most error responses follow FastAPI's standard format:

```json
{
  "detail": "Human-readable error message"
}
```

### Validation Errors (422)

For validation errors, FastAPI/Pydantic provides structured details:

```json
{
  "error": "Validation Error",
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "seconds"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

### Extended Format (Modality Not Found)

The `ModalityNotFoundError` returns additional helpful context:

```json
{
  "error": "Modality Not Found",
  "detail": "The modality 'invalid' does not exist",
  "requested_modality": "invalid",
  "available_modalities": ["location", "time", "weather", "chat", "email", "calendar", "sms"]
}
```

This extended format helps clients understand what modalities are available.

## Examples from Time Control Routes

### Consistent Error Handling (✅ Correct)

```python
@router.post("/advance")
async def advance_time(request: AdvanceTimeRequest, engine: SimulationEngineDep):
    try:
        engine.advance_time(delta=timedelta(seconds=request.seconds))
        time_state = engine.environment.time_state
        return TimeStateResponse(...)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to advance time: {str(e)}")
```

### Testing Error Handling

```python
def test_simulation_not_running_returns_400(client):
    """Test that operations fail with 400 when simulation not running."""
    response = client.post("/simulator/time/advance", json={"seconds": 3600})
    
    assert response.status_code == 400
    assert "not running" in response.json()["detail"].lower()

def test_invalid_time_range_returns_400(client):
    """Test that backward time travel returns 400."""
    response = client.post(
        "/simulator/time/set",
        json={"target_time": "2020-01-01T00:00:00Z"}
    )
    
    assert response.status_code == 400
    assert "backwards" in response.json()["detail"].lower()

def test_missing_resource_returns_404(client):
    """Test that missing events return 404."""
    response = client.post("/simulator/time/skip-to-next")
    
    assert response.status_code == 404
    assert "no pending events" in response.json()["detail"].lower()

def test_validation_error_returns_422(client):
    """Test that Pydantic validation errors return 422."""
    response = client.post(
        "/location/update",
        json={"latitude": 200, "longitude": 0}  # Invalid latitude
    )
    
    assert response.status_code == 422
```

## Migration Checklist

When updating existing endpoints or creating new ones:

1. ✅ Catch `ValidationError` (Pydantic) and return **422**
2. ✅ Catch `ValueError` (business rules) and return **400**
3. ✅ Use **409** for state conflicts (already running, already executed)
4. ✅ Catch resource not found errors and return **404**
5. ✅ Re-raise `HTTPException` to preserve status codes from nested calls
6. ✅ Catch unexpected `Exception` and return **500**
7. ✅ Use clear, actionable error messages
8. ✅ Write tests for each error condition
9. ✅ Log unexpected errors for debugging

## Related Documentation

- [REST API Design](REST_API.md)
- [API Testing Progress](../tests/progress/API_TESTING_PROGRESS.md)
- [Time Control Routes](../api/routes/time.py)
