# User Environment Simulator (UES) - AI Agent Instructions

## Project Overview

UES is an AI-driven testing tool for AI personal assistants, simulating multiple input modalities (email, calendar, SMS, location, weather, etc.) via a RESTful API.

**For architecture details**: See `README.md`, `docs/models/SIMULATION_ENGINE.md`, `docs/api/REST_API.md`
**For current status/roadmap**: See `TODO.md`
**For Python client usage**: See `docs/client/CLIENT_QUICK_REFERENCE.md` for available methods and patterns
**For API access control**: See `docs/api/API_ACCESS_CONTROL.md` for authentication and permissions

## Development Environment

### Common Commands
```bash
uv sync                              # Install dependencies
uv run uvicorn ues.main:app --reload # Start API server (dev)
uv run pytest                        # Run all tests
uv run pytest tests/api/ -v          # Run specific tests
cd webapp && npm run dev             # Start Web UI
```

**IMPORTANT**: Always use `uv run python ...` or `uv run <command>`. Never use plain `python ...` commands.

### Development URLs
When the server is running (`uv run uvicorn ues.main:app --reload`):
- **API Server**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/docs (interactive API testing)
- **ReDoc**: http://localhost:8000/redoc (alternative API docs)
- **OpenAPI Schema**: http://localhost:8000/openapi.json
- **Web UI**: http://localhost:5173 (run `cd webapp && npm run dev`)

**Note**: When the server starts, an admin API key is printed to the console. Save this key - it's required for all API requests. For automated deployments, use `UES_ADMIN_KEY` or `UES_ADMIN_KEY_FILE` env vars (see `docs/api/AUTHENTICATION.md`).

### Environment Variables
The project uses `python-dotenv` to load environment variables from `.env` files:
- `CORS_ORIGINS`: Comma-separated list of allowed CORS origins (default: localhost:5173, localhost:3000)
- `UES_ADMIN_KEY`: Pre-set admin API key secret (at least 32 chars). Avoids random key generation.
- `UES_ADMIN_KEY_FILE`: Path to write admin key credentials as JSON at startup.

See `webapp/.env.example` for web UI environment variables.

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

### Adding a New Modality
When implementing a new modality, follow this checklist:
1. **Models**: Create `src/ues/models/modalities/<modality>_input.py` and `<modality>_state.py`
   - Input class extends `ModalityInput` with action-specific fields
   - State class extends `ModalityState` with `apply_input()`, `clear()`, `create_undo_data()`, `apply_undo()`
2. **Registry**: Register in `src/ues/models/registry.py` `ModalityRegistry`
3. **API Routes**: Create `src/ues/api/routes/<modality>.py` with state/query/submit endpoints
   - **All routes must have authentication** - see API Access Control section below
4. **Route Registration**: Add router to `src/ues/main.py`
5. **Client Sub-client**: Create `src/ues/client/_<modality>.py` with sync/async methods
6. **Client Integration**: Add to `UESClient` and `AsyncUESClient` in `src/ues/client/client.py`
7. **Tests**: Add `tests/models/test_<modality>_input.py`, `test_<modality>_state.py`, and `tests/api/modalities/test_<modality>_routes.py`
8. **Web UI**: Add viewer component in `webapp/src/components/modalities/<modality>/`
9. **Permissions**: Add permission constants to `src/ues/api/auth.py` `Permissions` class

See `docs/api/MODALITY_ROUTES.md` for detailed API patterns and `docs/models/MODALITY_UNDO_NOTES.md` for undo implementation.

## API Access Control

**CRITICAL**: All API routes (except `/`, `/health`, `/docs`, `/redoc`, `/openapi.json`) require authentication via API key.

### Overview
- Authentication via `X-API-Key` header on every request
- Fine-grained permissions: each endpoint has a specific permission
- Admin key generated at startup with full access (`*` permission)
- Keys can be created, listed, and revoked via `/keys` endpoints

### Key Files
- `src/ues/api/auth.py` - `Permissions` class, `require_permission()` dependency, `APIKeyRegistry`
- `src/ues/models/api_key.py` - `APIKey` model with permission checking
- `src/ues/api/routes/keys.py` - Key management endpoints
- `docs/api/API_ACCESS_CONTROL.md` - Full design documentation

### Adding Authentication to Route Handlers

**Every route handler must include a permission dependency.** Use `require_permission()` from `ues.api.auth`:

```python
from typing import Annotated
from fastapi import Depends

from ues.api.auth import Permissions, require_permission
from ues.models.api_key import APIKey

@router.get("/state")
async def get_state(
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.EMAIL_STATE))],
) -> ModalityStateResponse:
    ...

@router.post("/send")
async def send_email(
    request: SendEmailRequest,
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.EMAIL_SEND))],
) -> ModalityActionResponse:
    ...
```

