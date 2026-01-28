# UES Development TODO

## ✅ Completed: Multi-Agent Coordination

### Simulation Hold System
The hold system enables coordination between multiple concurrent agents (e.g., user-side AI assistant + simulator-side character agents) by preventing time advancement while holds are active.

**API Endpoints**:
- `POST /simulation/hold` - Acquire a hold (returns hold_id), blocks time advancement
- `POST /simulation/release/{hold_id}` - Release a specific hold
- `GET /simulation/holds` - List all active holds

**Features**:
- Multiple holds can be active simultaneously (all must be released to allow time advancement)
- Optional timeout (default: 300s) auto-releases stale holds
- WebSocket notifications: `hold.acquired`, `hold.released`, `hold.expired`
- `HoldError` returned (409 Conflict) when time operations attempted with active holds

**Python Client**:
```python
# Acquire a hold while processing
hold = client.simulation.hold(reason="Generating LLM response", timeout_seconds=60.0)
try:
    # ... generate response and schedule events ...
    pass
finally:
    client.simulation.release(hold.hold_id)
```

**Documentation**: See `src/ues/models/hold.py` for implementation details.

---

## Test Suite Summary

**Total Tests: 3,325 passing** | Run: `uv run pytest`

| Category | Tests | Location |
|----------|-------|----------|
| Model Tests | 1,424 | `tests/models/` |
| API Tests | 1,279 | `tests/api/` |
| Client Tests | 514 | `tests/client/` |
| Agent Testing | 108 | `tests/agent_testing/` |

Note: 3 websocket concurrency tests have known flakiness issues with httpx-ws/anyio library.

---

## ✅ Completed: Core Simulator

**Data Models** - Full event-sourcing architecture with undo/redo support.

| Component | Description |
|-----------|-------------|
| `SimulatorEvent` | Scheduled actions with status tracking |
| `EventQueue` | Ordered event management with batch operations |
| `SimulatorTime` | Virtual time with pause/resume, time scaling |
| `Environment` | State container for all modalities |
| `SimulationEngine` | Orchestrator with undo/redo stack |
| `Scenario` | Save/load serialization infrastructure |

**Priority 1 Modalities** (Simple, Foundational):
- Location, Time, Weather

**Priority 2 Modalities** (Message-Based):
- Email (19 operations), SMS (13 actions), Chat, Calendar (with recurrence)

All modalities implement: `apply_input()`, `clear()`, `create_undo_data()`, `apply_undo()`, `summary`, `get_snapshot()`

**Documentation**: `docs/SIMULATION_ENGINE.md`, `docs/ENVIRONMENT.md`, `docs/SIMULATOR_TIME.md`, `docs/MODALITY_MODELS.md`

---

## ✅ Completed: REST API

**89 endpoints** across time control, events, environment, simulation, scenarios, and modalities.

| Category | Key Endpoints |
|----------|---------------|
| Time | GET/POST `/simulator/time/*` (advance, set, skip-to-next, pause, resume, set-scale) |
| Events | `/events` (list, create, batch), `/events/immediate`, `/events/{id}` |
| Environment | `/environment/state`, `/environment/modalities` (list only) |
| Simulation | `/simulation/start,stop,status,reset,clear,undo,redo,hold,release,holds` |
| Scenarios | `/scenario/export/*`, `/scenario/import/*` |
| Modalities | `/{modality}/state`, `/{modality}/query`, action endpoints |
| Webhooks | `/webhooks` (9 endpoints for registration/management) |
| WebSocket | `/ws` for real-time notifications |

**State Retrieval Semantics**:
- `/{modality}/state` - Returns **full state** (complete data including history)
- `/environment/state` - Returns **full state** for all modalities (`model_dump()`)
- `get_snapshot()` method - **Compact view** (optimized for LLM context, no history)

**Python Client Library**: Sync + async support, all endpoints covered. See `docs/API_CLIENT.md`

**Documentation**: `docs/REST_API.md`, `docs/MODALITY_ROUTES.md`, `docs/WEBSOCKET.md`, `docs/WEBHOOKS.md`

---

## ✅ Completed: Web UI

React 18 + TypeScript + Vite + Tailwind CSS + shadcn/ui

| Feature | Components |
|---------|------------|
| Simulation Controls | TimeDisplay, TimeScaleSlider, TimeAdvanceControls, SimulationStatus |
| Event Management | EventTimeline, EventCreationDialog, modality-specific forms |
| Modality Viewers | Email, SMS, Chat, Calendar (day/week/month), Location, Weather, Time |
| Scenario Management | ExportDialog, ImportDialog, CompatibilityDialog |
| Settings | Theme toggle, API configuration |

**Build**: `cd webapp && npm run dev` (dev) or `npm run build` (prod)

---

## ✅ Completed: Agent Testing Harness

The `agent_testing` package provides infrastructure for scenario authors to evaluate AI agent performance through customizable, hook-based testing.

