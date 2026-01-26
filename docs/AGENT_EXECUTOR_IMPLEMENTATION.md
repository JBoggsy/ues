# AgentExecutor Implementation Plan

**Phase**: 2.6 of AgentBeats Submission  
**Status**: ✅ COMPLETE (Phases A-E: Event Attribution, Core Infrastructure, Assessment Lifecycle, Evaluation, A2A Integration)  
**Created**: January 25, 2026  
**Last Updated**: January 25, 2026

---

## Overview

The AgentExecutor orchestrates the full assessment lifecycle for AgentBeats:
1. Loading scenarios and setting up the UES environment
2. Coordinating with Purple agents via A2A protocol
3. Tracking Purple agent actions
4. Running response generator sub-agents
5. Advancing simulation time
6. Evaluating results and producing scoring artifacts

---

## Key Design Decisions

### 1. UES Interaction: Python Client Library ✅

**Decision**: Use `AsyncUESClient` for all UES interactions.

**Rationale**:
- Type-safe with Pydantic models
- Built-in API key authentication support
- Async/await matches A2A executor pattern
- Comprehensive sub-client coverage
- Easy to mock for testing

### 2. Architecture: Separated Concerns ✅

**Decision**: Modular architecture with distinct components.

**Components**:
```
Agent (coordinator)
├── AssessmentSession (state container)
├── ScenarioRegistry (scenario resolution)
├── ActionTracker (Purple action tracking)
├── ResponseAgentManager (character responses) [existing]
└── Evaluator (scoring)
```

### 3. Action Tracking: Event Attribution ✅

**Decision**: Leverage API key-based event attribution.

**Problem Identified**: Event creation ≠ event execution. Purple creates events (status: PENDING), but we query after turn completion when events may not have executed yet. We need to identify which events were created by Purple vs. scenario/Green.

**Solution**: Automatically inject `agent_id` from access context when events are created.

**Implementation**:
1. Events already have `agent_id` field (in `SimulatorEvent` model)
2. Need to inject `agent_id` from `AccessContext` during event creation
3. Add `agent_id` filter to events list endpoint
4. Update client library to support `agent_id` filter

**Benefits**:
- Deterministic identification (no timing assumptions)
- Works regardless of when events execute
- Clear audit trail for debugging
- Backward compatible (field is optional)

---

## Implementation Tasks

### Phase A: Event Attribution Infrastructure ✅ COMPLETE

#### A.1 Inject agent_id from AccessContext ✅

**Files modified**:
- `api/routes/events.py` — Added `resolve_agent_id()` helper, injected agent_id from access context
- `api/access_dependencies.py` — Added `get_optional_access_context` dependency and `OptionalAccessContextDep` type alias

**Implementation**:
- Created `get_optional_access_context()` - returns None when access control disabled, validates key when enabled
- Created `resolve_agent_id(request_agent_id, access_context)` helper - prefers context, falls back to request
- Applied to: `create_event`, `create_immediate_event`, `create_batch_events`

**Notes**:
- Works when access control is disabled (access = None, uses request agent_id)
- Access context agent_id overrides request-provided agent_id (spoofing prevention)

#### A.2 Add agent_id filter to list_events endpoint ✅

**Files modified**:
- `api/routes/events.py` — Added `agent_id` query parameter with filtering logic

**Implementation**:
```python
@router.get("", response_model=EventListResponse)
async def list_events(
    ...
    agent_id: str | None = Query(None, description="Filter by agent that created the event"),
    ...
):
    # Filter by agent_id
    if agent_id:
        events = [e for e in events if e.agent_id == agent_id]
```

#### A.3 Update EventResponse to include agent_id ✅

**Files modified**:
- `api/routes/events.py` — Added `agent_id` to `EventResponse` model and `get_event` endpoint
- `api/routes/events.py` — Added `agent_id` to `ImmediateEventRequest` model

