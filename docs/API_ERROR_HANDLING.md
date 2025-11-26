# API Error Handling Guidelines

This document defines the standard error handling patterns for all UES API endpoints.

## HTTP Status Code Standards

Follow REST conventions for HTTP status codes:

### 2xx Success
- **200 OK**: Request succeeded, response contains data
- **201 Created**: Resource successfully created (future use for POST endpoints)
- **204 No Content**: Request succeeded, no response body needed

### 4xx Client Errors
- **400 Bad Request**: Client violated business rules or preconditions
  - Examples: simulation not running, invalid time jump (backwards), negative duration
- **404 Not Found**: Requested resource doesn't exist
  - Examples: no pending events, event ID not found, modality not found
- **422 Unprocessable Entity**: Request is syntactically valid but semantically incorrect
  - Examples: malformed datetime, missing required fields (caught by Pydantic)

### 5xx Server Errors
- **500 Internal Server Error**: Unexpected server-side failure
  - Examples: unhandled exceptions, database errors, internal bugs

## Exception Handling Pattern

All endpoints should follow this consistent pattern:

```python
from fastapi import APIRouter, HTTPException

@router.post("/endpoint")
async def endpoint_handler(request: RequestModel, engine: SimulationEngineDep):
    """Endpoint description."""
    try:
        # Perform operation
        result = engine.some_operation(...)
        
        # Return success response
        return ResponseModel(...)
        
    except ValueError as e:
        # Client errors: validation failures, precondition violations
        raise HTTPException(
            status_code=400,
            detail=str(e),  # Pass through the error message
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

All error responses follow FastAPI's standard format:

```json
{
  "detail": "Human-readable error message"
}
```

For validation errors (422), FastAPI/Pydantic provides structured details:

```json
{
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
```

## Migration Checklist

When updating existing endpoints or creating new ones:

1. ✅ Catch `ValueError` specifically and return **400**
2. ✅ Catch resource not found errors and return **404**
3. ✅ Re-raise `HTTPException` to preserve status codes from nested calls
4. ✅ Catch unexpected `Exception` and return **500**
5. ✅ Use clear, actionable error messages
6. ✅ Write tests for each error condition
7. ✅ Log unexpected errors for debugging

## Related Documentation

- [REST API Design](REST_API.md)
- [API Testing Progress](../API_TESTING_PROGRESS.md)
- [Time Control Routes](../api/routes/time.py)
