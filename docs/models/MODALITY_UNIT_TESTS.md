# Unit Testing Guide for UES

This document captures the design patterns, standards, and lessons learned from developing unit tests for the User Environment Simulator (UES) project.

## Overview

UES uses a comprehensive testing approach that validates both general behavioral patterns (shared across all modalities) and modality-specific features. Tests are written using pytest and follow strict documentation and organization conventions.

## Testing Philosophy

### GENERAL PATTERN vs MODALITY-SPECIFIC

All test docstrings must clearly indicate whether they test:

- **GENERAL PATTERN**: Behavior that applies to all ModalityInput or ModalityState subclasses. These patterns should be replicated across all modality tests.
- **MODALITY-SPECIFIC**: Unique features or validation rules specific to that modality.

**Example:**
```python
def test_minimal_instantiation(self):
    """GENERAL PATTERN: All ModalityInput subclasses should instantiate with timestamp."""
    # Test code here

def test_valid_operations(self):
    """MODALITY-SPECIFIC: Verify all 18 email operations are valid."""
    # Test code here
```

This convention helps developers understand which test patterns to replicate when adding new modalities and which features are unique.

## Test Organization

### File Structure

Each modality has two test files:
- `test_<modality>_input.py` - Tests for the input model
- `test_<modality>_state.py` - Tests for the state model

**Current test coverage:**
- Location: 69 tests (35 input + 34 state)
- Time: 78 tests (39 input + 39 state)
- Chat: 93 tests (46 input + 47 state)
- Weather: 77 tests (33 input + 44 state)
- Email: 56 tests (23 input + 33 state)
- **Total: 373 tests**

### Test Class Organization

Tests are organized into focused test classes:

**For Input Tests:**
1. `TestInstantiation` - Basic object creation
2. `TestValidation` - Validation logic and constraints
3. `TestSerialization` - Pydantic model_dump/model_validate
4. `TestFromFixtures` - Using pre-built fixtures
5. `TestEdgeCases` - Boundary conditions and edge cases

**For State Tests:**
1. `TestInstantiation` - Basic state creation
2. `TestHelperClasses` - Pydantic helper class behavior (if applicable)
3. `TestApplyInput` - Input processing and state updates
4. `TestGetSnapshot` - State snapshot generation
5. `TestValidation` - State consistency validation
6. `TestQuery` - State querying functionality
7. `TestSerialization` - State persistence
8. `TestFromFixtures` - Using pre-built fixtures
9. `TestIntegration` - Complex real-world scenarios

## Design Patterns and Standards

### 1. Pydantic Helper Classes

**Rule**: All helper classes used within modality states MUST be Pydantic BaseModel subclasses.

**Why**: State serialization requires all nested objects to be serializable via `model_dump()` and `model_validate()`.

**Examples of helper classes:**
- `LocationHistoryEntry` (Location)
- `TimeSettingsHistoryEntry` (Time)
- `ChatMessage`, `ConversationMetadata` (Chat)
- `WeatherReportHistoryEntry`, `WeatherLocationState` (Weather)
- `Email`, `EmailThread` (Email)

**Pattern:**
```python
from pydantic import BaseModel, Field

class HelperClass(BaseModel):
    """Helper class description.
    
    Args:
        field1: Description of field1.
        field2: Description of field2.
    """
    
    field1: str = Field(description="Field 1 description")
    field2: int = Field(default=0, description="Field 2 description")
    
    # Methods for state modification (not serialization)
    def update_something(self) -> None:
        """Update internal state."""
        self.field2 += 1
```

**Anti-pattern:**
```python
# ❌ WRONG - Plain Python class breaks serialization
class HelperClass:
    def __init__(self, field1: str, field2: int = 0):
        self.field1 = field1
        self.field2 = field2
```

### 2. Serialization Testing

**Rule**: All ModalityInput and ModalityState instances must support `model_dump()` and `model_validate()`.

**Pattern for Input Tests:**
```python
def test_simple_serialization(self):
    """GENERAL PATTERN: Verify input can be serialized and deserialized."""
    original = ModalityInput(
        timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        # ... other fields
    )
    
    dumped = original.model_dump()
    restored = ModalityInput.model_validate(dumped)
    
    assert restored.timestamp == original.timestamp
    # Assert other critical fields
```

**Pattern for State Tests:**
```python
def test_populated_state_serialization(self):
    """GENERAL PATTERN: Verify populated state persists correctly."""
    original = ModalityState(
        last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
    )
    
    # Populate state with data
    # ...
    
    dumped = original.model_dump()
    restored = ModalityState.model_validate(dumped)
    
    # Verify all critical state preserved
    assert len(restored.data_structure) == len(original.data_structure)
```

### 3. Fixture Organization