**Implementation**:
```python
class EventResponse(BaseModel):
    ...
    agent_id: str | None = Field(
        None, description="ID of the agent that created this event"
    )
```

#### A.4 Update client library for agent_id filter ✅

**Files modified**:
- `client/_events.py` — Added `agent_id` to `EventResponse` model
- `client/_events.py` — Added `agent_id` parameter to `list_events()` in both sync and async clients

**Implementation**:
```python
def list_events(
    self,
    ...
    agent_id: str | None = None,
    ...
) -> EventListResponse:
    """List events with optional filters.
    
    Args:
        ...
        agent_id: Filter by agent that created the event.
    """
```

#### A.5 Tests for event attribution ✅

**Files created**:
- `tests/api/events/test_event_attribution.py` — 11 tests covering:
  - Event creation with agent_id in request
  - Event creation without agent_id
  - Immediate event with agent_id
  - Batch events with agent_id
  - Filter events by agent_id
  - Filter by nonexistent agent_id
  - Combined filters (agent_id + status, agent_id + modality)
  - EventResponse includes agent_id
  - GET /events/{id} includes agent_id
  - List events includes agent_id

**Test Results**: All 11 tests passing, no regressions in existing tests (99 events tests, 514 client tests passing)

---

### Phase B: Core Infrastructure ✅ (COMPLETE)

#### B.1 AssessmentSession dataclass ✅

**File**: `agentbeats/green/session.py`

**Implementation notes:**
- Created `ActionLogEntry` Pydantic model with turn, event_id, modality, action_type, timestamp, summary, details fields
- Turn number has `ge=1` constraint (turns start at 1, not 0)
- Created `AssessmentSession` dataclass with:
  - Identity: assessment_id, scenario_id, participant_url
  - API keys: proctor_key, user_key, purple_agent_id
  - State tracking: current_turn, timing fields, action_log
  - Configuration: verbose_updates, seed, default_time_step, turn_timeout_seconds
- Helper methods: `record_action()`, `record_actions()`, `increment_turn()`, `update_turn_end_time()`
- Properties: `elapsed_wall_time`, `action_count`

#### B.2 ScenarioRegistry ✅

**File**: `agentbeats/green/scenarios.py`

**Implementation notes:**
- Created `ScenarioData` Pydantic model with scenario_id, scenario, user_prompt, characters, evaluation_criteria, metadata
- Created `ScenarioNotFoundError` custom exception
- Created `ScenarioRegistry` class with:
  - `get_scenario(scenario_id)`: Loads scenario JSON, characters, evaluation criteria
  - `_find_scenario_file()`: Searches both `examples/agents/{id}/` and `examples/scenarios/{id}.ues-scenario.json`
  - `_load_characters()`: Loads characters.json into CharacterRegistry if present
  - `_load_evaluation_criteria()`: Loads test_criteria.json if present
  - `_extract_chat_prompt()`: Extracts user prompt from chat modality in scenario
  - `_load_user_prompt()`: Loads system_prompt.txt if present
  - `extract_user_prompt()`: Convenience method for prompt extraction
  - `list_available_scenarios()`: Lists all scenario IDs found in search paths

#### B.3 ActionTracker ✅

**File**: `agentbeats/green/tracking.py`

**Implementation notes:**
- Created `ActionTracker` class that uses `AsyncUESClient` to query events by `agent_id`
- `get_actions_since(since_time, turn)`: Returns new events created after `since_time`, skips already-seen events
- `get_all_actions(turn)`: Returns all events regardless of seen status
- `_event_to_action_entry()`: Converts EventResponse to ActionLogEntry
- `_determine_action_type()`: Infers action type from event data (send, draft, create, delete, etc.)
- `_generate_summary()`: Creates human-readable summaries for different modalities
- Tracks seen event IDs to avoid duplicates across queries
- `reset()`: Clears seen events for a fresh start
- `seen_count` property for monitoring

