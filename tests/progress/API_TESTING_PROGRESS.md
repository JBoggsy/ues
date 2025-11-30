# API Testing Progress

This document tracks the implementation of unit and integration tests for the UES REST API.

## Summary

**Total Tests: 907 (all passing)**

| Category | Test Count | Status |
|----------|------------|--------|
| Environment Routes | 34 | ✅ Complete |
| Event Routes | 63 | ✅ Complete |
| Time Routes | 50 | ✅ Complete |
| Simulation Routes | 75 | ✅ Complete |
| Modality Routes (Chat) | 33 | ✅ Complete |
| Modality Routes (Email) | 62 | ✅ Complete |
| Modality Routes (SMS) | 46 | ✅ Complete |
| Modality Routes (Calendar) | 38 | ✅ Complete |
| Modality Routes (Location) | 39 | ✅ Complete |
| Modality Routes (Weather) | 30 | ✅ Complete |
| **Unit Tests (Request Models)** | **129** | ✅ Complete |
| **Unit Tests (Response Models)** | **55** | ✅ Complete |
| **Unit Tests (Dependencies)** | **30** | ✅ Complete |
| **Unit Tests (Error Handling)** | **71** | ✅ Complete |
| **Cross-Cutting (Error Scenarios)** | **49** | ✅ Complete |
| **Cross-Cutting (State Consistency)** | **33** | ✅ Complete |
| **Cross-Cutting (Concurrency)** | **23** | ✅ Complete |
| **Workflow Tests (Scenario 1)** | **12** | ✅ Complete |
| **Workflow Tests (Scenario 2)** | **17** | ✅ Complete |
| **Workflow Tests (Scenario 3)** | **18** | ✅ Complete |

## Testing Strategy

### Integration Tests (`tests/api/`)
Integration tests are organized into subdirectories by route group:
- `tests/api/events/` - Event creation, listing, operations, and queries
- `tests/api/time/` - Time control and navigation endpoints
- `tests/api/environment/` - Environment state and modality queries
- `tests/api/simulation/` - Simulation lifecycle control
- `tests/api/modalities/` - Modality-specific convenience routes
- `tests/api/cross_cutting/` - Cross-cutting integration tests (error handling, state consistency, concurrency)

Each subdirectory contains test files grouped by functional area following the pattern established in `API_TESTING_GUIDELINES.md`.

### Unit Tests (`tests/api/unit/`) - 285 tests

Unit tests for Pydantic model validation, dependency injection, and error handling.

**Test Files:**
- `test_request_models.py` - 129 tests
- `test_response_models.py` - 55 tests
- `test_dependencies.py` - 30 tests
- `test_error_handling.py` - 71 tests

## Key Infrastructure

### Test Fixture Pattern (`client_with_engine`)
A reusable fixture pattern that:
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

### API Helper Module (`tests/api/helpers.py`)
Comprehensive helper functions for constructing valid event data:
- **`make_event_request()`**: Wraps modality data into complete event request
- **Modality-specific helpers**: `email_event_data()`, `sms_event_data()`, `chat_event_data()`, `location_event_data()`, `calendar_event_data()`, `time_event_data()`, `weather_event_data()`

### Request Model Field Names
Tests revealed the actual request field names required by the API:
- `/simulator/time/advance` expects `{"seconds": float}`
- `/simulator/time/set-scale` expects `{"scale": float}`
- Email events use `operation` with fields like `from_address`, `to_addresses`, `body_text`
- SMS events use `action` with nested `message_data` containing `from_number`, `to_numbers`, `body`
- Chat events use simple `content` field (string for text)

---

## Integration Tests Detail

### Event Routes (`tests/api/events/`) - 63 tests

**Test Files:**
- `test_event_listing.py` - 10 tests
- `test_event_creation.py` - 34 tests
- `test_event_operations.py` - 9 tests
- `test_event_queries.py` - 10 tests

#### Event Listing (`test_event_listing.py`) - 10 tests
- [x] `GET /events` - List events with filters
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

#### Event Creation (`test_event_creation.py`) - 34 tests
- [x] `POST /events` - Create scheduled event (18 tests)
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
- [x] `POST /events/immediate` - Create immediate event (16 tests)
  - [x] Returns event with unique ID
  - [x] Scheduled at current simulator time
  - [x] Created with high priority (100)
  - [x] Works for all modalities (email, sms, chat, location, calendar, weather, time)
  - [x] Validates modality-specific data
  - [x] Validates required fields (modality, data)
  - [x] Rejects invalid modality names
  - [x] Events appear in queue
  - [x] Supports multiple immediate events

