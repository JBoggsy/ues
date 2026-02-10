# UES Development TODO

## Test Suite Summary

**Total Tests: 3,595 passing** | Run: `uv run pytest`

| Category | Tests | Location |
|----------|-------|----------|
| Model Tests | 1,499 | `tests/models/` |
| API Tests | 1,437 | `tests/api/` |
| Client Tests | 546 | `tests/client/` |
| Agent Testing | 108 | `tests/agent_testing/` |

Note: 3 websocket concurrency tests have known flakiness issues with httpx-ws/anyio library.

---

## 🐛 Bugs

### Confirmed
- [ ] **Hardcoded `status="executed"` in all modality route handlers** — Calendar routes were fixed (commit TBD), but the same pattern exists in email (11 instances), SMS (7), chat (3), weather (1), and location (1) route files. All use `status="executed"` in `ModalityActionResponse` instead of `event.status.value`, silently swallowing execution failures. See `src/ues/api/routes/{email,sms,chat,weather,location}.py`.

### Needs Investigation
- [ ] **SMS client/server model field mismatches** — The sub-agent analysis found 9 discrepancies between `src/ues/client/_sms.py` and `src/ues/models/modalities/sms_state.py`. High-severity: `SMSMessage.received_at` (client) vs `delivered_at` (server) causes delivery timestamps to always be `None`; `SMSConversation.is_group` is a field in client but a method in server, so group conversations always appear as one-on-one. Other mismatches: `deleted_at` client-only, `edited_at` server-only, `MessageAttachment.attachment_id` missing from client, `MessageReaction.reaction_id`/`message_id` missing from client, `GroupParticipant.left_at` missing from client, `GroupParticipant.display_name` client-only, `SMSConversation.message_ids` client-only.
- [ ] **Email client `participant_addresses` type mismatch** — Server uses `set[str]`, client uses `list[str]`. Low severity (JSON arrays round-trip fine) but could cause duplicate-handling differences.
- [ ] **Audit all client models against server models** — The calendar `Attendee` and SMS model mismatches suggest a systematic pattern of client models drifting from server models. All modalities should be audited: compare field names, types, enum values, and defaults between `src/ues/client/_<modality>.py` and `src/ues/models/modalities/<modality>_state.py` / `<modality>_input.py`.

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
