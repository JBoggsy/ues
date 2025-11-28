# API Testing Guidelines for UES

Guidelines for implementing integration tests for the UES REST API, distilled from implementing 63 passing event route tests.

## ⚠️ CRITICAL: Verifying Test Completion

### Pytest Passes Stub Tests!

**WARNING:** Pytest considers any test that doesn't raise an exception as "passing". This means:

```python
def test_something(self, client_with_engine):
    """Test description."""
    client, _ = client_with_engine
    # TODO: implement
    pass  # ← This shows as PASSING in pytest! ✓
```

### How to Verify Tests Are Actually Implemented

**❌ NEVER trust pytest output alone:**
```bash
$ pytest tests/api/environment/ -v
# 31 passed  ← This could include stub tests!
```

**✅ ALWAYS verify by reading the actual test file:**
1. Open the test file and scan for `pass` statements
2. Look for `TODO` comments in test bodies
3. Check that tests have actual assertions beyond basic structure checks
4. Verify tests execute the functionality they claim to test

**✅ Use grep to find stubs:**
```bash
# Find tests with pass statements (potential stubs)
grep -n "^\s*pass$" tests/api/environment/*.py

# Find TODO comments in test bodies
grep -n "# TODO:" tests/api/environment/*.py
```

**✅ Before marking tests complete in progress docs:**
1. Read the test file completely
2. Verify each test has meaningful assertions
3. Confirm tests actually exercise the endpoint/feature
4. Check that TODOs are removed or implemented

### Signs of Incomplete Tests:
- Test body contains only `pass`
- Test has `# TODO:` comments in the implementation (not docstring)
- Test only checks response structure but doesn't verify behavior
- Test creates setup but doesn't make assertions about results
- Test docstring is more detailed than the implementation

**Remember:** Green checkmarks mean "didn't fail", not "fully implemented"!

## Core Testing Infrastructure

### The `client_with_engine` Fixture Pattern

**Always use this fixture for API tests:**
```python
def test_something(client_with_engine):
    client, engine = client_with_engine
    response = client.get("/some/endpoint")
    assert response.status_code == 200
```

**What it provides:**
- TestClient with fresh SimulationEngine injected via dependency override
- Simulation automatically started in manual mode (`auto_advance=False`)
- Automatic cleanup (stops simulation, clears overrides)

**Location:** `tests/api/conftest.py`

## Essential Patterns

### 1. Getting Current Time

**✅ ALWAYS use the API:**
```python
time_response = client.get("/simulator/time")
current_time = datetime.fromisoformat(time_response.json()["current_time"])
```

**❌ NEVER access engine directly:**
```python
current_time = engine.current_time  # AttributeError - doesn't exist!
```

### 2. Comparing Timestamps

**✅ Parse datetime objects before comparing:**
```python
assert datetime.fromisoformat(data["scheduled_time"]) == event_time
```

**❌ Don't compare ISO strings:**
```python
assert data["scheduled_time"] == event_time.isoformat()  # Fails: 'Z' vs '+00:00'
```

### 3. Using Helper Functions

**All event data helpers are in `tests/api/helpers.py`:**
```python
from tests.api.helpers import (
    make_event_request,
    email_event_data,
    sms_event_data,
    chat_event_data,
    location_event_data,
    calendar_event_data,
    time_event_data,
    weather_event_data,
)

# Create complete event request
request = make_event_request(
    event_time,
    "email",
    email_event_data(subject="Test", from_address="sender@example.com"),
    priority=75,
)
```

**Benefits:**
- Correct field names (helpers already debugged and validated)
- Sensible defaults for all required fields
- Easy customization with optional parameters
- Comprehensive docstrings

## Critical Field Name Reference

### Modality-Specific Field Names
Different modalities use different field names for similar concepts:

| Modality | Action Field | Address Field | Notes |
|----------|-------------|---------------|-------|
| Email | `operation` | `from_address`, `to_addresses` | Plural `to_addresses` |
| SMS | `action` | `from_number`, `to_numbers` | Plural `to_numbers`, nested `message_data` |
| Chat | N/A | N/A | Simple `content` field (string) |
| Calendar | N/A | N/A | Use `start`/`end`, NOT `start_time`/`end_time` |
| Weather | N/A | N/A | Complex nested `report` with `lat`/`lon`/`timezone`/`timezone_offset` |
| Location | N/A | N/A | Flat `latitude`/`longitude` at top level |
| Time | N/A | N/A | Preference updates |

## HTTP Status Code Patterns

Follow these conventions (per `docs/API_ERROR_HANDLING.md`):

- **200 OK**: Request succeeded
- **400 Bad Request**: Business rule violation (simulation not running, past time, invalid operation)
- **404 Not Found**: Resource doesn't exist (invalid modality, event not found, empty queue)
- **422 Unprocessable Entity**: Pydantic validation failure (missing fields, type errors)
- **500 Internal Server Error**: Unexpected failure

### Testing Error Responses