**Tests**: 18 tests in `tests/agentbeats/green/test_tracking.py` covering:
- Initialization and configuration
- Event filtering by time and seen status
- Conversion of email, SMS, calendar, chat events
- Summary generation and truncation
- Reset functionality

---

### Phase C: Assessment Lifecycle ✅ (COMPLETE)

The AssessmentRunner class (`agentbeats/green/runner.py`) orchestrates the full
assessment lifecycle. It uses the components from Phase B and integrates with
the existing Agent/Executor infrastructure.

#### C.1 Setup Phase ✅

**File**: `agentbeats/green/runner.py` - `setup_assessment()` method

**Implementation notes:**
- Generated unique assessment_id using UUID
- Reset UES via `simulation.reset()`
- Provision proctor and user API keys via KeyManager
- Load scenario via ScenarioRegistry and import into UES
- Create AssessmentSession with all configuration
- Initialize ActionTracker for event attribution

#### C.2 Send Assessment Start ✅

**File**: `agentbeats/green/runner.py` - `send_assessment_start()` method

**Implementation notes:**
- Build `InitialStateSummary` by querying each modality's state
- Get current simulator time
- Create `AssessmentStartMessage` with UES URL, API key, time, and summary
- Send to Purple agent via Messenger with `new_conversation=True`
- Update session's `last_turn_end_time` for action tracking

#### C.3 Turn Loop ✅

**File**: `agentbeats/green/runner.py` - `run_turn_loop()` method

**Implementation notes:**
- Loop until max_turns or termination condition
- Increment turn counter via `session.increment_turn()`
- Wait for Purple's response with configurable timeout
- Track Purple's actions via ActionTracker using `get_actions_since()`
- Advance simulation time via `time.advance()`
- Update `last_turn_end_time` after each advance
- Send `TurnStartMessage` to Purple for next turn
- Returns `AssessmentCompleteReason` (SCENARIO_COMPLETE, EARLY_COMPLETION, TIMEOUT)

**Note**: The `_wait_for_purple_response()` is a placeholder - proper A2A
bidirectional messaging will be implemented in Phase E.

#### C.4 Cleanup ✅

**File**: `agentbeats/green/runner.py` - `cleanup_assessment()` method

**Implementation notes:**
- Invalidate API keys via KeyManager
- Reset Messenger state
- Clear internal references

**Convenience method**: `run_assessment()` combines setup, start, loop, and cleanup
with automatic cleanup in `finally` block.

**Tests**: 13 tests in `tests/agentbeats/green/test_runner.py` covering:
- UES reset, key provisioning, scenario loading
- Assessment start message with correct fields
- Initial state summary building with modality error handling
- Cleanup and resource management
- Full lifecycle with mocked dependencies

---

### Phase D: Evaluation

#### D.1 Evaluator class ✅

**File**: `agentbeats/green/evaluation.py`

**Implemented**:
- `CriterionDefinition`: Pydantic model for parsing criteria from `test_criteria.json`
- `EvaluationContext`: Context object passed to evaluator functions with:
  - UES client access for querying state
  - Action log filtering methods (`get_actions_by_modality`, `get_actions_by_type`, `get_actions_in_turn`)
  - Automatic state caching to minimize API calls
- `Evaluator`: Main orchestration class that runs criteria and produces `CriterionResult` objects
- Support for custom evaluator modules via `custom_module` parameter
- `parse_criteria_from_json()`: Convenience function for loading criteria

#### D.2 Built-in criterion evaluators ✅

**Implemented evaluators** (registered in `BUILTIN_EVALUATORS`):

| Evaluator | Description | Required Params |
|-----------|-------------|-----------------|
| `check_email_sent` | Verify email sent to recipient | `to`, optionally `subject_contains`, `body_contains` |
| `check_sms_sent` | Verify SMS sent to recipient | `to`, optionally `body_contains` |
| `check_calendar_event_created` | Verify calendar event exists | optionally `title_contains`, `date`, `hour` |
| `check_action_count` | Verify action count in bounds | `min`, `max` (either or both), `modality` |
| `check_no_actions` | Verify no actions taken | optionally `modality` |
| `check_state_contains` | Check modality state values | `modality`, `path`, `expected` or `exists` |