#### Event Operations (`test_event_operations.py`) - 9 tests
- [x] `GET /events/{event_id}` - Get event details (4 tests)
  - [x] Returns full event details
  - [x] Returns 404 for nonexistent events
  - [x] Returns executed events with status
  - [x] Includes custom metadata
- [x] `DELETE /events/{event_id}` - Cancel event (5 tests)
  - [x] Removes event from queue (marks as cancelled)
  - [x] Returns success confirmation
  - [x] Returns 404 for nonexistent events
  - [x] Rejects already-executed/failed events
  - [x] Handles multiple deletions (not idempotent - fails on second delete)

#### Event Queries (`test_event_queries.py`) - 10 tests
- [x] `GET /events/next` - Peek at next event (5 tests)
  - [x] Returns earliest pending event
  - [x] Returns 404 when queue is empty
  - [x] Skips already-executed events
  - [x] Respects priority for simultaneous events
  - [x] Does not modify queue (read-only)
- [x] `GET /events/summary` - Get statistics (5 tests)
  - [x] Returns zero counts for empty queue
  - [x] Counts events by status
  - [x] Includes counts per modality
  - [x] Includes next event time
  - [x] Updates after events are executed

---

### Time Control Routes (`tests/api/time/`) - 50 tests

**Test Files:**
- `test_time_state.py` - 5 tests
- `test_time_advance.py` - 10 tests
- `test_time_control.py` - 10 tests
- `test_time_navigation.py` - 14 tests
- `test_time_scale.py` - 11 tests

#### Time State (`test_time_state.py`) - 5 tests
- [x] `GET /simulator/time` - Get current time state
  - [x] Returns current state with all required fields
  - [x] Reflects engine state changes (time advance)
  - [x] Shows paused state correctly
  - [x] Reflects time scale changes
  - [x] Returns consistent ISO 8601 format

#### Time Advance (`test_time_advance.py`) - 10 tests
- [x] `POST /simulator/time/advance` - Advance by duration
  - [x] Moves time forward by specified duration
  - [x] Rejects zero duration
  - [x] Rejects negative duration
  - [x] Executes events in time window
  - [x] Does not execute future events
  - [x] Works with large durations
  - [x] Supports multiple sequential advances
  - [x] Fails when simulation is paused
  - [x] Accepts fractional seconds
  - [x] Returns consistent time state

#### Time Control (`test_time_control.py`) - 10 tests
- [x] `POST /simulator/time/pause` - Pause simulation (5 tests)
  - [x] Stops time advancement
  - [x] Is idempotent
  - [x] Prevents time advance operations
  - [x] Does not change current time
  - [x] Works with pending events in queue
- [x] `POST /simulator/time/resume` - Resume simulation (5 tests)
  - [x] Restarts time advancement
  - [x] Is idempotent
  - [x] Allows time advance after resume
  - [x] Does not change current time
  - [x] Works in pause/resume cycles

#### Time Navigation (`test_time_navigation.py`) - 14 tests
- [x] `POST /simulator/time/set` - Jump to specific time (8 tests)
  - [x] Jumps to specified time
  - [x] Handles past times appropriately (rejects with 400 error)
  - [x] Skips events in time window (marks as skipped)
  - [x] Does not skip future events beyond target time
  - [x] Handles setting to current time (no-op)
  - [x] Validates time format (rejects invalid formats)
  - [x] Validates missing target_time field (422 error)
  - [x] Validates null target_time value (422 error)
- [x] `POST /simulator/time/skip-to-next` - Skip to next event (6 tests)
  - [x] Moves to next scheduled event
  - [x] Handles empty queue appropriately (returns 404)
  - [x] Executes events at target time
  - [x] Works for multiple consecutive skips
  - [x] Handles multiple events at same time (executes all)
  - [x] Returns execution summary

#### Time Scale (`test_time_scale.py`) - 11 tests
- [x] `POST /simulator/time/set-scale` - Change time scale
  - [x] Changes time scale successfully
  - [x] Rejects zero scale (422 validation error)
  - [x] Rejects negative scale (422 validation error)
  - [x] Accepts fractional values (slow-motion mode)
  - [x] Accepts very large values (1000x fast-forward)
  - [x] Accepts very small positive values (0.01x slow-motion)
  - [x] Persists across pause/resume cycles
  - [x] Supports multiple scale changes
  - [x] Validates missing scale field (422 error)
  - [x] Validates null scale value (422 error)
  - [x] Returns to real-time when set to 1.0

---

### Environment Routes (`tests/api/environment/`) - 34 tests

**Test Files:**
- `test_environment_state.py` - 6 tests
- `test_environment_validation.py` - 6 tests
- `test_modality_listing.py` - 4 tests
- `test_modality_queries.py` - 12 tests
- `test_modality_state.py` - 6 tests