**For validation errors, always expect 422:**
```python
# Pydantic validation errors should return 422
response = client.post("/endpoint", json={"invalid": "data"})
assert response.status_code == 422
```

**Critical:** If validation errors return 400, the API needs a `RequestValidationError` handler:
```python
# In api/exceptions.py
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

async def request_validation_exception_handler(request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

# In main.py - MUST be registered BEFORE other exception handlers
app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
```

**Always check error details:**
```python
assert response.status_code == 404
assert "not found" in response.json()["detail"].lower()
assert "modality" in response.json()["detail"].lower()
```

### Pydantic Validation Quirks

**Be aware of Pydantic's flexible parsing:**
- Unix timestamps are valid datetime strings: `"12345"` → valid datetime
- ISO format variations accepted: `"2024-01-01T12:00:00Z"`, `"2024-01-01T12:00:00+00:00"`
- Empty strings may be rejected differently than null values
- Test both missing fields and null values separately

## Event Execution Testing

### Current State of Event Execution
- ✅ **Location events**: Execute successfully
- ⚠️ **Chat events**: May fail without proper implementation
- ❓ **Other modalities**: Execution not fully tested

### Pattern for Execution-Dependent Tests

```python
def test_something_with_execution(self, client_with_engine):
    """Test that verifies behavior after event execution.
    
    Note: This test may fail if event execution is broken/incomplete.
    """
    client, _ = client_with_engine
    
    # Create and execute event
    client.post("/events/immediate", json={"modality": "location", "data": location_event_data()})
    client.post("/simulator/time/advance", json={"seconds": 1})
    
    # Accept both executed and failed statuses
    data = client.get(f"/events/{event_id}").json()
    assert data["status"] in ["executed", "failed"]
    assert data["executed_at"] is not None
```

**Document execution dependencies in docstrings.**

## Test Organization

### File Structure
Split tests by **functional grouping**, not HTTP method:
- `test_event_listing.py` - GET /events (filtering, pagination)
- `test_event_creation.py` - POST /events, POST /events/immediate
- `test_event_operations.py` - GET/DELETE /events/{id}
- `test_event_queries.py` - GET /events/next, /events/summary

**Target:** ~200-300 lines per file, focused scope

### Class Organization
```python
class TestPostEvents:
    """Tests for POST /events endpoint."""
    
    def test_create_event_returns_event_id(self, client_with_engine):
        """Test that POST /events returns an event with a unique ID."""
        # Test implementation
    
    def test_create_event_email_modality(self, client_with_engine):
        """Test that POST /events works for email modality."""
        # Test implementation

class TestPostEventsImmediate:
    """Tests for POST /events/immediate endpoint."""
    # Separate class for related but distinct endpoint
```

## Test Implementation Checklist

### Before Writing Tests
1. ✅ Read relevant documentation (`docs/MODALITY_*.md`, `docs/SIMULATION_*.md`)
2. ✅ Read model implementations (`models/*.py`) to understand validation rules
3. ✅ Read API route implementations (`api/routes/*.py`) to understand behavior
4. ✅ Identify expected constraints (e.g., `time_scale > 0`, valid datetime formats)

### For Each Test
1. ✅ Use `client_with_engine` fixture
2. ✅ Get current time via API (not engine)
3. ✅ Use helper functions for event data
4. ✅ Compare parsed datetime objects (not ISO strings)
5. ✅ Check response status code first
6. ✅ Then verify response data structure
7. ✅ Use descriptive test names
8. ✅ Add docstrings for non-obvious scenarios

### For Each Test File
1. ✅ Import necessary helpers at top
2. ✅ Organize tests into logical classes
3. ✅ Keep file focused (one endpoint category)
4. ✅ Document execution dependencies
5. ✅ **Verify tests are actually implemented** (see warning at top of this document)
6. ✅ Remove all `TODO` comments and `pass` statements from test bodies
7. ✅ Run tests and confirm meaningful assertions execute
8. ✅ Update `API_TESTING_PROGRESS.md` **only after verifying implementation**

## Common Pitfalls to Avoid

1. **Don't trust pytest "passing" output alone** - verify test bodies are implemented
2. **Don't mark tests complete without reading the code** - check for TODOs and pass statements
3. **Don't access `engine.current_time`** - use API
4. **Don't compare ISO string formats** - parse first
5. **Don't hardcode event data** - use helpers
6. **Don't assume validation returns 400** - check for proper 422 error handler
7. **Don't assume execution works** - document dependencies
8. **Don't create monolithic test files** - split by function
9. **Don't forget cleanup** - fixture handles it automatically
10. **Don't skip reading documentation** - models/routes reveal critical constraints
11. **Don't test implementation details** - test API behavior and contracts
12. **Don't assume Pydantic rejects all invalid input** - it's surprisingly flexible

## Debugging Failed Tests

### When tests return unexpected status codes:
1. Check if `RequestValidationError` handler is registered in `main.py`
2. Verify handler is added **before** other exception handlers
3. Test the route manually to confirm actual vs. expected behavior
4. Check Pydantic model Field validators (e.g., `gt=0`, `le=100`)

