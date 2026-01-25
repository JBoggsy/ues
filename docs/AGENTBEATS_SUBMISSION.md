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

- [ ] **Baseline Purple Agent Design**: Design a simple reference agent
  - Must be A2A-compatible
  - Should demonstrate benchmark capabilities without being optimal
  - Could be rule-based or simple LLM-based

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
- [ ] Implement `AgentExecutor` class:
  - [ ] `__init__(ues_client, scenario_loader, evaluator, response_manager)`
  - [ ] `run_assessment(participants, config) -> AssessmentResult`
- [ ] Implement assessment lifecycle:
  - [ ] Parse and validate `assessment_request`
  - [ ] Generate proctor API key for self
  - [ ] Generate user API key for Purple Agent
  - [ ] Reset UES to clean state
  - [ ] Load scenario from `scenario_id`
  - [ ] Send `assessment_start` to Purple Agent via A2A
- [ ] Implement turn loop:
  - [ ] Wait for `turn_complete` from Purple Agent (with timeout)
  - [ ] Run response generator sub-agents for character replies
  - [ ] Advance simulation time
  - [ ] Process scheduled events (including character responses)
  - [ ] Check termination conditions
  - [ ] Send `turn_start` with new events
- [ ] Implement termination handling:
  - [ ] Time limit exceeded
  - [ ] Max turns exceeded
  - [ ] Scenario end reached
  - [ ] Early completion from Purple
  - [ ] Timeout/crash detection
- [ ] Implement evaluation:
  - [ ] Retrieve full event trace from UES
  - [ ] Run evaluation criteria
  - [ ] Compute dimension scores
  - [ ] Generate results artifact
- [ ] Cleanup: invalidate API keys

### Phase 3: Baseline Purple Agent

- [ ] Create simple A2A-compatible Purple Agent
- [ ] Implement assessment_start handler (connect to UES)
- [ ] Implement turn loop:
  - [ ] Query UES state
  - [ ] Make simple decisions (rule-based or LLM-based)
  - [ ] Execute actions via UES REST API
  - [ ] Send turn_complete
- [ ] Handle assessment_complete message
- [ ] Document agent behavior and limitations

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

- [ ] **Baseline Purple Agent(s)**
  - [ ] Source code in repository
  - [ ] A2A-compatible implementation
  - [ ] Documentation on how it works

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