#### Environment State (`test_environment_state.py`) - 6 tests
- [x] `GET /environment/state` - Complete state snapshot
  - [x] Returns complete snapshot with all modality states
  - [x] Reflects modality changes after event execution
  - [x] Includes all registered modalities
  - [x] Returns current simulator time
  - [x] Time changes after time advance
  - [x] Summary field has correct structure

#### Modality Listing (`test_modality_listing.py`) - 4 tests
- [x] `GET /environment/modalities` - List modalities
  - [x] Returns all modality types
  - [x] Matches environment state modalities
  - [x] Count is accurate
  - [x] Lightweight response (no full state)

#### Modality State (`test_modality_state.py`) - 6 tests
- [x] `GET /environment/modalities/{modality_name}` - Get modality state
  - [x] Returns modality state with correct structure
  - [x] Works for all registered modalities
  - [x] Returns 404 for invalid modality
  - [x] Reflects changes after event execution
  - [x] Includes current simulator time
  - [x] More efficient than fetching full environment state

#### Modality Queries (`test_modality_queries.py`) - 12 tests
- [x] `POST /environment/modalities/{modality_name}/query` - Query with filters
  - [x] Returns query results with correct structure
  - [x] Returns 404 for invalid modality
  - [x] Email modality supports filters
  - [x] SMS modality supports filters
  - [x] Calendar modality supports filters
  - [x] Chat modality supports filters
  - [x] Location modality supports filters
  - [x] Weather modality supports filters
  - [x] Weather query fails without required lat/lon
  - [x] Time modality supports filters
  - [x] Handles invalid query parameters gracefully
  - [x] All 7 modalities have working query methods

#### Environment Validation (`test_environment_validation.py`) - 6 tests
- [x] `POST /environment/validate` - Validate consistency
  - [x] Returns valid for clean environment
  - [x] Checked_at matches current simulator time
  - [x] Remains valid after event execution
  - [x] Detects inconsistencies
  - [x] Validation errors are descriptive
  - [x] Validation is read-only operation

---

### Simulation Routes (`tests/api/simulation/`) - 75 tests

**Test Files:**
- `test_simulation_start.py` - 18 tests
- `test_simulation_stop.py` - 14 tests
- `test_simulation_status.py` - 23 tests
- `test_simulation_reset.py` - 20 tests

#### Simulation Start (`test_simulation_start.py`) - 18 tests
- [x] `POST /simulation/start` - Start simulation
  - [x] Returns success response with simulation_id, status, current_time
  - [x] Defaults to manual mode (auto_advance=False)
  - [x] Manual mode explicit (auto_advance=False parameter)
  - [x] Auto-advance mode (auto_advance=True)
  - [x] Custom time_scale accepted
  - [x] time_scale with manual mode
  - [x] Returns unique simulation_id
  - [x] Returns current_time in ISO 8601 format
  - [x] Fails when already running (409 Conflict)
  - [x] Rejects zero time_scale (422)
  - [x] Rejects negative time_scale (422)
  - [x] Validates auto_advance type (422)
  - [x] Validates time_scale type (422)
  - [x] Very large time_scale accepted
  - [x] Very small positive time_scale accepted
  - [x] Fractional time_scale accepted
  - [x] Empty request body uses defaults
  - [x] Unknown fields ignored

#### Simulation Stop (`test_simulation_stop.py`) - 14 tests
- [x] `POST /simulation/stop` - Stop simulation
  - [x] Returns success response
  - [x] Returns simulation_id
  - [x] Returns stopped status
  - [x] Returns final_time in ISO 8601 format
  - [x] Returns event counts (total, executed, failed)
  - [x] Event counts are accurate
  - [x] Prevents further time operations
  - [x] Allows restart after stop
  - [x] Handles not-running state gracefully
  - [x] Stops auto-advance mode
  - [x] final_time matches last known state
  - [x] Preserves executed events
  - [x] Handles pending events correctly
  - [x] Idempotent behavior documented

#### Simulation Status (`test_simulation_status.py`) - 23 tests
- [x] `GET /simulation/status` - Get status and metrics
  - [x] Returns all required fields
  - [x] Returns correct types for all fields
  - [x] is_running=True when started
  - [x] is_running=False when stopped
  - [x] is_running=False initially
  - [x] is_paused=True when paused
  - [x] is_paused=False by default
  - [x] is_paused=False after resume
  - [x] current_time is valid ISO 8601
  - [x] time_scale default is 1.0
  - [x] time_scale reflects changes
  - [x] current_time reflects time advancement
  - [x] Zero event counts initially
  - [x] pending_events count updates when events added
  - [x] executed_events count updates after execution
  - [x] failed_events count updates when events fail
  - [x] Event counts are accurate
  - [x] next_event_time null when queue empty
  - [x] next_event_time present with pending events
  - [x] next_event_time shows earliest pending event
  - [x] next_event_time updates after execution
  - [x] Consistent across multiple requests
  - [x] Reflects state changes between requests