### Permission Naming Convention
Permissions follow the pattern `{resource}:{action}` or `{resource}:{sub-resource}:{action}`:
- `email:state`, `email:send`, `email:receive`
- `calendar:calendars:list`, `calendar:calendars:create`
- `simulation:start`, `simulation:stop`

### Adding New Permissions
When adding new endpoints, you must:
1. **Add permission constant** to `src/ues/api/auth.py` `Permissions` class
2. **Add permission dependency** to the route handler
3. **Update `docs/api/API_ACCESS_CONTROL.md`** permission tables

Example adding a new permission:
```python
# In src/ues/api/auth.py
class Permissions:
    # ... existing permissions ...
    
    # My New Modality (/mymodality)
    MYMODALITY_STATE = "mymodality:state"
    MYMODALITY_QUERY = "mymodality:query"
    MYMODALITY_UPDATE = "mymodality:update"
```

### Wildcard Permissions
- `*` - Full admin access (all permissions)
- `email:*` - All email permissions
- `calendar:*` - All calendar permissions (includes sub-resources)

### Testing Routes with Authentication

Tests must provide valid API keys. Use fixtures that initialize the registry:

```python
@pytest.fixture
def admin_client(fresh_engine):
    """Provide a TestClient with admin API key authentication."""
    from ues.api.auth import initialize_api_key_registry, shutdown_api_key_registry
    
    app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine
    admin_secret, admin_key = initialize_api_key_registry()
    
    client = TestClient(app)
    client.headers["X-API-Key"] = admin_secret
    
    yield client, admin_secret, admin_key
    
    shutdown_api_key_registry()
    app.dependency_overrides.clear()
```

### Endpoints Without Authentication
Only these endpoints are exempt from authentication:
- `GET /` - Root welcome message
- `GET /health` - Health check
- `GET /docs` - Swagger UI
- `GET /redoc` - ReDoc
- `GET /openapi.json` - OpenAPI schema

## Non-Code Documentation Imperatives
- Ensure documentation is clear, concise, and accessible to future developers
- Documentation is also for your future self, use it to store important context

### Post-Implementation Documentation
- When working from one or more documents (e.g., TODO lists, plans, design descriptions), always update documents after implementing a feature
- Carefully review both your code changes and your thinking and output to accurately reflect what was done
- It is crucial that documentation reflects the current state of the project, so you must update it as part of your development process

### Commit Messages
- Use clear, descriptive commit messages
- Follow industry-standard conventions (e.g., "Add", "Fix", "Update", "Refactor", "Remove")
- Always add "AI generated commit message" at the end of the commit message body

## Coding Instructions
- When writing code which calls methods or uses classes defined in this project, always make sure you first read and understand the relevant code
- Avoid hallucinations - if you are unsure about how something works, refer to the existing code or documentation

## Code Style Guidelines

### Timezone Handling
- Always use **timezone-aware** datetime objects
- Be VERY CAREFUL when using `datetime.now()` or `datetime.utcnow()` - these should only be used when capturing wall-clock time, not simulator time

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

### Testing Patterns
- **Organize tests by layer**: Tests are organized into `tests/models/`, `tests/api/`, `tests/client/`
- **API tests**: Integration tests in `tests/api/{modalities,time,events,simulation,environment,scenario}/`, unit tests in `tests/api/unit/`, workflow tests in `tests/api/workflows/`
- **Model tests by modality**: Each modality has two test files: `test_<modality>_input.py` and `test_<modality>_state.py`
- **Shared fixtures**: Use `tests/conftest.py` for shared fixtures, `tests/fixtures/` for pre-built test data
- **API testing guidelines**: See `tests/API_TESTING_GUIDELINES.md` for conventions
- **Distinguish general vs. specific tests**: Use docstrings and comments to clearly mark which tests apply to:
  - **General ModalityInput/ModalityState behavior**: Tests that verify the base class contract (e.g., instantiation, serialization, abstract method implementation). These patterns should be replicated for all modalities.
  - **Modality-specific behavior**: Tests that verify unique features or validation rules for that specific modality (e.g., LocationInput's lat/lon range validation, EmailState's thread management).
- **Test naming convention**: Use descriptive names that indicate scope:
  - `test_instantiation_*`: General pattern for all modalities
  - `test_<specific_feature>_*`: Modality-specific tests
- **Test organization**: Group related tests using pytest test classes when helpful
- **Use fixtures**: Leverage pre-built fixtures from `tests/fixtures/modalities/` to reduce boilerplate

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