**Tests**: 45 tests in `tests/agentbeats/green/test_evaluation.py` covering:
- CriterionDefinition parsing
- EvaluationContext action filtering and state caching
- All built-in evaluators with various parameter combinations
- Evaluator class orchestration
- Custom evaluator loading
- Full evaluation flow integration

**Creating Custom Evaluators**: See module docstring in `evaluation.py` for:
- Function signature requirements
- Example custom evaluator code
- How to specify custom module path

---

### Phase E: A2A Integration ✅ (COMPLETE)

**File**: `agentbeats/green/a2a_integration.py`

#### E.1 Message serialization ✅

**Implemented**:
- `serialize_message(message: BaseModel) -> str`: Serialize any Pydantic message for A2A transmission
- `parse_purple_response(response: str) -> TurnCompleteMessage | EarlyCompletionMessage`: Parse Purple's response, determining type by field presence
- `MessageParseError`: Custom exception for parse failures with helpful diagnostics
- `parse_time_step(time_step) -> timedelta | None`: Parse ISO 8601 duration strings (e.g., "PT1H30M")

**Key design**:
- Response type detection: If `reason` present without `actions_taken`, it's `EarlyCompletionMessage`
- Supports ISO 8601 duration format for `time_step` field
- Clear error messages for debugging

#### E.2 Task updates integration ✅

**Implemented**:
- `AssessmentUpdateEmitter`: High-level wrapper around `TaskUpdateEmitter` for assessment lifecycle events
  - `emit_assessment_started(assessment_id, scenario_id)`
  - `emit_scenario_loaded(scenario_id)`
  - `emit_turn_started(turn_number, current_time)`
  - `emit_turn_completed(turn_number, actions_taken, notes)`
  - `emit_simulation_advanced(new_time, events_processed)`
  - `emit_assessment_complete(reason, result)`
  - `get_a2a_event()`: Retrieve queued update events

**Integration with runner.py**:
- Updated `_wait_for_purple_response()` to return `TurnResult` instead of raw dict
- Added `parse_a2a_response()` method using `TurnResult.from_response()`
- Added `produce_result()` method as convenience wrapper

#### E.3 Result artifact production ✅

**Implemented**:
- `TurnResult`: Unified class for handling Purple responses
  - `from_message(message)`: Create from parsed message
  - `from_response(response)`: Parse string and create result
  - `to_dict()`: Convert to dictionary for logging
  - Properties: `is_early_completion`, `actions_taken`, `notes`, `time_step`, `early_completion_reason`
- `produce_result_artifact(session, reason, criteria_results) -> AssessmentResult`: Build final assessment result
  - Computes scores from criteria results
  - Converts completion reason to status
  - Includes action log and timing information
- `reason_to_status(reason) -> AssessmentStatus`: Maps `AssessmentCompleteReason` to `AssessmentStatus`

**Tests**: 45 tests in `tests/agentbeats/green/test_a2a_integration.py` covering:
- Message serialization (3 tests)
- Response parsing (8 tests)
- Time step parsing (8 tests)
- TurnResult creation and conversion (5 tests)
- Reason to status mapping (4 tests)
- Result artifact production (6 tests)
- AssessmentUpdateEmitter (8 tests)
- Integration tests (3 tests)

---

## Testing Strategy

### Unit Tests

| Test File | Coverage |
|-----------|----------|
| `test_event_attribution.py` | agent_id injection, filtering |
| `test_session.py` | AssessmentSession lifecycle |
| `test_scenarios.py` | ScenarioRegistry loading |
| `test_tracking.py` | ActionTracker queries (18 tests) |
| `test_evaluation.py` | Evaluator, scoring (45 tests) |
| `test_a2a_integration.py` | A2A message serialization, parsing, result artifacts (45 tests) |
| `test_runner.py` | AssessmentRunner lifecycle (13 tests) |

