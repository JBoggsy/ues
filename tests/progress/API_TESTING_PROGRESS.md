# API Testing Progress

This document tracks the implementation of unit and integration tests for the UES REST API.

## Overview

The API testing suite is divided into two main categories:
1. **Unit Tests**: Test individual API components in isolation (request/response models, utilities, dependencies)
2. **Integration Tests**: Test complete API workflows end-to-end (route behavior, state management, error handling)

## Testing Strategy

### Unit Tests (`tests/api/unit/`)
- Request/response model validation
- Utility function behavior
- Dependency injection components
- Error response formatting
- OpenAPI schema generation

### Integration Tests (`tests/api/integration/`)
- Complete HTTP request/response cycles
- Multi-step workflows
- State consistency across requests
- Concurrent request handling
- Error handling and recovery

## Key Infrastructure Discoveries

### Test Fixture Pattern (`client_with_engine`)
We've established a reusable fixture pattern that:
1. Creates a fresh `SimulationEngine` for each test (via `fresh_engine` fixture)
2. Overrides the FastAPI dependency injection to use the test engine
3. Automatically starts the simulation before each test
4. Cleans up after each test (stops simulation, clears overrides)

**Usage in all integration tests:**
```python
def test_something(client_with_engine):
    client, engine = client_with_engine
    response = client.get("/some/endpoint")
    # Test assertions here
```

### Request Model Validation
Tests revealed the actual request field names required by the API:
- `/simulator/time/advance` expects `{"seconds": float}` (not `duration_seconds`)
- `/simulator/time/set-scale` expects `{"scale": float}` (not `time_scale`)
- Email events use `operation` (not `action`) with fields like `from_address`, `to_addresses`, `body_text`
- SMS events use `action` with nested `message_data` containing `from_number`, `to_numbers` (plural list), `body`
- Chat events use simple `content` field (string for text, not nested dict)

This highlights the importance of integration tests to catch documentation/implementation mismatches and inconsistencies in field naming across modalities.

### Simulation State Requirement
Most time operations require a running simulation. The `client_with_engine` fixture (`tests/api/conftest.py`) handles this automatically by calling `POST /simulation/start` with `auto_advance=False` before each test.

### API Helper Module (`tests/api/helpers.py`)
Created comprehensive helper functions for constructing valid event data:
- **`make_event_request()`**: Wraps modality data into complete event request
- **Modality-specific helpers**: `email_event_data()`, `sms_event_data()`, `chat_event_data()`, `location_event_data()`, `calendar_event_data()`, `time_event_data()`, `weather_event_data()`
- **Benefits**: Centralized maintenance, correct field names, reusable across tests, well-documented signatures
- **Usage**: `make_event_request(event_time, "email", email_event_data(subject="Test"))`

This eliminates duplication and ensures consistency across all API integration tests.

## Progress Tracking

### Unit Tests

#### Core API Components
- [ ] Request validation (`test_request_models.py`)
  - [ ] Time control request models
  - [ ] Event creation request models
  - [ ] Query parameter models
  - [ ] Simulation control request models
- [ ] Response serialization (`test_response_models.py`)
  - [ ] Error response model
  - [ ] Event response models
  - [ ] State snapshot response models
  - [ ] Execution summary response models
  - [ ] Time-specific response models
  - [ ] Weather-specific response models
  - [ ] Modality submission response models
  - [ ] Environment validation response models
- [ ] Dependency injection (`test_dependencies.py`)
  - [ ] SimulationEngine dependency
  - [ ] Request context dependencies
- [ ] Error response formatting (`test_error_handling.py`)
  - [ ] Exception handler behavior
  - [ ] HTTP status code mapping
  - [ ] Error message formatting

### Integration Tests

#### Event Routes

**Test File Organization:**
- `test_event_listing.py` - GET /events (listing and filtering)
- `test_event_creation.py` - POST /events, POST /events/immediate
- `test_event_operations.py` - GET /events/{id}, DELETE /events/{id}
- `test_event_queries.py` - GET /events/next, GET /events/summary

**Completed Tests:**

