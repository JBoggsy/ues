# AgentBeats Competition Submission Plan

**Target**: AgentX-AgentBeats Competition - Phase 1 (Green Agent)  
**Track**: Other Agent (Personal Assistant Agent Benchmark)  
**Deadline**: January 31, 2026

---

## 1. Design Decisions

### High Priority (Research & Architecture)

- [x] **A2A SDK Selection**: Research and select which A2A SDK to use
  - **Decision**: Use Official A2A SDK (`pip install a2a-sdk`)
  - **Rationale**: Aligns with AgentBeats tutorial/templates, lightweight, model-agnostic, clean separation from UES architecture

- [x] **Green Agent ↔ Purple Agent Interaction Flow**: Design the communication pattern
  - **Decision**: Traced Environment pattern with turn-based A2A coordination
  - Purple Agent interacts directly with UES REST API (user-level API key)
  - Green Agent observes via event history, controls time advancement
  - See [AGENTBEATS_A2A_FLOW.md](AGENTBEATS_A2A_FLOW.md) for full design

- [x] **Assessment Request Handling**: Define the `assessment_request` message format
  - **Decision**: See Section 2 of A2A Flow doc
  - Config params: `scenario_id` (required), `verbose_updates`, `seed`

- [x] **Task Update / Streaming Design**: How does Green Agent report progress?
  - **Decision**: See Section 5 of A2A Flow doc
  - Update types: `assessment_started`, `scenario_loaded`, `turn_started`, `turn_completed`, `simulation_advanced`, `assessment_complete`

- [x] **UES Capability Exposure**: What UES features does Purple Agent have access to?
  - **Decision**: See Section 3 of A2A Flow doc
  - User-side modality actions only (send, reply, create, etc.)
  - Full state/query access, read-only time access
  - No simulator-side actions, time control, or admin endpoints

- [x] **API Access Enforcement**: How to enforce endpoint restrictions?
  - **Decision**: API key-based access control with `proctor` and `user` levels
  - Green Agent gets proctor key, Purple Agent gets user key in `assessment_start`
  - Middleware enforces access, attributes requests for tracing

- [x] **Response Generator Sub-agents**: How does Green Agent simulate character responses?
  - **Decision**: LLM-powered sub-agents generate in-character responses
  - Character profiles defined per-scenario (personality, timing, behavior)
  - Green detects Purple's outgoing messages and schedules character replies
  - Uses proctor-level API to inject responses via simulator-side endpoints
  - See [AGENTBEATS_A2A_FLOW.md](AGENTBEATS_A2A_FLOW.md) Section 4.1 for full design

### Medium Priority (Benchmark Design)

- [ ] **Scenario Catalog Design**: Define the set of evaluation scenarios
  - Difficulty progression (easy → medium → hard)
  - Modality coverage (single-modal vs multi-modal)
  - Task types (reactive, proactive, multi-step planning)
  - Suggested: 3 easy, 3 medium, 2 hard scenarios
  - **Each scenario must include a user prompt via chat modality** that contains the assessment instructions (goals, constraints, context)

- [ ] **Evaluation Criteria Design**: Define scoring dimensions
  - Leverage existing `agent_testing/` criteria system
  - Ensure multi-dimensional scoring (accuracy, efficiency, completeness, safety)
  - Design criteria that avoid trivial pass/fail

- [x] **Reproducibility Guarantees**: Ensure clean state between assessments
  - UES `/reset` and `/clear` fully reset all state ✅
  - API keys scoped per-assessment (auto-invalidated)
  - Deterministic scenario loading via `seed` parameter

### Lower Priority (Implementation Details)

- [x] **Baseline Purple Agent Design**: Design a simple reference agent ✅
  - A2A-compatible via PurpleExecutor infrastructure
  - SimpleEmailAgent (rule-based) + LLMAgent (LLM-based) examples
  - Full infrastructure: schemas, context, executor, server, tracked client

- [ ] **Docker Architecture**: Single container vs multi-container
  - Green Agent + UES in one container, or separate?
  - How to handle Purple Agent in local development vs production?

- [ ] **Agent Card Design**: Define green agent capabilities metadata
  - Skills, supported assessment types, resource requirements

---

## 2. Implementation Plan / TODO

### Phase 1: A2A Integration Foundation

