# Modality Route Pattern Documentation

## Overview

This document defines the standard pattern for implementing modality-specific REST API routes in UES. All modality routes should follow this pattern to ensure consistency, type safety, and maintainability.

## Design Principles

1. **Type Safety**: Use Pydantic models for all requests and responses
2. **Consistency**: All modalities follow the same endpoint structure
3. **Clarity**: Action-specific endpoints are more intuitive than generic submission
4. **Documentation**: FastAPI auto-generates OpenAPI docs from typed models
5. **Reusability**: Leverage shared base classes and utilities

## Standard Endpoint Pattern

Every modality should implement these three categories of endpoints:

### 1. State Endpoint
`GET /{modality}/state`

Returns the complete current state of the modality.

**Purpose**: Provide a snapshot of all modality data at the current simulator time.

**Response**: Uses `ModalityStateResponse[StateT]` with modality-specific state type.

**Example**: `GET /email/state` returns all emails across all folders.

### 2. Query Endpoint (Optional)
`POST /{modality}/query`

Queries modality data with filters, sorting, and pagination.

**Purpose**: Allow filtered access to large datasets without retrieving full state.

**Request**: Modality-specific query model with filter parameters.

**Response**: Uses `ModalityQueryResponse[ResultsT]` with paginated results.

**Example**: `POST /email/query` with `{"folder": "inbox", "is_read": false}` returns unread inbox emails.

### 3. Action Endpoints
`POST /{modality}/{action}`

Performs a specific action on the modality (e.g., send, receive, update, delete).

**Purpose**: Execute well-defined operations with type-safe parameters.

**Request**: Action-specific request model.

**Response**: Uses `ModalityActionResponse` or action-specific response model.

**Example**: `POST /email/send` creates and sends a new email.

## Shared Models and Utilities

### Base Response Models (from `api/models.py`)

```python
# Generic state response
class ModalityStateResponse(BaseModel, Generic[StateT]):
    modality_type: str
    current_time: datetime
    state: StateT

# Standard action response
class ModalityActionResponse(BaseModel):
    event_id: str
    scheduled_time: datetime
    status: str
    message: str
    modality: str

# Generic query response
class ModalityQueryResponse(BaseModel, Generic[StateT]):
    modality_type: str
    query: dict[str, Any]
    results: StateT
    total_count: int
    returned_count: int
```

### Common Request Models (from `api/models.py`)

```python
# Pagination
class PaginationParams(BaseModel):
    limit: int | None = Field(None, ge=1, le=1000)
    offset: int = Field(0, ge=0)

# Sorting
class SortParams(BaseModel):
    sort_by: str | None = None
    sort_order: str | None = Field(None, pattern="^(asc|desc)$")

# Date filtering
class DateRangeParams(BaseModel):
    start_date: datetime | None = None
    end_date: datetime | None = None

# Text search
class TextSearchParams(BaseModel):
    search_text: str | None = None
    search_fields: list[str] | None = None

# Marking items (read/unread, starred, etc.)
class MarkItemsRequest(BaseModel):
    item_ids: list[str] = Field(..., min_length=1)
    mark_value: bool

# Deleting items
class DeleteItemsRequest(BaseModel):
    item_ids: list[str] = Field(..., min_length=1)
    permanent: bool = False
```

### Utility Functions (from `api/utils.py`)

```python
# Event creation
create_immediate_event(engine, modality, data, priority=100) -> SimulatorEvent

# Validation
validate_modality_exists(engine, modality) -> None
get_modality_state(engine, modality) -> Any
get_current_simulator_time(engine) -> datetime

# Query helpers
apply_pagination(items, limit, offset) -> tuple[list, int, int]
apply_sort(items, sort_by, sort_order) -> list
filter_by_date_range(items, date_field, start_date, end_date) -> list
filter_by_text_search(items, search_text, search_fields) -> list
```

## Implementation Guide

### Step 1: Create Route File

Create `api/routes/{modality}.py` with this structure:

```python
"""Modality name endpoints.

Brief description of what this modality provides.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.dependencies import SimulationEngineDep
from api.models import ModalityActionResponse, ModalityStateResponse
from api.utils import create_immediate_event, get_modality_state

router = APIRouter(
    prefix="/{modality}",
    tags=["{modality}"],
)
```

### Step 2: Define Request Models

Create typed Pydantic models for each action:

```python
# Request Models

class SendModalityItemRequest(BaseModel):
    """Request model for sending/creating an item."""
    field1: str
    field2: int = Field(..., ge=0)

class ModalityQueryRequest(BaseModel):
    """Request model for querying modality data."""
    # Inherit from or compose with common parameter models
    filter_field: str | None = None
    limit: int | None = Field(None, ge=1, le=1000)
    offset: int = Field(0, ge=0)
    sort_by: str | None = None
    sort_order: str | None = Field(None, pattern="^(asc|desc)$")
```

### Step 3: Define Response Models

Create response models for complex state or query results:

```python
# Response Models

class ModalityStateData(BaseModel):
    """The actual state data for this modality."""
    items: list[dict]
    metadata: dict

class ModalityQueryResults(BaseModel):
    """Query result structure."""
    items: list[dict]
```

### Step 4: Implement State Endpoint

```python
@router.get("/state", response_model=ModalityStateResponse[ModalityStateData])
async def get_modality_state(engine: SimulationEngineDep):
    """Get current modality state.
    
    Returns a complete snapshot of the modality's current state
    including all items and metadata.
    
    Args:
        engine: The SimulationEngine instance (injected).
    
    Returns:
        Complete modality state.
    
    Raises:
        HTTPException: If modality not initialized (500).
    """
    try:
        state = get_modality_state(engine, "{modality}")
        current_time = get_current_simulator_time(engine)
        
        # Convert state to response format
        state_data = ModalityStateData(
            items=state.items,
            metadata={"count": len(state.items)},
        )
        
        return ModalityStateResponse(
            modality_type="{modality}",
            current_time=current_time,
            state=state_data,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve {modality} state: {str(e)}",
        )
```

### Step 5: Implement Query Endpoint (Optional)

```python
@router.post("/query", response_model=ModalityQueryResponse[ModalityQueryResults])
async def query_modality(
    request: ModalityQueryRequest,
    engine: SimulationEngineDep,
):
    """Query modality data with filters.
    
    Allows filtering, sorting, and paginating through modality data
    without retrieving the complete state.
    
    Args:
        request: Query parameters including filters and pagination.
        engine: The SimulationEngine instance (injected).
    
    Returns:
        Filtered and paginated query results.
    
    Raises:
        HTTPException: If query fails (400 for invalid params, 500 for errors).
    """
    try:
        state = get_modality_state(engine, "{modality}")
        
        # Convert state items to dicts for filtering
        items = [item.model_dump() for item in state.items]
        
        # Apply filters (modality-specific)
        if request.filter_field:
            items = [i for i in items if i.get("field") == request.filter_field]
        
        # Apply sorting
        items = apply_sort(items, request.sort_by, request.sort_order or "asc")
        
        # Apply pagination
        paginated, total, returned = apply_pagination(
            items,
            request.limit,
            request.offset,
        )
        
        results = ModalityQueryResults(items=paginated)
        
        return ModalityQueryResponse(
            modality_type="{modality}",
            query=request.model_dump(exclude_none=True),
            results=results,
            total_count=total,
            returned_count=returned,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query {modality}: {str(e)}",
        )
```

### Step 6: Implement Action Endpoints

```python
@router.post("/send", response_model=ModalityActionResponse)
async def send_item(
    request: SendModalityItemRequest,
    engine: SimulationEngineDep,
):
    """Send/create a new item in this modality.
    
    Creates an immediate event that adds the item to the modality state.
    
    Args:
        request: Item details to send/create.
        engine: The SimulationEngine instance (injected).
    
    Returns:
        Event details confirming the action.
    
    Raises:
        HTTPException: If action fails (400 for invalid data, 500 for errors).
    """
    try:
        # Construct event data from request
        event_data = {
            "action": "send",
            "field1": request.field1,
            "field2": request.field2,
        }
        
        # Create immediate event
        event = create_immediate_event(
            engine=engine,
            modality="{modality}",
            data=event_data,
            priority=100,
        )
        
        return ModalityActionResponse(
            event_id=event.event_id,
            scheduled_time=event.scheduled_time,
            status=event.status.value,
            message="Item sent successfully",
            modality="{modality}",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send item: {str(e)}",
        )
```

### Step 7: Register Router

In `main.py`, register the new router:

```python
from api.routes import {modality}

app.include_router({modality}.router)
```

## Modality-Specific Considerations

### Email Modality
- **State**: All folders (inbox, sent, drafts, trash, spam, archive), threads, labels
- **Query Filters**: folder, label, is_read, is_starred, has_attachments, from/to addresses, subject/body search
- **Actions**: send, receive, read, unread, star, unstar, archive, delete, label, unlabel, move

