# User Environment Simulator (UES)

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.121+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-3720%20passing-brightgreen.svg)](#testing)

An AI-driven testing and prototyping tool for AI personal assistants. UES provides a simple web-based UI and comprehensive REST API for simulating a variety of input modalities, enabling customizable and reproducible testing of AI agent capabilities.

## ✨ Features

- **Multi-Modal Simulation**: Email, SMS, Calendar, Chat, Location, Weather, and more
- **REST API**: 95 endpoints for complete control over simulation state
- **API Access Control**: Key-based authentication with fine-grained permissions
- **Real-time Updates**: WebSocket and Webhook support for event notifications
- **Python Client Library**: Sync and async support for easy integration
- **Web UI**: Modern React-based interface for interactive scenario design
- **Scenario Management**: Save, export, and replay test scenarios
- **Time Control**: Manual, event-driven, or auto-advance simulation modes
- **Agent Testing Harness**: Evaluate AI agent performance with customizable criteria
- **Multi-Agent Coordination**: Hold system for synchronizing concurrent agents

## 🚀 Quick Start

### Installation

```bash
# Using pip
pip install ues

# Using uv (recommended)
uv add ues
```

### Start the API Server

```bash
# Using the CLI
ues server

# With auto-reload for development
ues server --reload

# Or directly with uvicorn
uvicorn main:app --reload
```

The API is now available at:
- **API Server**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Basic Usage

> **Note**: When the server starts, an admin API key is printed to the console. Save this key for authentication.

```python
from ues.client import UESClient

# Connect to the server with your API key
client = UESClient("http://localhost:8000", api_key="ues_your_key_here...")

# Get current simulation time
time_state = client.time.get_state()
print(f"Simulator time: {time_state.current_time}")

# Simulate receiving an email
client.email.receive(
    from_addr="boss@company.com",
    to_addr="user@example.com",
    subject="Meeting Tomorrow",
    body="Don't forget our 9am meeting!"
)

# Check email state
email_state = client.email.get_state()
print(f"Inbox has {len(email_state.inbox)} emails")

# Advance time by 1 hour
client.time.advance(hours=1)
```

## 📦 Development Setup

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Node.js 18+ (for Web UI)

### Clone and Install

```bash
# Clone the repository
git clone https://github.com/JBoggsy/ues.git
cd ues

# Install Python dependencies
uv sync

# Install Web UI dependencies
cd webapp && npm install
```

### Running Development Servers

```bash
# Terminal 1: Start API server with auto-reload
uv run ues server --reload

# Terminal 2: Start Web UI
cd webapp && npm run dev
```

Access:
- **API**: http://localhost:8000/docs
- **Web UI**: http://localhost:5173

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/api/modalities/test_email_routes.py -v

# Run with coverage
uv run pytest --cov=api --cov=models
```

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Documentation Index](docs/README.md) | Full documentation table of contents |
| [REST API Reference](docs/api/REST_API.md) | Complete API endpoint documentation |
| [Authentication](docs/api/AUTHENTICATION.md) | API key authentication and permissions |
| [Modality Routes](docs/api/MODALITY_ROUTES.md) | Modality-specific endpoint patterns |
| [Python Client](docs/client/API_CLIENT.md) | Client library usage guide |
| [Agent Integration](docs/integration/AGENT_INTEGRATION.md) | Integrating AI agents with UES |
| [Agent Testing](docs/agent-testing/AGENT_TESTING.md) | Testing harness for evaluating AI agents |
| [Scenarios](docs/guides/SCENARIOS.md) | Saving and loading test scenarios |
| [WebSocket](docs/api/WEBSOCKET.md) | Real-time event notifications |
| [Webhooks](docs/api/WEBHOOKS.md) | HTTP callback notifications |

## 🎯 Supported Modalities

| Modality | Status | Description |
|----------|--------|-------------|
| Email | ✅ Complete | Inbox, folders, threads, labels (19 operations) |
| SMS/RCS | ✅ Complete | Text messaging with reactions (13 actions) |
| Calendar | ✅ Complete | Events, recurrence, invitations |
| Chat | ✅ Complete | Conversational interface |
| Location | ✅ Complete | GPS coordinates, named places |
| Weather | ✅ Complete | Conditions, temperature, forecasts |
| Contacts | 📋 Planned | Contact database |
| File System | 📋 Planned | Directory tree, file operations |
| Discord/Slack | 📋 Planned | Messaging platforms |
| Social Media | 📋 Planned | Posts, feeds, interactions |

## 🏗️ Architecture

UES uses an **event-sourcing architecture** where simulation state progresses through discrete events:

```
src/ues/                           # Main Python package
    ├── models/                    # Data models (events, modalities, etc.)
    ├── api/                       # FastAPI REST endpoints
    ├── client/                    # Python client library
    └── agent_testing/             # Testing harness for AI agents
tests/                             # Pytest test suite
webapp/                            # React + TypeScript web UI
docs/                              # Documentation
examples/                          # Example agents and scenarios
```

### Core Components

```
SimulationEngine (Orchestrator)
    ├── Environment (Current state)
    │   ├── SimulatorTime (Virtual time tracking)
    │   └── ModalityStates (Email, Location, Calendar, etc.)
    ├── EventQueue (Scheduled events)
    └── SimulationLoop (Auto-advance threading)
```

### Simulation Modes

- **Manual Mode**: Time advances only via explicit API calls
- **Event-Driven Mode**: Time skips directly to next scheduled event
- **Auto-Advance Mode**: Real-time or accelerated time progression

See [docs/models/SIMULATION_ENGINE.md](docs/models/SIMULATION_ENGINE.md) for detailed architecture documentation.

## 🌐 REST API Overview

### Authentication

All API endpoints require an API key via the `X-API-Key` header:

```bash
curl -H "X-API-Key: ues_your_key_here..." http://localhost:8000/simulation/status
```

An admin key with full permissions is generated at server startup. See [Authentication docs](docs/api/AUTHENTICATION.md) for key management and permissions.

### Time Control (\`/simulator/time\`)
```
GET  /simulator/time          # Get current time state
POST /simulator/time/advance  # Advance time by duration
POST /simulator/time/set      # Jump to specific time
POST /simulator/time/pause    # Freeze time
POST /simulator/time/resume   # Resume time
```

### Events (\`/events\`)
```
GET  /events                  # List events with filters
POST /events                  # Schedule new event
POST /events/immediate        # Execute event immediately
```

### Modalities (\`/{modality}\`)
```
GET  /{modality}/state        # Get current state
POST /{modality}/query        # Query with filters
POST /{modality}/*            # Modality-specific actions
```

Full API documentation: http://localhost:8000/docs (when server is running)

## 🔗 External Agent Integration

UES is designed as an **agent-interactable simulation platform**:

```
┌─────────────────────────────────────────────────────────────┐
│                    UES Core (Pure Simulation)               │
│  • Deterministic scenario execution                         │
│  • State management & event scheduling                      │
│  • REST API + WebSocket                                     │
└───────────────────────────┬─────────────────────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
   Simulator-Side      User-Side Agent    Developer
   Agent (external)    (being tested)     (Web UI)
         │                  │                  │
         └──────────────────┴──────────────────┘
                    All use the same REST API
```

**Use Cases**:
- **Reactive Agents**: Monitor for sent emails, generate replies
- **Content Generation**: Use LLMs to create realistic test data
- **Trigger-based Events**: Watch for conditions and schedule events
- **Character Simulation**: Maintain personalities that respond consistently

### Example Agents

The `examples/agents/` directory contains complete, runnable agent implementations:

| Example | Description |
|---------|-------------|
| [simple_email_summary](examples/agents/simple_email_summary/) | Basic email summarization agent |
| [email_reply_generator](examples/agents/email_reply_generator/) | Generates contextual email replies |
| [calendar_conflict_resolver](examples/agents/calendar_conflict_resolver/) | Resolves scheduling conflicts |
| [sms_group_chat](examples/agents/sms_group_chat/) | Multi-character SMS conversation simulator |
| [party_planner](examples/agents/party_planner/) | Full integration example with testing harness |

### Agent Testing Harness

Evaluate AI agent performance with the built-in testing framework:

```python
from ues.agent_testing import EvalRunner

runner = EvalRunner(
    scenario_path="./scenario.ues-scenario.json",
    criteria_path="./test_criteria.json",
)
report = await runner.run()
runner.print_report()  # Terminal scoreboard with grades
```

See [docs/agent-testing/AGENT_TESTING.md](docs/agent-testing/AGENT_TESTING.md) for complete documentation.

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Contributing Steps

1. Fork the repository
2. Create a feature branch (\`git checkout -b feature/amazing-feature\`)
3. Make your changes with tests
4. Commit (\`git commit -m 'Add amazing feature'\`)
5. Push (\`git push origin feature/amazing-feature\`)
6. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Pydantic](https://pydantic.dev/) - Data validation using Python type annotations
- [React](https://react.dev/) + [Vite](https://vite.dev/) - Frontend framework and tooling
- [shadcn/ui](https://ui.shadcn.com/) - Beautiful UI components
