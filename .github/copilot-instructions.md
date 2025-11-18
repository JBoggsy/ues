# User Environment Simulator (UES) - AI Agent Instructions

## Project Overview

UES is an AI-driven testing and prototyping tool for AI personal assistants. It provides a web app-based UI that simulates multiple input modalities (email, calendar, SMS, location, weather, file system, Discord, Slack, social media, screen simulation) to test how AI agents handle realistic user environments.

**Key Concept**: The simulator creates a controlled, replicable environment where developers can design sequences of events (new emails arriving, texts being sent, files changing) that an AI personal assistant "sees" in real-time via a RESTful API.

## Architecture

### Core Components (Planned)
- **Web App UI**: Interface for designing simulated environments and event sequences
- **RESTful API**: Exposes simulated modalities to connected AI agents
- **Event System**: Coordinates timestamped inputs across modalities with initial simulator time
- **Agent Integration**: Optional AI agents that generate new inputs or react to assistant responses

### Current State
The project has established core infrastructure with working data models:
- `main.py`: Minimal placeholder entry point (to be expanded with FastAPI)
- `pyproject.toml`: Python 3.12+ project with Pydantic dependency
- `README.md`: Comprehensive vision document
- `models/`: Complete data model layer with base classes and modality implementations
  - Core infrastructure: `SimulatorEvent`, `SimulatorTime`, `EventQueue`, `Environment`, `SimulationEngine`
  - Base classes: `ModalityInput`, `ModalityState`
  - Modality implementations: Email, SMS, Calendar, Chat, Weather, Location, Time, Discord, Slack, Social Media, File System, Screen
- `docs/`: Comprehensive documentation for all core components and modalities

**Next Steps**: Implement FastAPI REST API layer and web UI for environment configuration.

## Development Environment

### Setup
- **Python Version**: 3.12+ (specified in `.python-version`)
- **Package Manager**: `uv` for dependency management
- **Virtual Environment**: `.venv` directory (gitignored)
- **Web Framework**: FastAPI (recommended for API-first design with auto-documentation)

### Common Commands
```bash
# Install dependencies
uv sync

# Add new dependency
uv add <package-name>

# Run the application (will use FastAPI + Uvicorn)
uv run python main.py
# or: uv run uvicorn main:app --reload

# Run any Python script or command
uv run python script.py
# or: uv run python -m module.name
```

**IMPORTANT**: Always use `uv run python ...` (or `uv run <command>`) when executing Python code. Do NOT use plain `python ...` commands, as they will use the system Python installation which won't have access to project dependencies installed in the virtual environment.

## Implementation Priorities

When building features, refer to the README's modality list:
1. User Location, Current Time, Current Weather Data ✅ (Models complete)
2. Chat-style User Interaction, Email, Calendar, Text (SMS/RCS) ✅ (Models complete)
3. File System, Discord, Slack, Social Media, Screen Simulation ⏳ (Stub files only)

**Completed**:
- ✅ Core simulation engine and event system
- ✅ Priority 1 & 2 modality data models (Location, Time, Weather, Chat, Email, Calendar, SMS)
- ✅ Comprehensive documentation for implemented components

**In Progress / Next Steps**:
- ⏳ Priority 3 modality implementations (Contacts, File System, Discord, Slack, Social Media, Screen)
- ⏳ FastAPI REST API implementation
- ⏳ Web UI for environment configuration
- ⏳ API endpoints for each modality
- ⏳ Agent integration framework

## Design Patterns to Follow

- **API-First**: All modalities must be accessible via REST API for easy agent integration
  - Use FastAPI for automatic OpenAPI documentation
  - Pydantic models for type-safe event/modality data structures
- **Replicability**: Environment configurations and event sequences must be savable and reproducible
  - Persist configurations as JSON/YAML
  - Deterministic event ordering by simulator timestamp
- **Controlled Randomness**: AI-generated inputs should be controllable/disableable for testing
- **Real-time Simulation**: Events occur at specified simulator timestamps, not wall-clock time
  - Avoid `datetime.now()` - use simulator time context
- **General Purpose**: Design for any AI personal assistant, not specific to AIPA
- **Modularity**: Each modality should be a separate module/component for easy extension

## Tech Stack

- **Backend**: FastAPI + Uvicorn (async, auto-docs, WebSocket support) - *To be implemented*
- **Data Models**: Pydantic ✅ (validation, serialization) - *Implemented*
- **Package Management**: `uv` ✅ - *Active*
- **Storage**: TBD (SQLite/PostgreSQL for events, filesystem for configs)
- **Frontend**: TBD (React/Vue SPA or FastAPI templates)

## Code Style Guidelines

### Documentation
- Use **Google-style docstrings** for all functions, classes, and modules
- Always include type hints on function parameters and return values

### Error Handling
- **Avoid try-except blocks** during prototyping - let errors surface naturally
- Do NOT wrap imports in try-except blocks - standard import errors provide sufficient information
- Exceptions should only be caught when there's a specific recovery strategy

### Imports
- Keep all imports at the **top of the file**
- Never add imports inside classes or functions
- Group imports: standard library, third-party, local modules

### Code Clarity
- Prioritize **readability over cleverness**
- Avoid one-liners that sacrifice clarity
- Prefer explicit, verbose code over condensed "clever" solutions
- Whitespace and clear variable names matter more than brevity
- Be careful to avoid large, monolithic functions - break into smaller helper functions

### Line Length
- Aim for a maximum of **100 characters per line**

**Example:**
```python
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SimulatorEvent(BaseModel):
    """Represents a single event in the simulation timeline.
    
    Args:
        timestamp: The simulator time when this event occurs.
        modality: The input modality (email, sms, etc.).
        data: The event-specific payload.
        agent_id: Optional ID of the agent that generated this event.
    
    Returns:
        A validated SimulatorEvent instance.
    """
    timestamp: datetime
    modality: str
    data: dict
    agent_id: Optional[str] = None
```

