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
  - Config params: `scenario_id` (required), `time_limit_seconds`, `max_turns`, `verbose_updates`, `seed`

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

### Medium Priority (Benchmark Design)

- [ ] **Scenario Catalog Design**: Define the set of evaluation scenarios
  - Difficulty progression (easy → medium → hard)
  - Modality coverage (single-modal vs multi-modal)
  - Task types (reactive, proactive, multi-step planning)
  - Suggested: 3 easy, 3 medium, 2 hard scenarios

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

#### 2.1 API Key Access Control
- [ ] Define `AccessLevel` enum (`proctor`, `user`)
- [ ] Define `AccessContext` model (key, level, agent_id, assessment_id, created_at)
- [ ] Implement `KeyRegistry` class:
  - [ ] `generate_key(level, agent_id, assessment_id) -> str`
  - [ ] `validate_key(key) -> AccessContext | None`
  - [ ] `invalidate_keys(assessment_id)` — cleanup on assessment end
- [ ] Implement FastAPI dependency `get_access_context(x_api_key: Header)`
- [ ] Implement route-level enforcement:
  - [ ] `require_proctor` dependency
  - [ ] `require_user_or_proctor` dependency
- [ ] Add `X-API-Key` header requirement to all routes
- [ ] Add request attribution logging (agent_id on each request)

#### 2.2 A2A Message Schemas (Pydantic Models)
- [ ] `AssessmentStartMessage`:
  - `ues_url: str`
  - `api_key: str`
  - `scenario: ScenarioDescription` (description, goals, constraints)
  - `current_time: datetime`
  - `initial_state_summary: dict`
- [ ] `TurnStartMessage`:
  - `turn_number: int`
  - `current_time: datetime`
  - `events: list[EventSummary]` (type, summary)
- [ ] `TurnCompleteMessage`:
  - `actions_taken: int`
  - `notes: str | None`
- [ ] `AssessmentCompleteMessage`:
  - `reason: Literal["time_limit", "max_turns", "scenario_complete", "early_completion", "timeout", "error"]`
- [ ] `EarlyCompletionMessage`:
  - `reason: str | None`

#### 2.3 Task Update Streaming
- [ ] Define `TaskUpdate` model (type, timestamp, message, details)
- [ ] Define update types enum: `assessment_started`, `scenario_loaded`, `turn_started`, `turn_completed`, `simulation_advanced`, `assessment_complete`
- [ ] Implement `TaskUpdateEmitter` that streams updates via A2A

#### 2.4 Results Artifact
- [ ] Define `AssessmentResult` model:
  - `assessment_id`, `scenario_id`, `participant`, `status`
  - `duration_seconds`, `turns_taken`, `actions_taken`
  - `scores: Scores` (overall, dimensions)
  - `criteria_results: list[CriterionResult]`
  - `action_log: list[ActionLogEntry]`
- [ ] Define `Scores` model (overall, dimensions dict)
- [ ] Define `DimensionScore` model (score, max, weight)
- [ ] Define `CriterionResult` model (id, name, passed, score, max_score, explanation)
- [ ] Define `ActionLogEntry` model (turn, timestamp, action, parameters, success)

#### 2.5 AgentExecutor Implementation
- [ ] Implement `AgentExecutor` class:
  - [ ] `__init__(ues_client, scenario_loader, evaluator)`
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
  - [ ] Advance simulation time
  - [ ] Process scheduled events
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