#### Simulation Reset (`test_simulation_reset.py`) - 20 tests
- [x] `POST /simulation/reset` - Reset to initial state
  - [x] Returns success response
  - [x] Returns cleared_events count
  - [x] Clears event queue
  - [x] Cleared events count accurate
  - [x] Resets event statuses
  - [x] Resets simulation time
  - [x] Clears pause state
  - [x] Clears time scale
  - [x] Stops running simulation
  - [x] Works when already stopped
  - [x] Works when never started
  - [x] Stops auto-advance mode
  - [x] Resets environment state
  - [x] Preserves modality registrations
  - [x] Allows restart after reset
  - [x] New simulation_id on restart
  - [x] Idempotent (multiple resets)
  - [x] Handles pending events
  - [x] Handles failed events
  - [x] Message is descriptive

---

### Modality Convenience Routes (`tests/api/modalities/`) - 248 tests

Tests for each modality are split into three files:
1. `test_<modality>_state.py` - GET /<modality>/state endpoint
2. `test_<modality>_queries.py` - POST /<modality>/query endpoint
3. `test_<modality>_actions.py` - POST action endpoints (send, delete, etc.)

#### Chat Routes (`chat/`) - 33 tests
- `test_chat_state.py` - 6 tests
- `test_chat_queries.py` - 12 tests
- `test_chat_actions.py` - 15 tests

**Actions tested**: send, delete, clear

#### Email Routes (`email/`) - 62 tests
- `test_email_state.py` - 7 tests
- `test_email_queries.py` - 14 tests
- `test_email_actions.py` - 41 tests

**Actions tested**: send, receive, read, unread, star, unstar, archive, delete, label, unlabel, move

#### SMS Routes (`sms/`) - 46 tests
- `test_sms_state.py` - 7 tests
- `test_sms_queries.py` - 13 tests
- `test_sms_actions.py` - 26 tests

**Actions tested**: send, receive, read, unread, delete, react

#### Calendar Routes (`calendar/`) - 38 tests
- `test_calendar_state.py` - 6 tests
- `test_calendar_queries.py` - 12 tests
- `test_calendar_actions.py` - 20 tests

**Actions tested**: create, update, delete events

#### Location Routes (`location/`) - 39 tests
- `test_location_state.py` - 7 tests
- `test_location_queries.py` - 13 tests
- `test_location_actions.py` - 19 tests

**Actions tested**: update location

#### Weather Routes (`weather/`) - 30 tests
- `test_weather_state.py` - 7 tests
- `test_weather_queries.py` - 13 tests
- `test_weather_actions.py` - 10 tests

**Actions tested**: update weather (includes OpenWeather API integration tests)

---

### Unit Tests (`tests/api/unit/`) - 285 tests

**Test Files:**
- `test_request_models.py` - 129 tests
- `test_response_models.py` - 55 tests
- `test_dependencies.py` - 30 tests
- `test_error_handling.py` - 71 tests

#### Request Model Validation (`test_request_models.py`) - 129 tests

Tests for Pydantic request model validation including required fields, type constraints, default values, and Field validators.

**Common Models (`api/models.py`):**
- [x] `PaginationParams` - limit/offset constraints (ge, le)
- [x] `SortParams` - sort order pattern validation
- [x] `DateRangeParams` - date handling
- [x] `TextSearchParams` - search text/fields
- [x] `MarkItemsRequest` - item_ids min_length validation
- [x] `DeleteItemsRequest` - permanent flag defaults

**Simulation Models:**
- [x] `StartSimulationRequest` - time_scale gt=0, auto_advance defaults

**Time Control Models:**
- [x] `AdvanceTimeRequest` - seconds gt=0 required
- [x] `SetTimeRequest` - target_time datetime required
- [x] `SetScaleRequest` - scale gt=0 required

**Event Models:**
- [x] `CreateEventRequest` - priority ge=0 le=100, required fields
- [x] `ImmediateEventRequest` - modality and data required

**Chat Models:**
- [x] `SendChatMessageRequest` - Literal role validation, content types
- [x] `DeleteChatMessageRequest` - message_id required
- [x] `ClearChatRequest` - conversation_id defaults
- [x] `ChatQueryRequest` - limit/offset constraints, sort Literals