**Location**: `tests/fixtures/modalities/<modality>.py`

**Pattern:**
```python
"""Fixtures for <Modality> modality."""

from datetime import datetime, timezone

import pytest

from models.modalities.<modality>_input import ModalityInput
from models.modalities.<modality>_state import ModalityState


def create_modality_input(**kwargs) -> ModalityInput:
    """Create a ModalityInput with sensible defaults.
    
    Args:
        **kwargs: Fields to override defaults.
    
    Returns:
        ModalityInput instance ready for testing.
    """
    defaults = {
        "timestamp": datetime.now(timezone.utc),
        # ... other sensible defaults
    }
    defaults.update(kwargs)
    return ModalityInput(**defaults)


def create_modality_state(**kwargs) -> ModalityState:
    """Create a ModalityState with sensible defaults.
    
    Args:
        **kwargs: Fields to override defaults.
    
    Returns:
        ModalityState instance ready for testing.
    """
    defaults = {
        "last_updated": datetime.now(timezone.utc),
    }
    defaults.update(kwargs)
    return ModalityState(**defaults)


# Pytest fixtures
@pytest.fixture
def simple_input():
    """Provide a simple input for testing."""
    return create_modality_input(
        # specific test data
    )


@pytest.fixture
def modality_state():
    """Provide a fresh state instance for testing."""
    return create_modality_state()
```

**Registration**: Add to `tests/conftest.py`:
```python
pytest_plugins = [
    "tests.fixtures.modalities.<modality>",
]
```

### 4. API Understanding Before Testing

**Critical Rule**: Always examine the actual implementation API before writing tests.

**Checklist before writing tests:**
1. ✅ How many arguments does `apply_input()` take?
2. ✅ What does `get_snapshot()` return? (structure, not just presence)
3. ✅ What does `validate_state()` return? (tuple vs list vs dict)
4. ✅ What are the actual field names? (`modality` vs `modality_type`)
5. ✅ What are default values? (`None` vs `[]` vs auto-generated)
6. ✅ What operations/enum values are valid?

**Example - Common API variations:**

```python
# EmailInput uses modality_type, not modality
assert email.modality_type == "email"  # ✅ Correct
assert email.modality == "email"       # ❌ Wrong - AttributeError

# apply_input() signatures vary by implementation
state.apply_input(input_data)                    # ✅ Common pattern
state.apply_input(input_data, timestamp)         # ❌ Wrong for most implementations

# validate_state() return types vary
errors = state.validate_state()                  # ✅ Returns list
is_valid, errors = state.validate_state()        # ❌ Wrong - ValueError
```

## Common Issues and Solutions

### Issue 1: Helper Classes Not Pydantic

**Symptom**: State serialization fails with errors about non-serializable objects.

**Example Error**:
```
TypeError: Object of type 'HelperClass' is not JSON serializable
```

**Solution**: Convert all helper classes to Pydantic BaseModel:

```python
# Before (❌)
class Email:
    def __init__(self, message_id: str, subject: str):
        self.message_id = message_id
        self.subject = subject

# After (✅)
class Email(BaseModel):
    message_id: str = Field(description="Unique message identifier")
    subject: str = Field(description="Email subject line")
```

**Prevention**: When creating a new modality state, immediately convert any helper classes to Pydantic models before writing tests.

### Issue 2: None vs Empty List Default Values

**Symptom**: Pydantic validation errors when constructing objects.

**Example Error**:
```
pydantic_core._pydantic_core.ValidationError: 1 validation error for Email
  cc_addresses
    Input should be a valid list [type=list_type, input_value=None, input_type=NoneType]
```

**Root Cause**: Pydantic models with `list[str]` type expect lists, but input data provides `None`.

**Solution**: Handle None values when constructing Pydantic objects:

```python
# In state handler
email = Email(
    message_id=input_data.message_id,
    cc_addresses=input_data.cc_addresses or [],  # ✅ Convert None to []
    bcc_addresses=input_data.bcc_addresses or [], # ✅ Convert None to []
    attachments=input_data.attachments or [],     # ✅ Convert None to []
)
```

**Alternative**: Use `Optional[list[str]]` if None is semantically meaningful:

```python
cc_addresses: Optional[list[str]] = Field(default=None, description="CC recipients")
```

### Issue 3: Incorrect API Assumptions

**Symptom**: Tests fail with unexpected errors about wrong number of arguments or missing attributes.

**Example Errors**:
```
TypeError: apply_input() takes 2 positional arguments but 3 were given
AttributeError: 'EmailInput' object has no attribute 'modality'
```

**Root Cause**: Tests written based on assumptions rather than actual API inspection.

**Solution**: Always read the actual implementation before testing:

