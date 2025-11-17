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
This is an early-stage greenfield project. The codebase contains:
- `main.py`: Minimal placeholder entry point
- `pyproject.toml`: Python 3.12+ project with no dependencies yet
- `README.md`: Comprehensive vision document

**No existing data structures or schemas** - design from scratch with best practices.

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
uv run main.py
# or: uvicorn main:app --reload
```

## Implementation Priorities

When building features, refer to the README's modality list:
1. User Location, Current Time, Current Weather Data
2. Chat-style User Interaction, Email, Calendar, Text (SMS/RCS)
3. File System, Discord, Slack, Social Media, Screen Simulation

Each modality needs:
- Timestamp management
- Developer-defined initial inputs
- Optional AI agent integration for dynamic generation
- RESTful API endpoints

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

## Recommended Tech Stack

- **Backend**: FastAPI + Uvicorn (async, auto-docs, WebSocket support)
- **Data Models**: Pydantic (validation, serialization)
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

