# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### AgentBeats Green Agent (Assessment Orchestrator)
- **Event Attribution Infrastructure**: `agent_id` injection and filtering for tracking Purple agent actions
  - `api/access_dependencies.py`: `get_optional_access_context()`, `OptionalAccessContextDep`
  - `api/routes/events.py`: `resolve_agent_id()` helper, agent_id query parameter
  - `client/_events.py`: `agent_id` support in `EventResponse` and `list_events()`
  - 11 new tests in `tests/api/events/test_event_attribution.py`

- **Core Infrastructure** (`agentbeats/green/`)
  - `session.py`: `AssessmentSession` state container, `ActionLogEntry` model
  - `scenarios.py`: `ScenarioRegistry` for loading scenario definitions from filesystem
  - `tracking.py`: `ActionTracker` for Purple agent action attribution via event queries
  - 18 tests in `tests/agentbeats/green/test_tracking.py`

- **Assessment Lifecycle** (`agentbeats/green/runner.py`)
  - `AssessmentRunner` class orchestrating full assessment lifecycle
  - Setup phase: UES reset, scenario loading, API key provisioning
  - Turn loop with timeout handling and action tracking
  - Cleanup with API key invalidation
  - 13 tests in `tests/agentbeats/green/test_runner.py`

- **Evaluation Framework** (`agentbeats/green/evaluation.py`)
  - `CriterionDefinition` model for parsing criteria from scenario JSON
  - `EvaluationContext` with state caching and action log filtering
  - `Evaluator` class for running criteria against assessment sessions
  - Built-in evaluators: `check_email_sent`, `check_sms_sent`, `check_calendar_event_created`, `check_action_count`, `check_no_actions`, `check_state_contains`
  - Custom evaluator module loading support
  - 45 tests in `tests/agentbeats/green/test_evaluation.py`

- **A2A Integration** (`agentbeats/green/a2a_integration.py`)
  - Message serialization and parsing for Purple agent communication
  - `TurnResult` class for unified Purple response handling
  - `parse_time_step()` for ISO 8601 duration parsing (e.g., "PT1H30M")
  - `produce_result_artifact()` for building final `AssessmentResult`
  - `AssessmentUpdateEmitter` for streaming lifecycle events
  - 45 tests in `tests/agentbeats/green/test_a2a_integration.py`
  - Updated `runner.py` to use A2A integration module

### Changed
- Project organization for public GitHub release
- CLI entry point (`ues server`) for easy server startup

### Documentation
- Updated `agentbeats/green/README.md` with new modules and test information
- Updated `docs/AGENT_EXECUTOR_IMPLEMENTATION.md` with completed Phase A-E status (all phases complete)
- Updated `docs/AGENTBEATS_SUBMISSION.md` with implementation progress

## [0.1.0] - 2025-01-13

### Added
- **Core Simulation Engine**
  - Event-sourcing architecture with `SimulatorEvent`, `EventQueue`, and `Environment`
  - `SimulatorTime` with pause/resume and time scaling (1x, 10x, 100x)
  - `SimulationEngine` orchestrator with undo/redo support
  - Scenario save/load functionality for reproducible testing

- **Modalities**
  - Email (19 operations): send, receive, read, star, archive, delete, move, labels, threading
  - SMS/RCS (13 actions): send, receive, read, delete, reactions
  - Calendar: events, recurrence patterns, invitations
  - Chat: conversational interface with history
  - Location: GPS coordinates, named places
  - Weather: conditions, temperature, forecasts

- **REST API** (85+ endpoints)
  - Time control: advance, set, skip-to-next, pause, resume, set-scale
  - Event management: create, list, batch, immediate execution
  - Environment state: full snapshots, compact views
  - Simulation control: start, stop, reset, clear, undo, redo
  - Scenario export/import
  - WebSocket and Webhook support for real-time notifications

- **Python Client Library**
  - Sync and async support
  - Type-safe methods for all endpoints

- **Web UI**
  - Simulation controls (time display, scale slider, advance controls)
  - Event timeline and creation dialogs
  - Modality viewers (Email, SMS, Chat, Calendar, Location, Weather)
  - Scenario management (export/import)
  - Settings page with theme toggle

### Technical Details
- Built with FastAPI and Pydantic for type-safe API
- React 18 + TypeScript + Vite for modern web UI
- 1,242+ tests with comprehensive coverage

[Unreleased]: https://github.com/jbboggs/ues/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/jbboggs/ues/releases/tag/v0.1.0