##### Event Listing (`test_event_listing.py`)
- [x] `GET /events` - List events with filters (10 tests, all passing)
  - [x] Empty queue returns empty list with zero counts
  - [x] Returns created events with correct details
  - [x] Returns multiple events from different modalities
  - [x] Filter by status (pending, executed, etc.)
  - [x] Filter by modality type
  - [x] Filter by time range (start_time and end_time)
  - [x] Pagination with limit parameter
  - [x] Pagination with offset parameter
  - [x] Combined filters (modality + time range)
  - [x] Invalid status returns 400 error

**Pending Tests:**

##### Event Creation (`test_event_creation.py`)
- [x] `POST /events` - Create scheduled event (18 tests, all passing)
  - [x] Returns event with unique ID
  - [x] Works for all modalities (email, sms, chat, location, calendar, weather, time)
  - [x] Respects custom priority values
  - [x] Preserves custom metadata
  - [x] Accepts agent_id field
  - [x] Rejects invalid modality names
  - [x] Validates modality-specific data (email, sms, location)
  - [x] Rejects events scheduled in the past
  - [x] Allows multiple events at same time with different priorities
  - [x] Validates required fields
- [x] `POST /events/immediate` - Create immediate event (16 tests, all passing)
  - [x] Returns event with unique ID
  - [x] Scheduled at current simulator time
  - [x] Created with high priority (100)
  - [x] Works for all modalities (email, sms, chat, location, calendar, weather, time)
  - [x] Validates modality-specific data
  - [x] Validates required fields (modality, data)
  - [x] Rejects invalid modality names
  - [x] Events appear in queue
  - [x] Supports multiple immediate events

##### Event Operations (`test_event_operations.py`)
- [x] `GET /events/{event_id}` - Get event details (4 tests, all passing)
  - [x] Returns full event details
  - [x] Returns 404 for nonexistent events
  - [x] Returns executed events with status
  - [x] Includes custom metadata (documented limitation)
- [x] `DELETE /events/{event_id}` - Cancel event (5 tests, all passing)
  - [x] Removes event from queue (marks as cancelled)
  - [x] Returns success confirmation
  - [x] Returns 404 for nonexistent events
  - [x] Rejects already-executed/failed events
  - [x] Handles multiple deletions (not idempotent - fails on second delete)

##### Event Queries (`test_event_queries.py`)
- [x] `GET /events/next` - Peek at next event (5 tests, all passing)
  - [x] Returns earliest pending event
  - [x] Returns 404 when queue is empty
  - [x] Skips already-executed events
  - [x] Respects priority for simultaneous events
  - [x] Does not modify queue (read-only)
- [x] `GET /events/summary` - Get statistics (5 tests, all passing)
  - [x] Returns zero counts for empty queue
  - [x] Counts events by status
  - [x] Includes counts per modality
  - [x] Includes next event time
  - [x] Updates after events are executed

#### Time Control Routes (`test_time_routes.py`)
- [x] `GET /simulator/time` - Get current time state (5 tests)
  - [x] Returns current state with all required fields
  - [x] Reflects engine state changes (time advance)
  - [x] Shows paused state correctly
  - [x] Reflects time scale changes
  - [x] Returns consistent ISO 8601 format
- [ ] `POST /simulator/time/advance` - Advance by duration
- [ ] `POST /simulator/time/set` - Jump to specific time
- [ ] `POST /simulator/time/skip-to-next` - Event-driven skip
- [ ] `POST /simulator/time/pause` - Pause simulation
- [ ] `POST /simulator/time/resume` - Resume simulation
- [ ] `POST /simulator/time/set-scale` - Change time scale

#### Environment Routes (`test_environment_routes.py`)
- [ ] `GET /environment/state` - Complete state snapshot
- [ ] `GET /environment/modalities` - List modalities
- [ ] `GET /environment/modalities/{modality}` - Get modality state
- [ ] `POST /environment/modalities/{modality}/query` - Query with filters
- [ ] `POST /environment/validate` - Validate consistency

#### Simulation Routes (`test_simulation_routes.py`)
- [ ] `POST /simulation/start` - Start simulation
- [ ] `POST /simulation/stop` - Stop simulation
- [ ] `GET /simulation/status` - Get status and metrics
- [ ] `POST /simulation/reset` - Reset to initial state