### When validation seems inconsistent:
1. Check if input matches Pydantic's flexible parsing (Unix timestamps, ISO variations)
2. Test both missing fields (`{}`) and null values (`{"field": null}`) separately
3. Verify the actual error messages in response for clues
4. Consider testing at model level before integration testing

### When behavior differs from documentation:
1. Documentation may be aspirational - check actual implementation
2. Model code is source of truth for validation rules
3. Route code is source of truth for business logic
4. Update documentation after confirming correct behavior

## Progressive Implementation Strategy

### 0. Research Phase (Do This First!)
Read documentation and implementation before writing tests:
```python
# 1. Read docs/MODALITY_*.md or docs/SIMULATION_*.md
# 2. Read models/*.py for validation rules (Field constraints, custom validators)
# 3. Read api/routes/*.py for business logic and error handling
# 4. Identify expected behavior, constraints, and edge cases
```

### 1. Test Success Cases First
```python
def test_endpoint_success(self, client_with_engine):
    """Verify happy path works."""
    response = client.post("/endpoint", json=valid_data)
    assert response.status_code == 200
```

### 2. Then Test Validation Errors
```python
def test_endpoint_validates_required_fields(self, client_with_engine):
    """Verify missing fields rejected with 422."""
    response = client.post("/endpoint", json={})
    assert response.status_code == 422  # Pydantic validation

def test_endpoint_validates_null_values(self, client_with_engine):
    """Verify null values rejected with 422."""
    response = client.post("/endpoint", json={"field": None})
    assert response.status_code == 422
```

### 3. Then Test Business Rules
```python
def test_endpoint_enforces_business_rules(self, client_with_engine):
    """Verify business logic constraints (400 errors)."""
    response = client.post("/endpoint", json=invalid_but_well_formed_data)
    assert response.status_code == 400
```

### 4. Finally Test Edge Cases
```python
def test_endpoint_handles_edge_cases(self, client_with_engine):
    """Verify boundary conditions."""
    # Large datasets, extreme values, state persistence, etc.
```

## Example: Complete Test Implementation

```python
"""Integration tests for example endpoint."""

from datetime import datetime, timedelta
from tests.api.helpers import make_event_request, email_event_data


class TestExampleEndpoint:
    """Tests for POST /example endpoint."""
    
    def test_example_success(self, client_with_engine):
        """Test that POST /example creates resource successfully."""
        client, _ = client_with_engine
        
        # Get current time via API
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create request using helper
        request_time = current_time + timedelta(hours=1)
        request = make_event_request(
            request_time,
            "email",
            email_event_data(subject="Test"),
        )
        
        # Make request
        response = client.post("/example", json=request)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["id"] is not None
        assert datetime.fromisoformat(data["created_at"]) >= current_time
    
    def test_example_validation_error(self, client_with_engine):
        """Test that POST /example validates required fields."""
        client, _ = client_with_engine
        
        response = client.post("/example", json={})
        
        assert response.status_code in [400, 422]
        assert "detail" in response.json()
```

## When Adding New Helpers

If a new modality or endpoint needs helper functions:

1. Add to `tests/api/helpers.py`
2. Follow existing naming pattern: `{modality}_event_data()`
3. Provide sensible defaults for all required fields
4. Use keyword arguments for customization
5. Add comprehensive docstring with examples
6. Include correct field names from model implementation

## Performance Expectations

- **Individual tests**: < 50ms typically
- **Test file**: ~200-300ms for 10-15 tests
- **Full suite**: ~1-2 seconds for 113 tests (as of time route completion)
- Fresh engine per test ensures isolation
- Tests can run in parallel (not currently configured)

## Documentation Standards

- **Test names**: Descriptive, starting with `test_`, indicate what is verified
- **Docstrings**: Required for all tests, explain what is being verified
- **Inline comments**: Minimal, use only for non-obvious logic
- **Progress tracking**: Update `API_TESTING_PROGRESS.md` after completing each file
- **Known limitations**: Document in test docstrings with "Note:" prefix

## Key Lessons from Implementation

### Documentation-First Testing
Always read documentation and implementation **before** writing tests:
1. Documentation reveals expected behavior and design intent
2. Model code shows actual validation rules (Field constraints matter!)
3. Route code shows business logic and error handling
4. This prevents writing tests against wrong assumptions

### Exception Handler Registration Order Matters
When adding custom exception handlers in FastAPI:
- `RequestValidationError` handler **must** be registered first
- Other handlers come after
- Wrong order = validation errors return wrong status codes

### Test What the API Returns, Not What You Expect
- Response field names may differ from documentation
- Example: API returns `time_scale` but you might expect `new_scale`
- Always verify actual response structure before writing assertions
- Helper functions encode these discoveries for reuse

### Validation Happens at Multiple Layers
- Pydantic validates type/structure (422 errors)
- Route logic validates business rules (400 errors)
- Don't assume all "invalid input" returns the same status code
- Read the route implementation to understand which layer catches what
