# UES Development TODO

## Test Suite Summary

**Total Tests: 3,560 passing** | Run: `uv run pytest`

| Category | Tests | Location |
|----------|-------|----------|
| Model Tests | 1,502 | `tests/models/` |
| API Tests | 1,408 | `tests/api/` |
| Client Tests | 542 | `tests/client/` |
| Agent Testing | 108 | `tests/agent_testing/` |

Note: 3 websocket concurrency tests have known flakiness issues with httpx-ws/anyio library.

---

## 🚧 TODO: Core Simulator

### Priority 3 Modalities (Future)
Stub models exist but are not implemented (no `apply_input()`, API routes, etc.):
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
- [ ] Update `examples/agents/simple_email_summary/agent.py` to use `client.scenario` instead of direct HTTP calls

### Documentation
- [ ] Tutorial: Building an agent response loop
- [ ] Examples collection (copy-paste snippets)

---

## 🚧 TODO: Web UI

### Features
- [ ] "New Scenario" menu option (clears everything)
- [ ] "Receive Email" button in Email viewer (quick action, not via event form)
- [ ] "Receive Text" button in SMS viewer (quick action, not via event form)
- [ ] Calendar event invites (accept/decline actions)
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

**Current Documentation**: `docs/integration/AGENT_INTEGRATION.md`

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
