# UES Green Agent

The UES Green Agent is an [A2A](https://a2a-protocol.org/)-compatible benchmark agent for the [AgentBeats competition](https://rdi.berkeley.edu/agentx-agentbeats). It evaluates AI personal assistant agents ("Purple Agents") on their ability to handle multi-modal tasks in simulated environments using the User Environment Simulator (UES).

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- UES dependencies installed (`uv sync` from project root)

### Running the Green Agent Server

```bash
# From the green agent directory
cd agentbeats/green

# Start the A2A server (default: port 9009)
uv run python server.py

# Or with custom options
uv run python server.py --host 0.0.0.0 --port 9009 --card-url http://myserver:9009/
```

### Command Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--host` | `0.0.0.0` | Host to bind the server |
| `--port` | `9009` | Port to bind the server |
| `--card-url` | Auto-generated | URL advertised in the Agent Card |

## How It Works

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         AgentBeats Platform                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ 1. assessment_request (A2A)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         UES Green Agent                                  │
│  • Receives assessment request                                           │
│  • Resets and loads scenario into UES                                    │
│  • Provisions API keys (proctor + user)                                  │
│  • Orchestrates turn-based assessment loop                               │
│  • Streams task updates to platform                                      │
│  • Evaluates results and produces scoring artifact                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ 2. A2A messages + UES REST API
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Purple Agent (Participant)                       │
│  • Receives turn notifications via A2A                                   │
│  • Queries environment via UES REST API                                  │
│  • Performs actions (send email, create event, etc.)                     │
│  • Signals turn completion                                               │
└─────────────────────────────────────────────────────────────────────────┘
```

### Assessment Lifecycle

1. **Assessment Request**: The AgentBeats platform sends an evaluation request with:
   - `participants`: Map of role → agent URL (requires `"assistant"` role)
   - `config`: Assessment configuration (`scenario_id`, optional `seed`, `verbose_updates`)

2. **Setup Phase**:
   - Green Agent resets UES to clean state
   - Loads the specified scenario
   - Generates API keys (proctor key for self, user key for Purple)

3. **Assessment Start**: Green sends `AssessmentStartMessage` to Purple containing:
   - `ues_url`: Base URL of UES REST API
   - `api_key`: User-level API key for authentication
   - `assessment_instructions`: Fixed string directing agent to query `/chat/state` for user prompt
   - `current_time`: Current simulator time
   - `initial_state_summary`: Counts of items per modality (chat always has ≥1 for user prompt)

4. **Turn Loop**:
   - Purple queries UES state and performs actions via REST API
   - Purple sends `TurnCompleteMessage` with action count and optional time step
   - Green advances simulator time and processes scheduled events
   - Green sends `TurnStartMessage` with new time and events processed
   - Loop repeats until termination

5. **Termination**: Assessment ends when:
   - Scenario time limit reached
   - Purple sends `EarlyCompletionMessage`
   - Purple timeout (no response within turn timeout)
   - Error occurs

6. **Evaluation**: Green retrieves event trace, runs evaluation criteria, computes scores, and produces results artifact.

### Module Structure

| Module | Description |
|--------|-------------|
| `server.py` | A2A server entry point, creates Agent Card |
| `executor.py` | A2A AgentExecutor, manages assessment sessions |
| `agent.py` | Core Agent class, orchestrates assessment lifecycle |
| `schemas.py` | Pydantic models for A2A message schemas |
| `messenger.py` | A2A messaging utilities for Purple communication |
| `key_manager.py` | API key provisioning and lifecycle management |
| `updates.py` | Task update streaming for platform observability |

## A2A Message Schemas

### Green → Purple Messages

**AssessmentStartMessage**
```json
{
  "ues_url": "http://localhost:8000",
  "api_key": "user-level-token-...",
  "assessment_instructions": "You are a personal assistant AI being evaluated... Query the chat state (GET /chat/state) to find the most recent message from the user and follow the instructions provided there.",
  "current_time": "2026-01-22T09:00:00Z",
  "initial_state_summary": {
    "email": { "total": 12, "unread": 5 },
    "calendar": { "total": 8, "events_today": 3 },
    "sms": { "total": 15, "unread": 2 },
    "chat": { "total": 1, "unread": 1 }
  }
}
```

**TurnStartMessage**
```json
{
  "current_time": "2026-01-22T10:00:00Z",
  "events_processed": 3
}
```

**AssessmentCompleteMessage**
```json
{
  "reason": "scenario_complete",
  "message": "Assessment finished successfully"
}
```

### Purple → Green Messages

**TurnCompleteMessage**
```json
{
  "actions_taken": 3,
  "notes": "Replied to 2 urgent emails, archived 1 spam thread",
  "time_step": "PT1H"
}
```

**EarlyCompletionMessage**
```json
{
  "reason": "All goals achieved - inbox empty, all urgent emails replied"
}
```

## API Access Control

The Green Agent uses API key-based access control to enforce what Purple Agents can access:

| Level | Holder | Access |
|-------|--------|--------|
| `proctor` | Green Agent | Full API access (all endpoints) |
| `user` | Purple Agent | Restricted access (see below) |

### Purple Agent Allowed Endpoints

**Read Access:**
- `GET /{modality}/state` — Full state for any modality
- `POST /{modality}/query` — Query with filters
- `GET /simulator/time` — Current simulation time (read-only)

**Action Access:**
- Email: `send`, `reply`, `forward`, `move`, `archive`, `delete`, `label`, `mark_read`
- SMS: `send`, `react`, `delete`, `mark_read`
- Calendar: `create`, `update`, `delete`, `rsvp`
- Chat: `send`

**Forbidden:**
- Simulator-side actions (`/email/receive`, `/sms/receive`, etc.)
- Time control (`/simulator/time/advance`, `/simulator/time/set`)
- Simulation control (`/simulator/reset`, `/simulator/clear`)
- Event history, undo/redo, holds, webhooks

## Task Updates (Streaming)

Green Agent streams task updates to the AgentBeats platform for real-time observability:

| Update Type | When |
|-------------|------|
| `log_assessment_started` | Assessment begins (includes `user_prompt` from chat) |
| `log_scenario_loaded` | Scenario imported into UES |
| `log_turn_started` | New turn begins |
| `log_turn_completed` | Purple signals ready |
| `log_simulation_advanced` | Time progresses |
| `log_assessment_complete` | Assessment ends |

Set `verbose_updates: false` in config to only emit start/complete updates.

## Example Assessment Request

```json
{
  "participants": {
    "assistant": "http://localhost:9010/"
  },
  "config": {
    "scenario_id": "email-triage-basic",
    "verbose_updates": true,
    "seed": 42
  }
}
```

## Development

### Running Tests

```bash
# From project root
uv run pytest tests/ -k "green" -v
```

### Related Documentation

- [AgentBeats Submission Plan](../../docs/AGENTBEATS_SUBMISSION.md)
- [A2A Flow Design](../../docs/AGENTBEATS_A2A_FLOW.md)
- [UES REST API](../../docs/REST_API.md)