### SMS Modality
- **State**: All threads and messages
- **Query Filters**: thread_id, phone_number, direction, message_type, is_read, has_attachments, text search
- **Actions**: send, receive, read, unread, delete, react

### Chat Modality
- **State**: All conversations and messages
- **Query Filters**: conversation_id, role, text search, date range
- **Actions**: send, delete, clear

### Calendar Modality
- **State**: All calendars and events (with recurring event expansion optional)
- **Query Filters**: calendar_id, date range, status, has_attendees, recurring, text search, color
- **Actions**: create, update, delete, accept, decline, tentative

### Location Modality
- **State**: Current coordinates, history, tracking status
- **Query Filters**: (minimal - typically just get current state)
- **Actions**: update, move-to

### Weather Modality
- **State**: Current conditions and forecasts for tracked locations
- **Query Filters**: location, date range
- **Actions**: update, set-location

## Testing Guidelines

Each modality route should have tests covering:

1. **State Retrieval**
   - Get state when modality is empty
   - Get state with populated data
   - Error handling when modality not initialized

2. **Query Functionality** (if applicable)
   - Query with no filters (returns all)
   - Query with single filter
   - Query with multiple filters
   - Query with sorting (asc/desc)
   - Query with pagination
   - Query with invalid parameters

3. **Action Endpoints**
   - Successful action execution
   - Action with invalid data (validation errors)
   - Action creating expected event
   - State changes after action execution

4. **Error Handling**
   - 400 for invalid request data
   - 404 for missing modality
   - 500 for unexpected errors

## OpenAPI Documentation

FastAPI automatically generates OpenAPI documentation from:
- Pydantic model schemas (request/response types)
- Function docstrings (endpoint descriptions)
- Field descriptions and constraints

Ensure all models and endpoints have:
- Clear docstrings
- Field descriptions using `Field(..., description="...")`
- Proper type hints
- Example values using `Field(..., example=...)`

## Common Patterns and Best Practices

### 1. Always Use Type Hints
```python
async def endpoint(request: RequestModel, engine: SimulationEngineDep) -> ResponseModel:
```

### 2. Leverage Shared Utilities
```python
# Don't recreate event creation logic
event = create_immediate_event(engine, "email", data)

# Don't reimplement modality lookup
state = get_modality_state(engine, "email")
```

### 3. Consistent Error Messages
```python
raise HTTPException(
    status_code=400,
    detail=f"Invalid {modality} data: {str(e)}",
)
```

### 4. Use Field Validation
```python
class MyRequest(BaseModel):
    email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    count: int = Field(..., ge=1, le=100)
```

### 5. Document Query Parameters
```python
class EmailQueryRequest(BaseModel):
    """Query email state with filters.
    
    All parameters are optional. If no filters provided, returns all emails.
    """
    folder: str | None = Field(None, description="Filter by folder name")
    is_read: bool | None = Field(None, description="Filter by read status")
```

## API Design Benefits

The modality-specific route pattern provides several advantages over a generic `/modalities` approach:

1. **Type Safety**: Each endpoint has precisely typed request/response models
2. **Better Documentation**: Auto-generated OpenAPI docs show exact schemas for each action
3. **Clearer Intent**: `/email/send` is more intuitive than `/modalities/email/submit?operation=send`
4. **Easier Discovery**: Related operations are grouped under modality prefix
5. **Better Error Messages**: Validation errors reference specific field names
6. **IDE Support**: Type hints provide autocomplete and inline documentation

### Example Comparison

**Modality-Specific (Current)**:
```python
POST /email/send
{
  "to_addresses": ["user@example.com"],
  "subject": "Test",
  "body_text": "Hello"
}
```

Benefits:
- No need for generic "operation" field
- Better type safety (SendEmailRequest vs dict)
- Clearer API documentation
- More intuitive endpoint naming

## Code Organization Patterns

### File Structure

Each modality route file follows this structure:

```
api/routes/<modality>.py
│
├── Imports (models, dependencies, utilities)
├── Router definition
├── Request model definitions (Pydantic)
├── Response model definitions (Pydantic)
├── Core endpoints (state, query)
└── Action endpoints (modality-specific)
```

### Naming Conventions

**Route Files**: `api/routes/<modality>.py` (lowercase, singular)
- Examples: `email.py`, `sms.py`, `calendar.py`, `location.py`

**Request Models**: `<Action><Modality>Request`
- Examples: `SendEmailRequest`, `UpdateLocationRequest`, `CreateCalendarEventRequest`

