# UES Documentation

Welcome to the User Environment Simulator (UES) documentation. This documentation is organized to mirror the source code structure in `src/ues/`.

## 📚 Quick Links

| I want to... | Go to... |
|--------------|----------|
| Get started quickly | [Quickstart Guide](guides/QUICKSTART.md) |
| Use the Python client | [Client Quick Reference](client/CLIENT_QUICK_REFERENCE.md) |
| Understand the REST API | [REST API Overview](api/REST_API.md) |
| Build an agent integration | [Agent Integration Guide](integration/AGENT_INTEGRATION.md) |
| Test my AI agent | [Agent Testing Harness](agent-testing/AGENT_TESTING.md) |

---

## 📁 Documentation Structure

```
docs/
├── models/              # Data models and simulation engine
├── api/                 # REST API and real-time communication
├── client/              # Python client library
├── agent-testing/       # Agent evaluation framework
├── integration/         # External agent integration patterns
├── guides/              # Tutorials and how-to guides
└── webapp/              # Web UI documentation
```

---

## 🏗️ Models (`models/`)

Core data models, simulation engine, and modality implementations.

### Core Architecture
| Document | Description |
|----------|-------------|
| [Simulation Engine](models/SIMULATION_ENGINE.md) | Main orchestrator for event-driven simulation |
| [Simulator Time](models/SIMULATOR_TIME.md) | Virtual time management and time scaling |
| [Environment](models/ENVIRONMENT.md) | State container for all modalities |
| [Simulation Event](models/SIMULATION_EVENT.md) | Event structure and lifecycle |
| [Orchestration](models/ORCHESTRATION.md) | Requirements for simulation orchestration |

### Modality System
| Document | Description |
|----------|-------------|
| [Modality Models](models/MODALITY_MODELS.md) | Architecture overview for Input/State pattern |
| [Modality Undo Notes](models/MODALITY_UNDO_NOTES.md) | Implementation guide for undo/redo support |
| [Modality Unit Tests](models/MODALITY_UNIT_TESTS.md) | Testing patterns for modalities |

### Individual Modalities (`models/modalities/`)
| Modality | Description |
|----------|-------------|
| [Email](models/modalities/EMAIL.md) | Inbox, folders, threads, labels (19 operations) |
| [SMS](models/modalities/SMS.md) | Text messaging with reactions |
| [Calendar](models/modalities/CALENDAR.md) | Events, recurrence, invitations |
| [Chat](models/modalities/CHAT.md) | Conversational interface |
| [Location](models/modalities/LOCATION.md) | GPS coordinates, named places |
| [Weather](models/modalities/WEATHER.md) | Conditions, temperature, forecasts |
| [Time](models/modalities/TIME.md) | Time-of-day awareness |

---

## 🌐 API (`api/`)

REST API endpoints, WebSocket, and webhook support.

| Document | Description |
|----------|-------------|
| [REST API Overview](api/REST_API.md) | Complete endpoint reference (89 endpoints) |
| [Authentication](api/AUTHENTICATION.md) | API key authentication and permissions |
| [Auth Migration Guide](api/MIGRATION_AUTH.md) | Migrating to authenticated API |
| [Modality Routes](api/MODALITY_ROUTES.md) | Patterns for modality-specific endpoints |
| [Error Handling](api/API_ERROR_HANDLING.md) | HTTP status codes and error responses |
| [WebSocket](api/WEBSOCKET.md) | Real-time event notifications |
| [Webhooks](api/WEBHOOKS.md) | HTTP callback notifications |

---

## 🐍 Client (`client/`)

Python client library for interacting with the UES API.

| Document | Description |
|----------|-------------|
| [API Client Guide](client/API_CLIENT.md) | Full client library documentation |
| [Quick Reference](client/CLIENT_QUICK_REFERENCE.md) | Cheat sheet for common operations |

---

## 🧪 Agent Testing (`agent-testing/`)

Framework for evaluating AI agent performance.

| Document | Description |
|----------|-------------|
| [Agent Testing Harness](agent-testing/AGENT_TESTING.md) | Complete testing framework documentation |

---

## 🔗 Integration (`integration/`)

Patterns for integrating external agents with UES.

| Document | Description |
|----------|-------------|
| [Agent Integration Guide](integration/AGENT_INTEGRATION.md) | How to connect AI agents to UES |
| [Event Generation Agent](integration/simulation_agents/EVENT_GENERATION_AGENT.md) | Example: simulator-side content agent |

---

## 📖 Guides (`guides/`)

Tutorials and how-to documentation.

| Document | Description |
|----------|-------------|
| [Quickstart](guides/QUICKSTART.md) | Get up and running in 5 minutes |
| [Manual Time Tutorial](guides/TUTORIAL_MANUAL_TIME.md) | Step-by-step time control guide |
| [Scenarios](guides/SCENARIOS.md) | Working with simulation scenarios |
| [Scenario Format](guides/SCENARIO_FORMAT.md) | JSON schema for scenario files |
| [Scenario Save/Load](guides/SCENARIO_SAVE_LOAD.md) | Persisting and restoring scenarios |

---

## 🖥️ Web UI (`webapp/`)

React-based web interface documentation.

| Document | Description |
|----------|-------------|
| [Implementation Plan](webapp/WEB_UI_IMPLEMENTATION_PLAN.md) | Architecture and component design |

---

## 🗺️ See Also

- [README.md](../README.md) - Project overview and installation
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Contribution guidelines
- [CHANGELOG.md](../CHANGELOG.md) - Version history
- [TODO.md](../TODO.md) - Development roadmap
