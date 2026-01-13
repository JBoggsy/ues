# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Project organization for public GitHub release
- CLI entry point (`ues server`) for easy server startup
- MIT License
- Contributing guidelines (CONTRIBUTING.md)
- Issue and PR templates
- Startup scripts in `scripts/` directory

### Changed
- Updated README with installation instructions and quickstart guide
- Enhanced pyproject.toml with full project metadata and entry points

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