**Email Models:**
- [x] `SendEmailRequest` - to_addresses min_length, priority Literal
- [x] `EmailMarkRequest` - message_ids min_length
- [x] `EmailLabelRequest` - labels min_length
- [x] `EmailMoveRequest` - folder required
- [x] `EmailQueryRequest` - pagination constraints

**SMS Models:**
- [x] `SendSMSRequest` - to_numbers min_length, message_type Literal
- [x] `SMSMarkRequest` - message_ids min_length
- [x] `SMSDeleteRequest` - message_ids min_length
- [x] `SMSReactRequest` - emoji required
- [x] `SMSQueryRequest` - direction Literal filter

**Calendar Models:**
- [x] `CreateCalendarEventRequest` - title, start, end required
- [x] `UpdateCalendarEventRequest` - event_id required
- [x] `DeleteCalendarEventRequest` - event_id required
- [x] `CalendarQueryRequest` - expand_recurring defaults

**Location Models:**
- [x] `UpdateLocationRequest` - latitude/longitude required
- [x] `LocationQueryRequest` - include_current defaults

**Weather Models:**
- [x] `UpdateWeatherRequest` - latitude, longitude, report required
- [x] `WeatherQueryRequest` - lat/lon required, units Literal

#### Response Model Serialization (`test_response_models.py`) - 55 tests

Tests for response model structure, required fields, optional fields, and JSON serialization.

**Common Response Models:**
- [x] `ModalityStateResponse` - generic state wrapper
- [x] `ModalityActionResponse` - action result structure
- [x] `ModalityQueryResponse` - query result pagination
- [x] `ErrorResponse` - error structure with details

**Simulation Responses:**
- [x] `StartSimulationResponse` - simulation_id, status, current_time
- [x] `StopSimulationResponse` - final_time, event counts
- [x] `SimulationStatusResponse` - is_running, is_paused, metrics
- [x] `ResetSimulationResponse` - cleared_events count

**Time Responses:**
- [x] `TimeStateResponse` - current_time, time_scale, is_paused
- [x] `SetTimeResponse` - previous_time, skipped_events
- [x] `SkipToNextResponse` - events_executed, next_event_time

**Event Responses:**
- [x] `EventResponse` - event details with timestamps
- [x] `EventListResponse` - events array with status counts
- [x] `EventSummaryResponse` - statistics by modality

**Environment Responses:**
- [x] `EnvironmentStateResponse` - modalities dict, summary
- [x] `ModalityListResponse` - modalities array, count
- [x] `ModalitySummary` - modality_type, state_summary
- [x] `ValidationResponse` - valid flag, errors list

**Modality-Specific Responses:**
- [x] `ChatStateResponse` - conversations, messages
- [x] `ChatQueryResponse` - filtered messages
- [x] `LocationStateResponse` - current location, history
- [x] `LocationQueryResponse` - locations array
- [x] `WeatherStateResponse` - locations dict
- [x] `WeatherQueryResponse` - reports array, error field

---

## Testing Infrastructure

### Test Utilities
- [x] API test fixtures (`tests/api/conftest.py`)
  - [x] `client_with_engine` fixture
  - [x] `fresh_engine` fixture
  - [x] FastAPI test client setup
- [x] API test helpers (`tests/api/helpers.py`)
  - [x] Event request builder (`make_event_request()`)
  - [x] Modality data creators (email, sms, chat, location, calendar, time, weather)

---

## All Tests Complete ✅

All API tests have been implemented and are passing. See the detailed breakdowns below.

### Unit Tests (`tests/api/unit/`) - 285 tests ✅ Complete
- [x] Request validation (`test_request_models.py`) - 129 tests
- [x] Response serialization (`test_response_models.py`) - 55 tests
- [x] Dependency injection (`test_dependencies.py`) - 30 tests
- [x] Error response formatting (`test_error_handling.py`) - 71 tests

### Cross-Cutting Integration Tests (`tests/api/cross_cutting/`) - 105 tests ✅ Complete

#### Error Handling (`test_error_scenarios.py`) - 49 tests ✅ Complete
Tests that error responses are consistent and well-formed across all endpoints.

**HTTP 400 Bad Request - Invalid Input (18 tests):**
- [x] Invalid JSON body returns consistent error format (events)
- [x] Invalid JSON body returns consistent error format (simulation)
- [x] Invalid JSON body returns consistent error format (time advance)
- [x] Missing required fields return field-specific errors (events)
- [x] Missing required fields return field-specific errors (time advance)
- [x] Missing required fields return field-specific errors (time set)
- [x] Invalid field types return type validation errors (priority)
- [x] Invalid field types return type validation errors (time scale)
- [x] Out-of-range values - negative priority
- [x] Out-of-range values - priority > 100
- [x] Out-of-range values - invalid latitude
- [x] Out-of-range values - invalid longitude
- [x] Invalid enum values (modality) handled correctly
- [x] Negative time scale rejected
- [x] Zero time scale rejected
- [x] Negative time advance rejected
- [x] Zero time advance rejected
- [x] Empty request body handled gracefully

