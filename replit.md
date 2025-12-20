# User Environment Simulator (UES)

## Overview
A full-stack application for simulating user environments to test AI personal assistants. The system provides a control panel for managing simulation environments with various modalities (Email, SMS, Chat, Calendar, Location, Weather, Time).

## Architecture
- **Backend**: Python FastAPI application (`main.py`) serving REST API
- **Frontend**: React/Vite application (`webapp/`) with TypeScript

## Development Setup

### Backend
- Runs on port 8000 (localhost)
- Entry point: `main.py`
- Dependencies managed via `pyproject.toml`

### Frontend
- Runs on port 5000 (0.0.0.0)
- Built with Vite + React + TypeScript
- Uses Tailwind CSS v4 with shadcn/ui components
- API calls proxied to backend via Vite proxy config

## Running the Application
Both workflows should be running:
1. **Backend API**: `uvicorn main:app --host localhost --port 8000 --reload`
2. **Frontend**: `cd webapp && npm run dev`

## Project Structure
```
├── api/              # FastAPI routes and dependencies
├── client/           # Python API client library
├── models/           # Pydantic models for modalities
├── tests/            # Test suite
├── webapp/           # React frontend
│   ├── src/
│   │   ├── api/      # API client and hooks
│   │   ├── components/
│   │   └── pages/
│   └── package.json
├── main.py           # FastAPI entry point
└── pyproject.toml    # Python dependencies
```

## Deployment
- Build command: `cd webapp && npm install && npm run build`
- Run command: `uvicorn main:app --host 0.0.0.0 --port 5000`
- The FastAPI app serves the built frontend in production