### Integration Tests

| Test File | Coverage |
|-----------|----------|
| `test_turn_loop.py` | Full turn cycle with mocked Purple |
| `test_assessment_e2e.py` | End-to-end with mock Purple agent |

### Test Fixtures

```python
@pytest.fixture
def mock_ues_client():
    """Mock AsyncUESClient with all sub-clients."""
    client = AsyncMock(spec=AsyncUESClient)
    client.simulation.clear = AsyncMock(return_value=ClearResponse(...))
    client.simulation.reset = AsyncMock(return_value=ResetResponse(...))
    client.time.get_state = AsyncMock(return_value=TimeStateResponse(...))
    client.time.advance = AsyncMock(return_value=AdvanceTimeResponse(...))
    client.events.list_events = AsyncMock(return_value=EventListResponse(...))
    client.scenario.import_scenario = AsyncMock(return_value=LoadScenarioResponse(...))
    return client

@pytest.fixture
def mock_messenger():
    """Mock A2A Messenger."""
    messenger = AsyncMock(spec=Messenger)
    messenger.talk_to_agent = AsyncMock(return_value='{"actions_taken": 2}')
    return messenger
```

---

## Implementation Order

| Step | Task | Status |
|------|------|--------|
| 1 | A.1: Inject agent_id from AccessContext | ✅ |
| 2 | A.2: Add agent_id filter to list_events | ✅ |
| 3 | A.3: Update EventResponse to include agent_id | ✅ |
| 4 | A.4: Update client library | ✅ |
| 5 | A.5: Tests for event attribution | ✅ |
| 6 | B.1: AssessmentSession | ✅ |
| 7 | B.2: ScenarioRegistry | ✅ |
| 8 | B.3: ActionTracker | ✅ |
| 9 | C.1: Setup phase | ✅ |
| 10 | C.2: Send assessment start | ✅ |
| 11 | C.3: Turn loop | ✅ |
| 12 | C.4: Cleanup | ✅ |
| 13 | D.1: Evaluator class | ✅ |
| 14 | D.2: Built-in evaluators | ✅ |
| 15 | E.1: Message serialization | ✅ |
| 16 | E.2: Task updates integration | ✅ |
| 17 | E.3: Result artifact production | ✅ |
| 18 | Documentation updates | ✅ |

**All phases complete!** Total: 121 tests for agentbeats/green

---

## Open Questions

1. **Default time step**: When Purple doesn't specify `time_step`, should default be 1 hour?
   - **Tentative**: Yes, 1 hour default

2. **Turn timeout**: Default timeout for waiting for `turn_complete`?
   - **Tentative**: 300 seconds (5 minutes), matching messenger default

3. **Evaluation timing**: Run incrementally or at end?
   - **Tentative**: At end only (matches `post_scenario` in test_criteria.json)

4. **LLM for evaluation**: Use LLMs or rule-based?
   - **Tentative**: Rule-based for determinism; LLM optional for complex criteria

---

## Notes

### Access Control Compatibility

Access control is opt-in via `UES_ACCESS_CONTROL=true`. The implementation must:
- Work when access control is disabled (agent_id from request only)
- Work when access control is enabled (agent_id from access context)
- Never fail if access context is None

### Backward Compatibility

- `agent_id` field is optional throughout
- Existing scenarios without agent_id continue to work
- Event responses include agent_id only if set

---

## References

- [AGENTBEATS_A2A_FLOW.md](AGENTBEATS_A2A_FLOW.md) — Full A2A protocol design
- [AGENTBEATS_SUBMISSION.md](AGENTBEATS_SUBMISSION.md) — Submission checklist
- [agentbeats/green/README.md](../agentbeats/green/README.md) — Green agent documentation
- [client/CLIENT_QUICK_REFERENCE.md](../client/CLIENT_QUICK_REFERENCE.md) — Client library reference