#### Modality Convenience Routes (`test_modality_routes.py`)
- [ ] `POST /modalities/chat/submit` - Submit chat message
- [ ] `POST /modalities/email/submit` - Submit email action
- [ ] `POST /modalities/calendar/submit` - Submit calendar action
- [ ] `POST /modalities/sms/submit` - Submit SMS action
- [ ] `POST /modalities/location/submit` - Submit location update
- [ ] `POST /modalities/time/submit` - Submit time preference update
- [ ] `POST /modalities/weather/submit` - Submit weather update
- [ ] Generic modality handler (`POST /modalities/{modality}/submit`)

#### Modality-Specific Query Routes
- [ ] Email routes (`test_email_routes.py`)
  - [ ] State retrieval
  - [ ] Query with filters (folder, sender, subject, date range)
  - [ ] All 11 action endpoints (send, receive, delete, move, mark_read, etc.)
- [ ] SMS routes (`test_sms_routes.py`)
  - [ ] State retrieval
  - [ ] Query with filters (conversation, participant, search)
  - [ ] All 6 action endpoints (send, receive, delete, mark_read, etc.)
- [ ] Chat routes (`test_chat_routes.py`)
  - [ ] State retrieval
  - [ ] Query with filters (role, content search, turn range)
  - [ ] All 3 action endpoints (user_message, assistant_message, system_message)
- [ ] Calendar routes (`test_calendar_routes.py`)
  - [ ] State retrieval
  - [ ] Query with filters (date range, recurrence, attendees)
  - [ ] Create/update/delete event endpoints
- [ ] Location routes (`test_location_routes.py`)
  - [ ] State retrieval
  - [ ] Query with filters (history, named locations, time range)
  - [ ] Update location endpoint
- [ ] Weather routes (`test_weather_routes.py`)
  - [ ] State retrieval
  - [ ] Query with filters (location, units, time range)
  - [ ] Update weather endpoint
- [ ] Time routes (`test_time_modality_routes.py`)
  - [ ] State retrieval
  - [ ] Query with filters (preference history, timezone changes)
  - [ ] Update preferences endpoint

#### Cross-Cutting Integration Tests
- [ ] Error handling (`test_error_scenarios.py`)
  - [ ] Invalid request data
  - [ ] Missing modality references
  - [ ] Concurrent modification conflicts
  - [ ] Resource not found errors
  - [ ] Validation errors
- [ ] State consistency (`test_state_consistency.py`)
  - [ ] Environment state after event execution
  - [ ] Query results match actual state
  - [ ] Time advancement affects all modalities correctly
- [ ] Concurrent requests (`test_concurrency.py`)
  - [ ] Multiple simultaneous event submissions
  - [ ] Concurrent time control operations
  - [ ] Race condition handling

#### Multi-Step Workflow Tests
- [ ] Complete simulation scenarios (`test_workflows.py`)
  - [ ] Manual time control workflow
  - [ ] Event-driven simulation
  - [ ] Auto-advance with fast-forward
  - [ ] Agent responding to user messages
  - [ ] Scheduled event creation and execution

## Testing Infrastructure

### Test Utilities
- [x] API test fixtures (`tests/fixtures/api.py`)
  - [x] FastAPI test client setup
  - [x] Pre-configured simulation engines
  - [x] Sample request/response data
- [x] API test helpers (`tests/api/helpers.py`)
  - [x] Event request builder (`make_event_request()`)
  - [x] Modality data creators (email, sms, chat, location, calendar, time, weather)
  - [x] Comprehensive docstrings for all helper functions
  - [x] Correct field names matching actual model implementations

### Test Configuration
- [ ] pytest configuration for API tests
- [ ] Test coverage reporting
- [ ] Integration test markers
- [ ] Slow test markers

## Documentation & Examples

- [ ] API usage examples
  - [ ] Manual time control workflow
  - [ ] Event-driven simulation
  - [ ] Auto-advance with fast-forward
  - [ ] Agent responding to user messages
  - [ ] Scheduled event creation
- [ ] Postman/Thunder Client collection
- [ ] API client library (optional)

## Notes

- Integration tests should use the FastAPI TestClient for realistic HTTP request/response cycles
- Unit tests should mock dependencies to isolate component behavior
- All tests should use fixtures from `tests/fixtures/` for consistent test data
- Tests should verify both success cases and error handling
- Query tests should verify filters, pagination, and result accuracy
- Concurrent tests should verify thread-safety and race condition handling