**HTTP 404 Not Found - Resource Not Found (8 tests):**
- [x] Nonexistent event_id returns consistent 404 format
- [x] Nonexistent event_id on DELETE returns 404
- [x] Invalid modality name returns consistent 404 format (state)
- [x] Invalid modality name returns consistent 404 format (query)
- [x] All 404 responses have same structure (detail field)
- [x] Nonexistent chat message handled gracefully
- [x] Skip to next with empty queue returns 404
- [x] Next event with empty queue returns 404

**HTTP 409 Conflict - State Conflicts (5 tests):**
- [x] Starting already-running simulation returns error
- [x] Advancing time when paused returns error
- [x] Deleting already-executed event returns error
- [x] Setting time to past returns error
- [x] Conflict errors provide helpful context

**HTTP 422 Unprocessable Entity - Validation Errors (5 tests):**
- [x] Pydantic validation errors have consistent format
- [x] Nested validation errors show field path
- [x] Multiple validation errors returned together
- [x] Invalid datetime format rejected
- [x] Null value for required field rejected

**Error Response Structure (6 tests):**
- [x] All error responses have detail/error field
- [x] Error details are human-readable
- [x] Sensitive info not leaked in error messages
- [x] Error responses include meaningful messages
- [x] 422 errors consistent across endpoints
- [x] 404 errors consistent across endpoints

**Edge Cases (7 tests):**
- [x] Empty request body handled gracefully
- [x] Very long string fields handled
- [x] Unicode in requests handled correctly
- [x] Special characters in event ID lookup handled safely
- [x] Extremely large numbers handled
- [x] Extremely small positive numbers handled
- [x] Infinity and NaN values rejected
- [x] Array instead of object body rejected

#### State Consistency (`test_state_consistency.py`) - 33 tests ✅ Complete
Tests that state changes are properly reflected across all related endpoints.

**Event Lifecycle Consistency (6 tests):**
- [x] Created event appears in GET /events list
- [x] Created event appears in GET /events/summary counts
- [x] Executed event status updated in GET /events/{id}
- [x] Executed event reflected in environment state
- [x] Cancelled event removed from pending counts
- [x] Immediate event increments executed count after time advance

**Time State Consistency (6 tests):**
- [x] Time advance reflected in GET /simulator/time
- [x] Time advance reflected in GET /simulation/status
- [x] Time advance reflected in GET /environment/state current_time
- [x] Pause state consistent across time and status endpoints
- [x] Time scale consistent across time and status endpoints
- [x] Set time reflected in all time-reporting endpoints

**Environment State Consistency (8 tests):**
- [x] Email event updates email modality state
- [x] SMS event updates sms modality state
- [x] Chat event updates chat modality state
- [x] Location event updates location modality state
- [x] Calendar event updates calendar modality state
- [x] Weather event updates weather modality state
- [x] Modality state matches full environment state snapshot
- [x] Modality query results match modality state

**Simulation Lifecycle Consistency (6 tests):**
- [x] Start sets is_running=true in status
- [x] Stop sets is_running=false in status
- [x] Reset resets event statuses and time
- [x] Reset preserves modality registrations
- [x] Stop returns accurate event counts
- [x] Status reflects auto_advance mode

**Cross-Modality Consistency (4 tests):**
- [x] Multiple events at same time all execute
- [x] Event priorities respected across modalities
- [x] Time advance executes events from all modalities
- [x] Environment state shows all modality changes

**Edge Cases (3 tests):**
- [x] State consistent after rapid successive operations
- [x] State consistent after skip-to-next operations
- [x] State consistent with mixed immediate and scheduled events

#### Concurrent Requests (`test_concurrency.py`) - 23 tests ✅
Tests that the system handles concurrent requests correctly.

**Concurrent Read Operations (5 tests):**
- [x] Multiple simultaneous GET /simulation/status
- [x] Multiple simultaneous GET /environment/state
- [x] Multiple simultaneous GET /events
- [x] Reads don't block other reads
- [x] Reads return consistent snapshots

**Concurrent Write Operations (5 tests):**
- [x] Multiple simultaneous event creations
- [x] Events created concurrently all get unique IDs
- [x] Concurrent time advances handled correctly
- [x] Concurrent pause/resume handled correctly
- [x] Last-write-wins or proper conflict detection

