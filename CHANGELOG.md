# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Calendar respond test** - Added `tests/api/modalities/calendar/test_calendar_respond.py` to verify `POST /calendar/respond` correctly updates attendee status in state.

### Fixed
- **EventResponse now includes agent_id field** - The `agent_id` field is now returned in API responses for event endpoints (`GET /events`, `POST /events`, `GET /events/{event_id}`, `GET /events/next`, `POST /events/immediate`). Previously, `agent_id` was accepted on event creation but not included in responses, making it impossible to filter or attribute events by agent.

## [0.2.1] - 2026-01-29

### Added
- **Calendar RSVP Support** - Respond to calendar event invitations
  - `POST /calendar/respond` endpoint for updating attendee response status
  - `respond_to_event()` method in `CalendarClient` and `AsyncCalendarClient`
  - `respond` operation in `CalendarInput` with `attendee_email`, `response`, `response_comment` fields
  - `_handle_respond()` handler in `CalendarState`
  - `calendar:respond` permission for access control
  - 5 new client tests for respond_to_event functionality

## [0.2.0] - 2026-01-28

### Added
- **API Access Control** - Complete key-based authentication and authorization system
  - `APIKey` model with fine-grained permissions and wildcard support (`*`, `email:*`)
  - `APIKeyRegistry` for in-memory key storage with admin key auto-generation at startup
  - `require_permission()` FastAPI dependency for route protection
  - `Permissions` constants class covering all 94 API endpoints
  - Key management endpoints: `POST /keys`, `GET /keys`, `GET /keys/{key_id}`, `DELETE /keys/{key_id}`
  - Access logging middleware with queryable logs (`GET /access-logs`, `GET /access-logs/stats`)
  - Event attribution: auto-sets `agent_id` and `created_by_key` on event creation
  - Python client updated with `api_key` parameter support
  - Documentation: `docs/api/AUTHENTICATION.md`, `docs/api/MIGRATION_AUTH.md`

- **Python Client `scenario` Sub-client** (`client.scenario`)
  - `export_full()` / `export_full_async()` - Export complete scenario
  - `export_environment()` / `export_environment_async()` - Export environment only
  - `export_events()` / `export_events_async()` - Export events only
  - `import_full()` / `import_full_async()` - Import complete scenario
  - `import_environment()` / `import_environment_async()` - Import environment
  - `import_events()` / `import_events_async()` - Import events
  - 695 tests for scenario client functionality

- **Agent Testing Harness** (`agent_testing` package)
  - JSON-defined test criteria referencing Python evaluator functions
  - `EvalRunner` orchestrates test execution lifecycle
  - `EvalContext` for accessing simulation state in evaluators
  - Two evaluation timings: `post_scenario` and `on_event` (real-time)
  - Terminal scoreboard display with progress bars and grades
  - JSON report export for CI integration
  - CLI: `uv run python -m agent_testing path/to/scenario/`
  - 108 tests for the harness itself

- **Simulation Hold System** for multi-agent coordination
  - `POST /simulation/hold` - Acquire a hold (returns hold_id)
  - `POST /simulation/release/{hold_id}` - Release a specific hold
  - `GET /simulation/holds` - List all active holds
  - Optional timeout (default: 300s) auto-releases stale holds
  - WebSocket notifications: `hold.acquired`, `hold.released`, `hold.expired`
  - Python client: `client.simulation.hold()` and `client.simulation.release()`

- **Example Agents** (5 complete examples in `examples/agents/`)
  - Simple email summary agent
  - Email reply generator agent
  - Calendar conflict resolver agent
  - SMS group chat simulator agent
  - Party planner multi-agent integration example

- Project organization for public GitHub release
- CLI entry point (`ues server`) for easy server startup
- MIT License
- Contributing guidelines (CONTRIBUTING.md)
- Issue and PR templates
- Startup scripts in `scripts/` directory

### Changed
- **Project structure reorganization**: Source code moved to `src/ues/` following Python packaging best practices
  - All imports updated from `models.`, `api.`, `client.` to `ues.models.`, `ues.api.`, `ues.client.`
  - Documentation reorganized into subdirectories: `docs/api/`, `docs/models/`, `docs/client/`, `docs/guides/`, `docs/integration/`
  - Agent testing moved to `src/ues/agent_testing/`
- Updated README with installation instructions and quickstart guide
- Enhanced pyproject.toml with full project metadata and entry points
- Test count increased from 1,242 to 3,560 tests
- REST API now has 94 endpoints (up from 85+)
- API tests increased to 1,408 (was 1,388)
- Client tests increased to 542 (was 514)

### Fixed
- Email threading support improvements
- Calendar state typing issues
- Email state API now returns folder/label message IDs instead of counts

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

[Unreleased]: https://github.com/JBoggsy/ues/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/JBoggsy/ues/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/JBoggsy/ues/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/JBoggsy/ues/releases/tag/v0.1.0