**Response Models**:
- State: `<Modality>StateResponse` (e.g., `EmailStateResponse`)
- Actions: Use shared `ModalityActionResponse` (defined in `api/models.py`)
- Query: `<Modality>QueryResponse` (e.g., `EmailQueryResponse`)

**Endpoints**:
- State: `GET /<modality>/state`
- Query: `POST /<modality>/query`
- Actions: `POST /<modality>/<action>` (e.g., `/email/send`, `/sms/react`)

### Example Template

```python
"""<Modality> modality REST API routes.

Provides endpoints for interacting with the <modality> modality in the simulation.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.dependencies import SimulationEngineDep
from api.models import ModalityActionResponse
from api.utils import create_immediate_event
from models.modalities.<modality>_input import <Modality>Input
from models.modalities.<modality>_state import <Modality>State

router = APIRouter(prefix="/<modality>", tags=["<modality>"])

# --- Request Models ---

class ActionOneRequest(BaseModel):
    """Request model for action one."""
    field1: str = Field(..., description="Field one description")
    field2: int = Field(..., description="Field two description")

class ActionTwoRequest(BaseModel):
    """Request model for action two."""
    field1: str = Field(..., description="Field one description")

class <Modality>QueryRequest(BaseModel):
    """Request model for querying <modality> state."""
    filter_field: str | None = Field(None, description="Optional filter")

# --- Response Models ---

class <Modality>StateResponse(BaseModel):
    """Response model for <modality> state."""
    state: <Modality>State

class <Modality>QueryResponse(BaseModel):
    """Response model for <modality> query results."""
    results: list[<SomeModel>]  # Type depends on modality

# --- Core Endpoints ---

@router.get("/state", response_model=<Modality>StateResponse)
async def get_modality_state(engine: SimulationEngineDep):
    """Get current <modality> state.
    
    Returns a complete snapshot of the modality's current state.
    """
    modality_state = engine.environment.get_modality("<modality>")
    if not modality_state:
        raise HTTPException(
            status_code=404,
            detail="<Modality> modality not found in environment",
        )
    
    return <Modality>StateResponse(state=modality_state)

@router.post("/query", response_model=<Modality>QueryResponse)
async def query_modality(request: <Modality>QueryRequest, engine: SimulationEngineDep):
    """Query <modality> state with filters.
    
    Allows filtering and searching through <modality> data.
    """
    modality_state = engine.environment.get_modality("<modality>")
    if not modality_state:
        raise HTTPException(
            status_code=404,
            detail="<Modality> modality not found in environment",
        )
    
    # Apply filters and return results
    results = modality_state.query(...)  # Implementation depends on modality
    
    return <Modality>QueryResponse(results=results)

# --- Action Endpoints ---

@router.post("/action-one", response_model=ModalityActionResponse)
async def perform_action_one(request: ActionOneRequest, engine: SimulationEngineDep):
    """Perform a specific action on this modality.
    
    Creates an immediate event that executes the action.
    """
    try:
        # Create modality input from request
        modality_input = <Modality>Input(
            action="action_one",
            field1=request.field1,
            field2=request.field2,
        )
        
        # Create and execute immediate event
        event = create_immediate_event(
            engine=engine,
            modality="<modality>",
            input_data=modality_input,
        )
        
        return ModalityActionResponse(
            event_id=event.event_id,
            status="executed",
            message="Action performed successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to perform action: {str(e)}",
        )

@router.post("/action-two", response_model=ModalityActionResponse)
async def perform_action_two(request: ActionTwoRequest, engine: SimulationEngineDep):
    """Perform another specific action on this modality."""
    # Similar implementation to action-one
    pass
```

### Key Implementation Notes

1. **Import Modality Models**: Always import both `<Modality>Input` and `<Modality>State`
2. **Use Shared Response Types**: `ModalityActionResponse` is defined in `api/models.py`
3. **Use Helper Utilities**: `create_immediate_event()` from `api/utils.py` handles event creation
4. **Check Modality Exists**: Always verify modality is in environment before accessing
5. **Proper Error Handling**: Use `HTTPException` with appropriate status codes
6. **Type Safety**: All request/response models use Pydantic, no `dict[str, Any]`
7. **Documentation**: Include docstrings for all endpoints and models

## Summary

Following this standard pattern ensures:
- ✅ Consistent API structure across all modalities
- ✅ Type-safe requests and responses
- ✅ Reusable code through shared utilities
- ✅ Self-documenting API via OpenAPI
- ✅ Easy maintenance and extension
- ✅ Clear separation of concerns

When implementing a new modality, use this document as a checklist and reference the existing modality implementations (email, sms, chat, etc.) as examples.