**Read-Write Consistency:**
- [x] Read during write returns consistent state
- [x] Event creation visible in subsequent reads
- [x] Time advance visible in subsequent reads
- [x] No partial state exposed during updates

**Race Condition Prevention:**
- [x] Double-start simulation handled (one succeeds, one 409)
- [x] Double-stop simulation handled gracefully
- [x] Concurrent delete of same event handled
- [x] Concurrent cancellation of same event handled

**Resource Contention:**
- [x] High-frequency event creation doesn't deadlock
- [x] Rapid time advances don't corrupt state
- [x] Queue operations thread-safe
- [x] Modality state updates atomic

### Multi-Step Workflow Tests (`tests/api/workflows/`) - 47 tests (Scenario 1, 2 & 3 Complete)

Workflow tests validate realistic multi-step API usage scenarios. Each scenario is fully documented with detailed timelines, event contents, and expected state checkpoints.

#### Workflow Test Infrastructure

The workflow test system provides reusable components for building and validating complex API scenarios:

**Test Files:**
- `tests/api/workflows/test_scenario_1.py` - 12 tests (Scenario 1 implementation)
- `tests/api/workflows/test_scenario_2.py` - 17 tests (Scenario 2 implementation)
- `tests/api/workflows/test_scenario_3.py` - 18 tests (Scenario 3 implementation)
- `tests/api/workflows/scenarios/scenario_1_basic.py` - Scenario definition
- `tests/api/workflows/scenarios/scenario_2_multimodality.py` - Scenario definition
- `tests/api/workflows/scenarios/scenario_3_interactive.py` - Scenario definition
- `tests/api/workflows/builders.py` - Fluent event builders
- `tests/api/workflows/validators.py` - State validation helpers
- `tests/api/workflows/runner.py` - Scenario execution engine

**Event Builders (`builders.py`):**
- `EmailEventBuilder` - Fluent builder for email events with `with_subject()`, `with_sender()`, `with_recipients()`, `with_body()`, `with_headers()` methods
- Builders automatically handle event data structure and metadata

**State Validators (`validators.py`):**
- `StateValidator` - Wraps API response for fluent assertions
- `email_count(expected)` - Verify total email count
- `email_from(sender)` - Verify email from specific sender exists
- `event_status(expected)` - Verify event execution status

**Scenario Runner (`runner.py`):**
- `WorkflowRunner` - Executes scenario steps sequentially
- Fetches simulation time to use as base time for event scheduling
- Handles time offsets relative to simulation start
- Supports validation callbacks at checkpoints

#### Scenario 1: Basic Manual Time Control (`test_scenario_1.py`) - 12 tests ✅ Complete
**Complexity**: Simple | **Modalities**: Email | **Events**: 3

Tests fundamental simulation lifecycle and manual time advancement:

**TestScenario1BasicManualControl (2 tests):**
- [x] Full scenario runs end-to-end successfully
- [x] Simulation starts in manual mode (status == "running")

**TestScenario1IndividualSteps (4 tests):**
- [x] All 3 scheduled emails are created with correct timestamps
- [x] Events start in pending state before time advance
- [x] First email executes after 90-second time advance
- [x] All emails execute after advancing past all scheduled times

**TestEventExecutionUpdatesEnvironment (6 tests):**
- [x] Email event execution updates environment state (email count increases)
- [x] Email content is correctly stored (sender matches)
- [x] SMS event execution updates SMS state
- [x] Calendar event execution updates calendar state
- [x] Location event execution updates location state
- [x] Chat event execution updates chat state

**Key Implementation Notes:**
- `/events/immediate` schedules events at current time with high priority but does NOT execute them immediately
- Events execute only during time advancement (manual or auto-advance)
- Tests must advance time (even 1 second) after immediate events to verify execution
- Simulation time starts at 2025-01-01T12:00:00+00:00 (not wall-clock time)
- Use `datetime.fromisoformat(response.json()["current_time"])` to get base time for scheduling

**Documentation**: `tests/api/workflows/SCENARIO_1_BASIC_MANUAL_CONTROL.md`

#### Scenario 2: Multi-Modality Morning Simulation (`test_scenario_2.py`) - 17 tests ✅ Complete
**Complexity**: Medium | **Modalities**: SMS, Calendar, Email, Location, Weather, Chat | **Events**: 10

Simulates a realistic 2-hour morning (8:00 AM - 10:00 AM) with events across 6 modalities:

**TestScenario2MultiModalityMorning (2 tests):**
- [x] Full scenario runs end-to-end successfully with all 30 workflow steps
- [x] Quiet mode workflow completes without validation output