| Component | Description |
|-----------|-------------|
| `EvalRunner` | Orchestrates test execution lifecycle |
| `EvalContext` | Context object passed to evaluator functions |
| `EvalResult` | Result returned by evaluator functions |
| `CriterionResult` | Aggregated result for a single criterion |
| `EvalReport` | Complete test report with grades and scoring |
| `EventHookManager` | Hook registration and dispatch for on_event criteria |

**Features**:
- JSON-defined criteria referencing Python evaluator functions
- Two evaluation timings: `post_scenario` (after completion) and `on_event` (real-time)
- LLM-friendly: evaluators can use any logic (programmatic, LLM-based, hybrid)
- Terminal scoreboard display with progress bars and grades
- JSON report export for CI integration

**Example**:
```python
from agent_testing import EvalRunner

async def main():
    runner = EvalRunner(
        scenario_path="./scenario.ues-scenario.json",
        criteria_path="./test_criteria.json",
    )
    report = await runner.run()
    runner.print_report()
```

**CLI**: `uv run python -m agent_testing path/to/scenario/`

**Tests**: 108 tests in `tests/agent_testing/`

**Documentation**: `docs/AGENT_TESTING.md`

---

## 🚧 TODO: Core Simulator

### Priority 3 Modalities (Future)
- [ ] **Contacts** - Contact database for SMS/Email/Calendar integration
- [ ] **File System** - Directory tree, file operations
- [ ] **Discord/Slack** - Messaging platform simulation
- [ ] **Social Media** - Posts, feeds, interactions
- [ ] **Screen** - UI state simulation

### Improvements
- [ ] Fix real weather timestamping and sunrise/sunset times
- [ ] Consider removing real weather API from backend (let clients supply it)

---

## 🚧 TODO: REST API

### Python Client Library
- [x] ~~**Add `client.scenario` sub-client**~~ - Wraps `/scenario/import/*` and `/scenario/export/*` endpoints
  - [ ] Update `examples/agents/simple_email_summary/agent.py` to use `client.scenario` once implemented

### API Enhancements
- [x] ~~**Add `compact` query parameter to `/{modality}/state`**~~
  - `GET /{modality}/state` - Full state (default)
  - `GET /{modality}/state?compact=true` - Compact snapshot for LLM context
  - Implemented for: location, time, weather, sms, chat, calendar, email

### Documentation
- [x] ~~Update `docs/REST_API.md` - Document removed `/environment/modalities/{modality}` endpoint and `compact` param~~
- [ ] Tutorial: Building an agent response loop
- [ ] Examples collection (copy-paste snippets)

---

## 🚧 TODO: Web UI

### Features
- [ ] "New Scenario" menu option (clears everything)
- [ ] "Receive Email" button in Email viewer
- [ ] "Receive Text" button in SMS viewer
- [ ] Calendar event invites (accept/decline)
- [ ] Named locations/saved addresses management
- [ ] Mobile responsive improvements
- [ ] Accessibility audit

### Future Enhancements
- [ ] Scenario library (browse/manage multiple scenarios)
- [ ] Scenario versioning and diff
- [ ] Auto-save with recovery
- [ ] Scenario templates for common patterns

---

## 🚧 TODO: External Agent Integration

### Example Agents
- [ ] Reactive email reply agent (Python)
- [ ] LLM content generation agent
- [ ] Condition-based trigger agent

### Future: External Agent Package (Separate Repository)
- [ ] Reference implementation of simulator-side agent patterns
- [ ] Character personality system
- [ ] Trigger/condition framework
- [ ] LLM provider abstraction layer

**Current Documentation**: `docs/AGENT_INTEGRATION.md`

---

## 🔮 Future: OpenEnv Compatibility

[OpenEnv](https://github.com/meta-pytorch/OpenEnv) is Meta's framework for agentic RL training environments using Gymnasium-style APIs (`step()`, `reset()`, `state()`). Adding compatibility would enable RL training of AI assistants on simulated user environments.

### Conceptual Mapping
| OpenEnv | UES Equivalent |
|---------|----------------|
| `Environment` | Simulation Engine |
| `Action` | `ModalityInput` |
| `Observation` | `ModalityState` snapshots |
| `State` | Episode metadata (sim time, step count) |
| Episode | Scenario |

### Implementation Tasks
- [ ] Create `openenv/` adapter layer (`models.py`, `environment.py`, `client.py`)
- [ ] Define `UESAction` (modality + payload) and `UESObservation` (state snapshot)
- [ ] Implement `reset()` → simulation reset, `step()` → apply input + advance time
- [ ] Design reward signal system (task completion, scenario-defined criteria)
- [ ] Add WebSocket support (OpenEnv prefers WS over HTTP)
- [ ] Create `Dockerfile` and `openenv.yaml` for deployment
- [ ] Example: RL training script with TRL/torchforge

**Note**: OpenEnv is experimental (APIs may change). Revisit when stable.

---

## Notes

- All models use Pydantic with `ConfigDict`
- Each modality has `<modality>_input.py` and `<modality>_state.py`
- Use Google-style docstrings
- Timestamps use simulator time, not wall-clock time
- Use `uv run` for all Python commands
