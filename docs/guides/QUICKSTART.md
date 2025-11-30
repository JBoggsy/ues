# UES Quickstart Guide

Get the User Environment Simulator running and make your first API request in under 5 minutes.

## Prerequisites

- **Python 3.12+** installed
- **uv** package manager ([installation guide](https://docs.astral.sh/uv/getting-started/installation/))

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/JBoggsy/ues.git
   cd ues
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

3. **Run the tests (optional, verifies installation):**
   ```bash
   uv run pytest -q
   ```
   You should see `1807 passed` if everything is working.

## Starting the Server

Start the UES API server:

```bash
uv run uvicorn main:app --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

The API is now running at `http://localhost:8000`.

## Interactive API Documentation

Once the server is running, explore the API interactively:

- **Swagger UI** (interactive testing): http://localhost:8000/docs
- **ReDoc** (alternative view): http://localhost:8000/redoc
- **OpenAPI Schema** (JSON): http://localhost:8000/openapi.json

## Your First Request

Let's start a simulation and check its status.

### Using curl


#### Start the simulation
```bash
curl -X POST http://localhost:8000/simulation/start \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Example response from `/simulation/start`:**
```json
{
  "simulation_id": "351580b7-99d4-4c6e-850c-8b1aaf027079",
  "status": "running",
  "current_time": "2025-11-30T17:00:00.000000+00:00",
  "auto_advance": false,
  "time_scale": null
}
```

#### Check simulation status
```bash
curl http://localhost:8000/simulation/status
```

**Example response from `/simulation/status`:**
```json
{
    "is_running":true,
    "current_time":"2025-11-30T17:00:00.000000+00:00",
    "is_paused":false,
    "auto_advance":false,
    "time_scale":1.0,
    "pending_events":0,
    "executed_events":0,
    "failed_events":0,
    "next_event_time":null
}
```

### Using Python requests

```python
import requests

BASE_URL = "http://localhost:8000"

# Start the simulation
response = requests.post(f"{BASE_URL}/simulation/start", json={})
print(f"Started: {response.json()}")

# Check simulation status
response = requests.get(f"{BASE_URL}/simulation/status")
status = response.json()
print(f"Running: {status['is_running']}")
print(f"Current time: {status['current_time']}")
```

### Using UES Python Client (Coming Soon)

```python
# Future: UES client library for cleaner API interactions
# from ues_client import UESClient
#
# client = UESClient("http://localhost:8000")
# client.simulation.start()
# status = client.simulation.status()
# print(f"Current time: {status.current_time}")
```

## Core Concepts

Before diving deeper, understand these key concepts:

### Simulator Time vs. Wall-Clock Time

UES maintains its own internal clock separate from real time. This allows you to:
- Start simulations at any date/time (e.g., "Monday 9 AM")
- Advance time in discrete steps (manual control)
- Fast-forward through events (auto-advance at 10x, 100x speed)
- Pause and resume the simulation

### Events

Events are scheduled changes to the simulated environment. For example:
- "User receives an email at 9:15 AM"
- "Calendar reminder triggers at 10:00 AM"
- "SMS arrives from spouse at 12:30 PM"

Events are created with a scheduled time and only execute when the simulator time reaches that point.

### Modalities

Modalities are the different data types the simulator manages:
- **Email**: Inbox, sent mail, drafts, threads
- **SMS**: Text message conversations
- **Calendar**: Events and appointments
- **Chat**: AI assistant conversation history
- **Location**: User's current location
- **Weather**: Current conditions and forecast
- **Time**: Timezone and display preferences

Each modality has:
- A **state** (current data, e.g., all emails in inbox)
- **Inputs** (events that modify state, e.g., "new email received")

## Basic Workflow

Here's a typical workflow for testing an AI assistant:

### 1. Start the Simulation

```bash
curl -X POST http://localhost:8000/simulation/start -H "Content-Type: application/json" -d '{}'
```

### 2. Schedule Some Events

Create an email that will arrive at the current simulator time:

```bash
curl -X POST http://localhost:8000/events/immediate \
  -H "Content-Type: application/json" \
  -d '{
    "modality": "email",
    "data": {
      "operation": "receive",
      "from_address": "boss@company.com",
      "to_addresses": ["user@example.com"],
      "subject": "Urgent: Project deadline moved",
      "body_text": "Hi, the deadline has been moved to Friday. Please update your timeline."
    }
  }'
```

### 3. Advance Time to Execute Events

Events only execute when simulator time advances past their scheduled time:

```bash
curl -X POST http://localhost:8000/simulator/time/advance \
  -H "Content-Type: application/json" \
  -d '{"seconds": 1}'
```

### 4. Check the Environment State

See what the AI assistant would "see":

```bash
# Get email state
curl http://localhost:8000/email/state

# Or get all modality states at once
curl http://localhost:8000/environment/state
```

### 5. Simulate AI Assistant Response

Add a chat message (simulating user asking the assistant):

```bash
curl -X POST http://localhost:8000/chat/send \
  -H "Content-Type: application/json" \
  -d '{
    "role": "user",
    "content": "What emails do I have?"
  }'
```

Advance time and check chat state:

```bash
curl -X POST http://localhost:8000/simulator/time/advance \
  -H "Content-Type: application/json" \
  -d '{"seconds": 1}'

curl http://localhost:8000/chat/state
```

## Next Steps

- **[Manual Time Control Tutorial](./TUTORIAL_MANUAL_TIME.md)** - Deep dive into time management
- **[Building an Agent Loop](./TUTORIAL_AGENT_LOOP.md)** - Create an AI agent that responds to user messages
- **[API Examples](./EXAMPLES.md)** - Copy-paste examples for common operations
- **[REST API Reference](../REST_API.md)** - Complete endpoint documentation

## Troubleshooting

### Server won't start

Make sure you're in the project directory and have run `uv sync`:
```bash
cd ues
uv sync
uv run uvicorn main:app --reload
```

### "Simulation not running" errors

Most endpoints require an active simulation. Start one first:
```bash
curl -X POST http://localhost:8000/simulation/start -H "Content-Type: application/json" -d '{}'
```

### Events not appearing in state

Remember: events only execute when time advances. After creating an event, advance time:
```bash
curl -X POST http://localhost:8000/simulator/time/advance \
  -H "Content-Type: application/json" \
  -d '{"seconds": 1}'
```

### Reset and start fresh

To clear all state and start over:
```bash
curl -X POST http://localhost:8000/simulation/reset -H "Content-Type: application/json" -d '{}'
curl -X POST http://localhost:8000/simulation/start -H "Content-Type: application/json" -d '{}'
```