```python
# Check actual method signature
def apply_input(self, input_data: ModalityInput) -> None:
    # Implementation extracts timestamp from input_data.timestamp
    self.last_updated = input_data.timestamp

# Write test matching actual API
state.apply_input(email_input)  # ✅ Correct - 1 argument
```

**Prevention**:
1. Use `grep_search` to find method definitions
2. Use `read_file` to examine actual signatures and return types
3. Check field names in model definitions
4. Verify enum/Literal values

### Issue 4: Test Assumes Wrong Data Structure

**Symptom**: Assertion failures because expected structure doesn't match actual.

**Example Error**:
```
AssertionError: assert 'inbox_count' in {'folders': {...}, 'total_emails': 5, ...}
```

**Root Cause**: Test expects flat structure but API returns nested structure.

**Solution**: Examine actual return structure:

```python
# Check actual get_snapshot() implementation
def get_snapshot(self) -> dict[str, Any]:
    return {
        "folders": {
            "inbox": {"message_count": 5, "unread_count": 3},
            # ...
        },
        "total_emails": 5,
    }

# Write test matching actual structure
snapshot = state.get_snapshot()
assert "folders" in snapshot  # ✅ Correct
assert snapshot["folders"]["inbox"]["message_count"] == 5  # ✅ Correct
assert "inbox_count" in snapshot  # ❌ Wrong
```

### Issue 5: Missing Required Fields in Test Data

**Symptom**: Validation errors when creating test inputs.

**Example Error**:
```
ValueError: Operation 'reply' requires in_reply_to
```

**Solution**: Check validation rules for each operation:

```python
# Email reply requires in_reply_to
reply = EmailInput(
    timestamp=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
    operation="reply",
    from_address="you@example.com",
    to_addresses=["sender@example.com"],
    subject="Re: Test",
    body_text="My reply",
    in_reply_to="msg-original",  # ✅ Required for reply operation
)
```

**Prevention**: Read the `validate_input()` implementation to understand constraints for each operation type.

### Issue 6: Removed Methods Still Called

**Symptom**: AttributeError when calling methods that were removed during Pydantic conversion.

**Example Error**:
```
AttributeError: 'Email' object has no attribute 'to_dict'
```

**Root Cause**: After converting to Pydantic, custom `to_dict()` methods should be replaced with `model_dump()`.

**Solution**: Update all usages:

```python
# Before Pydantic conversion
result = {"emails": [e.to_dict() for e in results]}  # ❌ Wrong after conversion

# After Pydantic conversion
result = {"emails": [e.model_dump() for e in results]}  # ✅ Correct
```

**Prevention**: After converting a class to Pydantic, search for all calls to custom serialization methods and replace with `model_dump()`.

## Testing Workflow

### Step-by-Step Process

1. **Understand the API**
   - Read the input model definition
   - Read the state model definition
   - Check method signatures (apply_input, get_snapshot, validate_state, query)
   - Note field names and default values
   - Identify helper classes

2. **Convert Helper Classes** (if needed)
   - Convert any plain Python helper classes to Pydantic BaseModel
   - Use Field() descriptors for all fields
   - Remove custom to_dict() methods
   - Add state-modifying methods as needed

3. **Create/Update Fixtures**
   - Add factory functions for input and state
   - Add pytest fixtures for common test scenarios
   - Register in conftest.py

4. **Write Input Tests** (~20-40 tests)
   - Instantiation (minimal, full, defaults)
   - Validation (valid values, constraints)
   - Serialization (simple, complex)
   - Fixtures (verify pre-built fixtures work)
   - Edge cases (empty values, boundaries, large data)

5. **Write State Tests** (~30-50 tests)
   - Instantiation (minimal, defaults)
   - Helper classes (if any - instantiation, methods, serialization)
   - apply_input (各operation type)
   - get_snapshot (empty, populated)
   - validate_state (empty, populated)
   - query (各query parameter)
   - Serialization (empty, populated, complex)
   - Integration (multi-step scenarios)

6. **Run Tests and Fix Issues**
   - Run tests: `uv run python -m pytest tests/test_<modality>_*.py -v`
   - For failures, check actual API against test assumptions
   - Fix issues systematically
   - Re-run until all tests pass

7. **Verify Coverage**
   - Ensure both GENERAL and MODALITY-SPECIFIC patterns documented
   - Check that all operations/query types tested
   - Verify edge cases covered

## Best Practices

### 1. Use Descriptive Test Names

```python
# ✅ Good - describes what is tested
def test_receive_email_creates_thread(self):
    """MODALITY-SPECIFIC: Verify receiving email creates new thread."""

# ❌ Poor - unclear what is tested
def test_email(self):
    """Test email."""
```

### 2. Document GENERAL vs MODALITY-SPECIFIC

Every test docstring should start with one of these tags to make patterns clear to future developers.

### 3. Test One Thing Per Test

