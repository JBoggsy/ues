# Contributing to UES

Thank you for your interest in contributing to the User Environment Simulator (UES)! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Code Style](#code-style)
- [Documentation](#documentation)

## Code of Conduct

Please be respectful and constructive in all interactions. We're building a welcoming community for developers of all backgrounds and experience levels.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/ues.git
   cd ues
   ```
3. **Add the upstream remote**:
   ```bash
   git remote add upstream https://github.com/JBoggsy/ues.git
   ```

## Development Setup

### Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Node.js 18+ and npm (for Web UI development)
- Git

### Backend Setup

```bash
# Install dependencies using uv (recommended)
uv sync

# Or using pip
pip install -e ".[dev]"

# Verify installation
uv run pytest --version
```

### Web UI Setup

```bash
cd webapp
npm install
```

### Running the Development Server

```bash
# Start the API server (from project root)
uv run ues server --reload

# Or directly with uvicorn
uv run uvicorn ues.main:app --reload
```

The API will be available at:
- API Server: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Running the Web UI

```bash
cd webapp
npm run dev
```

The Web UI will be available at http://localhost:5173

## Making Changes

### Branch Naming

Create a descriptive branch name:
- `feature/add-contacts-modality`
- `fix/email-threading-bug`
- `docs/update-api-reference`
- `refactor/simplify-event-queue`

```bash
git checkout -b feature/your-feature-name
```

### Commit Messages

Use clear, descriptive commit messages:
- Start with a verb: "Add", "Fix", "Update", "Refactor", "Remove"
- Keep the first line under 72 characters
- Add details in the body if needed

Example:
```
Add contacts modality with basic CRUD operations

- Implement ContactState with contact storage
- Add ContactInput actions (add, update, delete, search)
- Include API routes for /contacts endpoints
- Add comprehensive test coverage

AI generated commit message
```

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/api/modalities/test_email_routes.py

# Run with verbose output
uv run pytest -v

# Run tests matching a pattern
uv run pytest -k "email"

# Run with coverage
uv run pytest --cov=api --cov=models
```

### Test Organization

- `tests/models/` - Unit tests for data models
- `tests/api/` - API integration tests
- `tests/client/` - Client library tests

### Writing Tests

- Follow existing patterns in the test files
- Use descriptive test function names
- Include both success and error cases
- Use fixtures from `tests/conftest.py`

## Submitting Changes

### Pull Request Process

1. **Update your branch** with the latest upstream changes:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Push your branch**:
   ```bash
   git push origin feature/your-feature-name
   ```

3. **Create a Pull Request** on GitHub with:
   - Clear title describing the change
   - Description of what changed and why
   - Reference any related issues
   - Screenshots for UI changes

4. **Address review feedback** by pushing additional commits

### PR Checklist

Before submitting, ensure:
- [ ] All tests pass (`uv run pytest`)
- [ ] Code follows project style guidelines
- [ ] Documentation is updated if needed
- [ ] Commit messages are clear and descriptive
- [ ] Branch is up-to-date with main

## Code Style

### Python

- Use **Google-style docstrings**
- Include **type hints** on all function parameters and returns
- Maximum **100 characters per line**
- Keep imports at the **top of files**
- Prioritize **readability over cleverness**

Example:
```python
def process_event(
    event: SimulatorEvent,
    environment: Environment,
    *,
    validate: bool = True,
) -> EventResult:
    """Process a simulator event and update the environment.
    
    Args:
        event: The event to process.
        environment: The current environment state.
        validate: Whether to validate the event before processing.
    
    Returns:
        The result of processing the event.
    
    Raises:
        ValidationError: If validation is enabled and the event is invalid.
    """
    if validate:
        event.validate()
    
    return environment.apply_event(event)
```

### TypeScript (Web UI)

- Follow the existing ESLint configuration
- Use TypeScript types for all components and functions
- Prefer functional components with hooks

### Timezone Handling

- Always use **timezone-aware** datetime objects
- Use simulator time, not wall-clock time (`datetime.now()`)

### Error Handling

- Avoid try-except blocks during prototyping
- Let errors surface naturally for debugging
- Only catch exceptions when there's a specific recovery strategy

## Documentation

### When to Update Docs

- Adding new features or modalities
- Changing API endpoints or behavior
- Modifying installation or setup procedures
- Fixing errors in existing documentation

### Documentation Locations

- `README.md` - Project overview and quickstart
- `docs/` - Detailed technical documentation
- `docs/guides/` - How-to guides and tutorials
- Code docstrings - API reference

### Adding a New Modality

Follow the checklist in `.github/copilot-instructions.md`:
1. Create models in `src/ues/models/modalities/`
2. Register in `src/ues/models/registry.py`
3. Add API routes in `src/ues/api/routes/`
4. Create client sub-client in `src/ues/client/`
5. Add tests in `tests/`
6. Add Web UI component in `webapp/src/components/modalities/`
7. Update documentation

## Questions?

If you have questions about contributing:
- Open a [Discussion](https://github.com/JBoggsy/ues/discussions) on GitHub
- Check existing issues and documentation

Thank you for contributing to UES! 🎉