- [x] Add `a2a-sdk` to `pyproject.toml` dependencies
- [x] Study the [AgentBeats green-agent-template](https://github.com/RDI-Foundation/green-agent-template) structure
- [x] Design our `AgentCard` (skills, capabilities, version)
- [x] Design our `AgentExecutor` that wraps UES simulation + evaluation

### Phase 2: Green Agent Implementation

#### 2.1 API Key Access Control ✅

Implemented opt-in API key-based access control via middleware. Enabled with `UES_ACCESS_CONTROL=true`.

**Files created:**
- `api/access_control.py` — `AccessLevel` enum, `AccessContext` model, `KeyRegistry` class, endpoint permission mappings
- `api/access_dependencies.py` — FastAPI dependencies (`get_api_key`, `require_proctor`, etc.)
- `api/routes/admin.py` — Key management endpoints (`POST/GET/DELETE /admin/keys`)
- `agentbeats/green/key_manager.py` — `KeyManager` class for Green Agent key provisioning

**Tests:** 75 tests passing (`test_access_control.py`, `test_access_middleware.py`, `test_admin_routes.py`, `test_key_manager.py`)

**Documentation:** See `docs/REST_API.md` (Access Control section)

#### 2.2 A2A Message Schemas (Pydantic Models) ✅

Implemented in `agentbeats/green/schemas.py`.

- [x] `ModalityCounts`:
  - `total: int`
  - `unread: int | None` (for email, sms, chat)
  - `events_today: int | None` (for calendar)
- [x] `InitialStateSummary`:
  - `email: ModalityCounts | None`
  - `calendar: ModalityCounts | None`
  - `sms: ModalityCounts | None`
  - `chat: ModalityCounts | None`
- [x] `AssessmentStartMessage`:
  - `ues_url: str`
  - `api_key: str`
  - `assessment_instructions: str` (fixed string directing agent to check chat for user instructions)
  - `current_time: datetime`
  - `initial_state_summary: InitialStateSummary`
- [x] `DEFAULT_ASSESSMENT_INSTRUCTIONS`: Constant string telling agent to query `/chat/state` for user instructions
- [x] `TurnStartMessage`:
  - `current_time: datetime`
  - `events_processed: int` (number of events fired during time advance)
- [x] `TurnCompleteMessage`:
  - `actions_taken: int`
  - `notes: str | None` (reasoning/comments for logging and potential scoring)
  - `time_step: timedelta | None` (how much to advance simulator time; optional)
- [x] `AssessmentCompleteMessage`:
  - `reason: Literal["scenario_complete", "early_completion", "timeout", "error"]`
- [x] `EarlyCompletionMessage`:
  - `reason: str | None`

#### 2.3 Task Update Streaming ✅
- [x] Define `TaskUpdate` model (type, timestamp, message, details)
- [x] Define update types enum: `log_assessment_started`, `log_scenario_loaded`, `log_turn_started`, `log_turn_completed`, `log_simulation_advanced`, `log_assessment_complete`
- [x] Implement `TaskUpdateEmitter` that streams updates via A2A
- [x] `log_assessment_started` includes `user_prompt` field with initial chat message from user

**Files created:**
- `agentbeats/green/schemas.py` — `TaskUpdateType` enum, `TaskUpdate` model
- `agentbeats/green/updates.py` — `TaskUpdateEmitter` class, helper functions, A2A conversion

**Tests:** 34 tests passing (`test_schemas.py` TaskUpdate tests, `test_updates.py`)

#### 2.4 Results Artifact ✅

**Scoring Architecture**: Pyramid structure where criteria → dimensions → overall score.
- **Criteria**: Specific rubric items per scenario, each belonging to one dimension
- **Dimensions**: Fixed categories across all assessments (accuracy, instruction_following, efficiency, safety, politeness)
- **Overall**: Sum of all criteria scores

See [AGENTBEATS_A2A_FLOW.md](AGENTBEATS_A2A_FLOW.md) Section 6 for full schema.

Implemented in `agentbeats/green/schemas.py`.

- [x] `EvaluationDimension` enum: `accuracy`, `instruction_following`, `efficiency`, `safety`, `politeness`
- [x] `ScoreSummary` model:
  - `score: int` (points earned)
  - `max_score: int` (points possible)
  - `percentage: float` (computed property)
- [x] `Scores` model:
  - `overall: ScoreSummary`
  - `dimensions: dict[EvaluationDimension, ScoreSummary]`
  - `from_criteria()` class method for computing scores from criteria list
- [x] `CriterionResult` model:
  - `id: str` (unique identifier from rubric)
  - `name: str` (human-readable name)
  - `dimension: EvaluationDimension`
  - `score: int` (points earned, 0 to max_score)
  - `max_score: int` (points possible)
  - `explanation: str` (justification for score)
- [x] `ActionLogEntry` model:
  - `turn: int`
  - `timestamp: datetime`
  - `action: str` (e.g., "email.query", "chat.send")
  - `parameters: dict`
  - `success: bool`
- [x] `AssessmentStatus` enum: `completed`, `timeout`, `error`
- [x] `AssessmentResult` model:
  - `assessment_id: str`
  - `scenario_id: str`
  - `participant: str`
  - `status: AssessmentStatus`
  - `duration_seconds: float`
  - `turns_taken: int`
  - `actions_taken: int`
  - `scores: Scores`
  - `criteria_results: list[CriterionResult]`
  - `action_log: list[ActionLogEntry]`

**Tests:** 77 tests passing (`test_schemas.py`)

#### 2.5 Response Generator Sub-agents ✅
- [x] Implement `ResponseAgentManager` class:
  - [x] `__init__(ues_client, characters, llm_provider, seed, user_email, user_phone)`
  - [x] `process_turn() -> list[ScheduledResponse]`
  - [x] `reset_state()` — clear tracking for new assessment
  - [x] `get_scheduled_responses()` — retrieve all scheduled responses
- [x] Implement character profile loading:
  - [x] `CharacterProfile` model with personality, communication_style, response_timing
  - [x] `ResponseTiming` model with base_delay, variance, work_hours config
  - [x] `CharacterRegistry` for lookup by email/phone
  - [x] Support legacy party_planner format conversion
- [x] Implement response necessity check:
  - [x] `ResponseNecessityChecker` class with LLM-based analysis
  - [x] `ResponseDecision` dataclass (needs_response, reason)
  - [x] System prompt for detecting questions vs acknowledgments
  - [x] Prevent infinite reply chains
- [x] Implement response generation:
  - [x] `_detect_outgoing_messages()` — scan email/SMS sent folders
  - [x] `_build_email_thread_context()` / `_build_sms_thread_context()`
  - [x] `_generate_response()` — LLM call with character system prompt
  - [x] `_calculate_delay()` — deterministic delay from seed + message_id
- [x] Implement response injection:
  - [x] `_schedule_email_response()` — create email.receive event
  - [x] `_schedule_sms_response()` — create sms.receive event
  - [ ] Calendar RSVP updates (future enhancement)
- [x] Implement determinism:
  - [x] `LLMConfig.get_temperature()` — seed-based temperature calculation
  - [x] Hash-based delay variance for reproducibility
- [x] Implement LLM abstraction:
  - [x] `LLMProvider` ABC with `generate(prompt, system_prompt)` method
  - [x] `OllamaProvider` for local Ollama inference
  - [x] `MockLLMProvider` for deterministic testing

**Files created:**
- `agentbeats/green/characters.py` — `CharacterProfile`, `ResponseTiming`, `RSVPBehavior`, `ContactType`, `CharacterRegistry`
- `agentbeats/green/llm.py` — `LLMConfig`, `LLMProvider`, `OllamaProvider`, `MockLLMProvider`, `ResponseNecessityChecker`, `ResponseDecision`
- `agentbeats/green/response_agents.py` — `ResponseAgentManager`, `ScheduledResponse`, `OutgoingMessage`, `create_response_agent_manager()`

**Tests:** 114 tests passing (`test_characters.py` 57 tests, `test_response_agents.py` 26 tests, `test_llm.py` 31 tests)

**Dependencies added:** `email-validator` for Pydantic `EmailStr` support

#### 2.6 AgentExecutor Implementation

> **Detailed implementation plan:** See [AGENT_EXECUTOR_IMPLEMENTATION.md](AGENT_EXECUTOR_IMPLEMENTATION.md)

##### 2.6.0 Event Attribution Infrastructure ✅

The AgentExecutor tracks which events were created by the Purple agent vs. scenario/Green events via `agent_id` injection and filtering.

**Files modified:**
- `api/access_dependencies.py` — Added `get_optional_access_context()`, `OptionalAccessContextDep`
- `api/routes/events.py` — Added `resolve_agent_id()` helper, agent_id injection, filter support
- `client/_events.py` — Added `agent_id` to `EventResponse` and `list_events()` methods

**Files created:**
- `tests/api/events/test_event_attribution.py` — 11 tests for attribution

**Tests:** All 11 attribution tests passing, 99 events API tests passing

##### 2.6.1 Core Infrastructure ✅

**Files created:**
- `agentbeats/green/session.py` — `AssessmentSession` dataclass, `ActionLogEntry` model
- `agentbeats/green/scenarios.py` — `ScenarioRegistry`, `ScenarioData`, `ScenarioNotFoundError`
- `agentbeats/green/tracking.py` — `ActionTracker` for Purple action tracking via agent_id filter

**Tests:** 18 tests in `tests/agentbeats/green/test_tracking.py`

##### 2.6.2 Assessment Lifecycle ✅

**Files created:**
- `agentbeats/green/runner.py` — `AssessmentRunner` class with full lifecycle

**Implemented:**
- Setup phase: reset UES, load scenario, provision keys via `setup_assessment()`
- Send `assessment_start` to Purple Agent via A2A via `send_assessment_start()`
- Turn loop with timeout handling via `run_turn_loop()`
- Cleanup: invalidate API keys via `cleanup_assessment()`
- Convenience method `run_assessment()` for full lifecycle

**Tests:** 13 tests in `tests/agentbeats/green/test_runner.py`

##### 2.6.3 Turn Processing ✅

Implemented in `AssessmentRunner.run_turn_loop()`:
- Wait for `turn_complete` from Purple Agent (placeholder, full A2A integration pending)
- Track Purple's actions via `ActionTracker.get_actions_since()`
- Advance simulation time via `time.advance()`
- Check termination conditions via `_should_terminate()`
- Send `turn_start` with event counts via `_send_turn_start()`

**Note:** Response generator sub-agent integration is separate from runner.

##### 2.6.4 Evaluation ✅

Implemented in `agentbeats/green/evaluation.py`:
- `CriterionDefinition` model for parsing criteria from scenario JSON
- `EvaluationContext` context object with state caching and action filtering
- `Evaluator` class for running criteria against session
- Built-in evaluators in `BUILTIN_EVALUATORS` registry:
  - `check_email_sent`, `check_sms_sent`, `check_calendar_event_created`
  - `check_action_count`, `check_no_actions`, `check_state_contains`
- Custom evaluator module loading support
- Score computation via `Scores.from_criteria()`

**Tests:** 45 tests in `tests/agentbeats/green/test_evaluation.py`

##### 2.6.5 A2A Integration ✅

**Files created:**
- `agentbeats/green/a2a_integration.py` — A2A message serialization, parsing, and result artifact production

**Implemented:**
- `serialize_message(message)` — Pydantic model to JSON for A2A transmission
- `parse_purple_response(response)` — Parse Purple's response into `TurnCompleteMessage` or `EarlyCompletionMessage`
- `MessageParseError` — Custom exception for parse failures
- `parse_time_step(time_step)` — ISO 8601 duration parsing (e.g., "PT1H30M")
- `TurnResult` — Unified class for handling Purple responses with `from_message()`, `from_response()`, `to_dict()` methods
- `produce_result_artifact(session, reason, criteria_results)` — Build final `AssessmentResult`
- `reason_to_status(reason)` — Map `AssessmentCompleteReason` to `AssessmentStatus`
- `AssessmentUpdateEmitter` — High-level wrapper for streaming lifecycle events:
  - `emit_assessment_started()`, `emit_scenario_loaded()`, `emit_turn_started()`
  - `emit_turn_completed()`, `emit_simulation_advanced()`, `emit_assessment_complete()`

**Files modified:**
- `agentbeats/green/runner.py` — Updated to use A2A integration module:
  - `_wait_for_purple_response()` now returns `TurnResult`
  - Added `parse_a2a_response()` and `produce_result()` convenience methods

**Tests:** 45 tests in `tests/agentbeats/green/test_a2a_integration.py`

**Total agentbeats/green tests:** 121 passing

### Phase 3: Baseline Purple Agent ✅

- [x] Create simple A2A-compatible Purple Agent infrastructure
- [x] Implement assessment_start handler (connect to UES)
- [x] Implement turn loop:
  - [x] Query UES state
  - [x] Make simple decisions (rule-based or LLM-based)
  - [x] Execute actions via UES REST API
  - [x] Send turn_complete
- [x] Handle assessment_complete message
- [x] Document agent behavior and limitations

**Files created in `agentbeats/purple/`:**
- `schemas.py` — Re-exports green schemas + purple-specific models
- `context.py` — AssessmentContext for state tracking
- `base_agent.py` — BaseAgent ABC + SimpleAgent reference
- `executor.py` — PurpleExecutor (A2A lifecycle management)
- `server.py` — Server setup utilities (create_agent_card, run_purple_agent)
- `ues_client.py` — TrackedAsyncUESClient with automatic action tracking
- `examples/simple_agent.py` — Minimal working example
- `examples/llm_agent.py` — LLM-powered reference agent

**Tests:** 211 tests in `tests/agentbeats/purple/`

### Phase 4: Docker & Deployment

- [ ] Create `Dockerfile` for Green Agent + UES
  - [ ] Accept `--host`, `--port`, `--card-url` arguments
  - [ ] Build for `linux/amd64`
- [ ] Create `docker-compose.yml` for local development (Green + Purple)
- [ ] Test end-to-end in containerized environment
- [ ] Publish to GitHub Container Registry (ghcr.io)
- [ ] Verify headless operation (no manual intervention)

---

## 3. Documentation & Submission TODO

### Required Submission Materials

- [ ] **Abstract** (1-2 paragraphs)
  - Brief description of what UES evaluates
  - Target agent type (personal assistant)
  - Key differentiators (multi-modal, reproducible, rich evaluation)

- [ ] **Public GitHub Repository**
  - [ ] Create `agentbeats` branch (or decide on repo strategy)
  - [ ] Complete source code with A2A integration
  - [ ] README with:
    - [ ] Overview of the benchmark
    - [ ] Setup instructions (prerequisites, installation)
    - [ ] Usage instructions (how to run assessments)
    - [ ] Architecture diagram
    - [ ] Scenario descriptions
    - [ ] Scoring methodology

- [x] **Baseline Purple Agent(s)** ✅
  - [x] Source code in `agentbeats/purple/`
  - [x] A2A-compatible implementation via PurpleExecutor
  - [x] Documentation in `agentbeats/purple/README.md`

- [ ] **Docker Image**
  - [ ] Dockerfile for Green Agent (must accept `--host`, `--port`, `--card-url`)
  - [ ] Build for `linux/amd64` architecture
  - [ ] Publish to GitHub Container Registry (ghcr.io)
  - [ ] Verify runs end-to-end without manual intervention

- [ ] **AgentBeats Platform Registration**
  - [ ] Register green agent on [agentbeats.dev](https://agentbeats.dev/)
  - [ ] Register baseline purple agent(s)

- [ ] **Demo Video** (up to 3 minutes)
  - [ ] Script the demo flow
  - [ ] Show: scenario load → agent interaction → real-time evaluation → final report
  - [ ] Record and edit

### Submission Actions

- [ ] Complete [Individual Sign Up](https://forms.gle/NHE8wYVgS6iJLwRj8) (if not done)
- [ ] Complete [Team Sign Up](https://forms.gle/bThAdujamMju6JTg8) (if applicable)
- [ ] Submit via [Phase 1 Submission Form](https://forms.gle/1C5d8KXny2JBpZhz7) by Jan 31, 2026

### Optional / Nice-to-Have

- [ ] GitHub Actions workflow for automated Docker image publishing
- [ ] Detailed scenario documentation with expected behaviors
- [ ] Contribution to AgentBeats tutorial/examples

---

## References

- [AgentX-AgentBeats Competition Page](https://rdi.berkeley.edu/agentx-agentbeats)
- [AgentBeats Tutorial Repository](https://github.com/RDI-Foundation/agentbeats-tutorial)
- [A2A Protocol Documentation](https://a2a-protocol.org/latest/)
- [Green Agent Template](https://github.com/RDI-Foundation/green-agent-template)
- [Purple Agent Template](https://github.com/RDI-Foundation/agent-template)
- [Competition Info Session Video](https://www.youtube.com/watch?v=EGBuCfVsokE)
- [Competition Slides](https://rdi.berkeley.edu/assets/agentbeats-competition-info-session-deck.pdf)