**TestScenario2IndividualSteps (6 tests):**
- [x] SMS event creates conversation with spouse message
- [x] Calendar event creates team standup meeting
- [x] Email event adds meeting agenda to inbox
- [x] Location event updates current location
- [x] Weather event updates weather conditions
- [x] Chat event adds assistant contextual message

**TestMultiModalityStateAccumulation (3 tests):**
- [x] Multiple location events accumulate in history
- [x] Mixed modality events don't interfere with each other
- [x] Skip-to-next executes events in chronological order

**TestSimulationResetBehavior (3 tests):**
- [x] Reset clears all modality state
- [x] Reset stops simulation
- [x] Simulation can restart after reset

**TestSkipToNextEdgeCases (2 tests):**
- [x] Skip with no pending events returns 404
- [x] Multiple events at same time all execute

**TestMidPointStateVerification (1 test):**
- [x] Mid-point state verification after first 4 events

**Key Implementation Notes:**
- Events: SMS, Calendar, Email, 3x Location, Weather, 2x Chat (10 total)
- Uses fluent EventBuilder API for all 6 modalities
- Validates state changes after each event execution
- Tests skip-to-next navigation for event-driven progression
- Verifies reset clears queue and all modality states
- Location state: `current.named_location` (not `current_location.location_name`)
- SMS state: `messages` dict at top level (not nested in conversations)
- Calendar state: `events` is a dict keyed by event_id (not a list)
- Chat state: `messages` list at top level (not nested in conversations)
- `/simulation/start` requires JSON body (even empty `{}`)

**Documentation**: `tests/api/workflows/SCENARIO_2_MULTIMODALITY_MORNING.md`

#### Scenario 3: Interactive Agent Conversation (`test_scenario_3.py`) - 18 tests ✅ Complete
**Complexity**: Complex | **Modalities**: Chat, Calendar, Email, Location | **Events**: ~15 + 5 setup

Simulates interactive AI assistant session with cross-modality actions:

**TestScenario3InteractiveAgentConversation (2 tests):**
- [x] Full scenario runs end-to-end successfully with all 35 workflow steps
- [x] Quiet mode workflow completes without validation output

**TestScenario3SetupPhase (3 tests):**
- [x] Setup creates calendar event (Dentist Appointment)
- [x] Setup creates three unread emails (HR, Bob, Newsletter)
- [x] Setup creates location (TechCorp Office)

**TestScenario3ChatConversation (3 tests):**
- [x] User schedule query creates chat message
- [x] Assistant response lists dentist appointment
- [x] Conflict detection conversation flow works correctly

**TestScenario3CalendarOperations (2 tests):**
- [x] Meeting with Bob created at 3 PM (after conflict resolution)
- [x] Calendar has both events after scheduling (Dentist + Bob meeting)

**TestScenario3EmailOperations (3 tests):**
- [x] Email receive adds message to inbox
- [x] Mark read via API action (using message_ids)
- [x] Star via API action (using message_ids)

**TestScenario3ProactiveReminders (1 test):**
- [x] Proactive reminder appears in chat at correct time

**TestScenario3DailySummary (2 tests):**
- [x] User can request daily summary
- [x] Assistant provides summary with correct content

**TestScenario3StateConsistency (2 tests):**
- [x] Multi-modality state is consistent after full setup
- [x] Environment state snapshot contains all modalities

**Key Implementation Notes:**
- Uses setup_events for pre-populating state (5 immediate events)
- Tests multi-turn conversational flow (11 chat messages total)
- Validates calendar conflict detection and resolution
- Email actions require message_ids (dynamic lookup needed)
- Time jumps span ~3.5 hours (1:30 PM to 5:00 PM)
- Demonstrates cross-modality context in assistant responses

**Documentation**: `tests/api/workflows/SCENARIO_3_INTERACTIVE_AGENT_CONVERSATION.md`

### Future Work (Optional)
The following documentation tasks are optional enhancements for developer experience:
- [ ] API usage examples (manual time control, event-driven simulation, etc.)
- [ ] Postman/Thunder Client collection
- [ ] API client library

---

## Completion Summary

**API Testing is COMPLETE** with 907 tests covering:
- All route categories (events, time, environment, simulation, modalities)
- All modality-specific actions (chat, email, SMS, calendar, location, weather)
- Request/response model validation
- Error handling consistency
- State consistency across operations
- Concurrent request handling
- Multi-step workflow scenarios

---

## Notes

- Integration tests use the FastAPI TestClient for realistic HTTP request/response cycles
- All tests use fixtures from `tests/fixtures/` for consistent test data
- Tests verify both success cases and error handling
- The `client_with_engine` fixture automatically starts the simulation before each test
- Always update this document (`API_TESTING_PROGRESS.md`) once you finish implementing API tests