```python
# ✅ Good - focused test
def test_mark_read(self):
    """MODALITY-SPECIFIC: Verify marking email as read."""
    # Setup, apply mark_read operation, assert is_read changed

# ❌ Poor - testing multiple operations
def test_email_operations(self):
    """Test various email operations."""
    # Tests mark_read, star, move, delete all in one test
```

### 4. Use Fixtures for Common Setup

```python
# ✅ Good - reusable fixture
@pytest.fixture
def populated_email_state(email_state):
    """Provide email state with 5 emails in inbox."""
    for i in range(5):
        email_state.apply_input(create_email_input(subject=f"Email {i}"))
    return email_state

def test_query_inbox(populated_email_state):
    """Test querying inbox."""
    result = populated_email_state.query({"folder": "inbox"})
    assert len(result["emails"]) == 5
```

### 5. Use Timezone-Aware Datetimes

```python
# ✅ Good - explicit timezone
from datetime import datetime, timezone
timestamp = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

# ❌ Poor - naive datetime can cause issues
timestamp = datetime(2025, 1, 1, 12, 0)
```

### 6. Assert Multiple Properties When Relevant

```python
# ✅ Good - comprehensive verification
assert email.is_read is False
assert email.is_starred is False
assert email.folder == "inbox"
assert len(email.labels) == 0

# ❌ Minimal - misses potential issues
assert email.folder == "inbox"
```

### 7. Test Serialization Roundtrips

Always verify that serialize → deserialize produces equivalent objects:

```python
def test_serialization(self):
    """Verify complete roundtrip serialization."""
    original = create_complex_state()
    
    dumped = original.model_dump()
    restored = StateClass.model_validate(dumped)
    
    # Verify critical fields preserved
    assert restored.field1 == original.field1
    assert len(restored.nested_data) == len(original.nested_data)
```

## Tools and Commands

### Running Tests

```bash
# Run all tests
uv run python -m pytest

# Run specific modality tests
uv run python -m pytest tests/test_email_*.py

# Run with verbose output
uv run python -m pytest tests/test_email_*.py -v

# Run specific test class
uv run python -m pytest tests/test_email_state.py::TestEmailStateApplyInput -v

# Run specific test
uv run python -m pytest tests/test_email_state.py::TestEmailStateApplyInput::test_receive_email -v

# Show short traceback
uv run python -m pytest tests/test_email_*.py --tb=short

# Stop on first failure
uv run python -m pytest tests/test_email_*.py -x
```

### Debugging Failed Tests

```bash
# Show full error output
uv run python -m pytest tests/test_email_state.py::test_name -vv

# Drop into debugger on failure
uv run python -m pytest tests/test_email_state.py --pdb

# Show print statements
uv run python -m pytest tests/test_email_state.py -s
```

## Metrics

### Current Test Coverage (by modality)

| Modality | Input Tests | State Tests | Total | Status |
|----------|-------------|-------------|-------|--------|
| Location | 35 | 34 | 69 | ✅ Complete |
| Time | 39 | 39 | 78 | ✅ Complete |
| Chat | 46 | 47 | 93 | ✅ Complete |
| Weather | 33 | 44 | 77 | ✅ Complete |
| Email | 23 | 33 | 56 | ✅ Complete |
| Calendar | 0 | 0 | 0 | ⏳ Pending |
| SMS | 0 | 0 | 0 | ⏳ Pending |
| **Total** | **176** | **197** | **373** | **5/7** |

### Recommended Test Counts

Based on patterns from completed modalities:

- **Simple modality** (Location, Time): 30-40 input tests, 35-45 state tests
- **Medium modality** (Weather, Email): 25-35 input tests, 35-50 state tests
- **Complex modality** (Chat): 45+ input tests, 50+ state tests

Target: **60-100 tests per modality** for comprehensive coverage.

## Future Improvements

1. **Add integration tests** that span multiple modalities
2. **Add performance tests** for operations on large state (e.g., 10,000 emails)
3. **Add property-based tests** using Hypothesis for edge case discovery
4. **Add mutation testing** to verify test quality
5. **Extract common test patterns** into shared base classes or mixins

## Summary

The key to successful testing in UES:

1. **Understand before implementing** - Read actual code, don't assume
2. **All helpers must be Pydantic** - State serialization requires it
3. **Document patterns clearly** - GENERAL vs MODALITY-SPECIFIC tags
4. **Test systematically** - Follow the established test class structure
5. **Handle None values** - Convert to empty collections when needed
6. **Verify roundtrip serialization** - Critical for state persistence
7. **Use fixtures wisely** - Reduce boilerplate, improve maintainability

Following these patterns ensures consistent, maintainable tests that catch real issues while clearly documenting both shared behaviors and unique modality features.
