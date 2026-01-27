# UES Baseline Purple Agent

A baseline A2A-compatible Purple Agent for the AgentBeats-AgentX competition that demonstrates how to interact with the UES (User Environment Simulator) benchmark.

## Overview

### What is a Purple Agent?

In the AgentBeats ecosystem, a **Purple Agent** (also called a "competing agent" or "participant") is the agent being evaluated. It receives assessment instructions from a Green Agent (evaluator), interacts with a simulated environment, and demonstrates its capabilities to be scored.

For the UES benchmark, the Purple Agent plays the role of a **Personal Assistant AI** — helping a simulated user manage their email, calendar, SMS messages, and chat conversations within a controlled, reproducible environment.

### Purpose of This Baseline Agent

This baseline Purple Agent serves multiple purposes:

1. **Demonstration**: Shows how a Purple Agent should interact with the UES Green Agent and REST API
2. **Reference Implementation**: Provides a working example of A2A protocol compliance
3. **Baseline Comparison**: Establishes a minimum performance baseline for evaluation
4. **Testing**: Enables end-to-end testing of the UES benchmark infrastructure

The baseline agent is intentionally simple — it demonstrates correct protocol compliance rather than optimal task performance. Competition participants should use this as a starting point and implement more sophisticated reasoning, planning, and action strategies.

---

## A2A Protocol Compliance

The Purple Agent must implement the [A2A (Agent-to-Agent) protocol](https://a2a-protocol.org/latest/) to communicate with the Green Agent. This ensures interoperability with any A2A-compatible benchmark on the AgentBeats platform.

### Required Capabilities

| Capability | Description |
|------------|-------------|
| **A2A Server** | Expose an A2A-compatible HTTP endpoint |
| **Agent Card** | Provide metadata describing agent skills and capabilities |
| **Message Handling** | Process incoming A2A messages from the Green Agent |
| **Task Lifecycle** | Manage task state (working, completed, failed) |
| **Status Updates** | Emit progress updates via A2A task updates |

### Agent Card

The agent must expose an agent card at `/.well-known/agent.json` describing its capabilities:

```json
{
  "name": "UES Baseline Personal Assistant",
  "description": "A baseline personal assistant agent for the UES benchmark",
  "version": "1.0.0",
  "skills": [
    {
      "id": "personal_assistant",
      "name": "Personal Assistant",
      "description": "Manages email, calendar, SMS, and chat for a user"
    }
  ]
}
```

---

## Assessment Lifecycle

### 1. Receive Assessment Start

The Green Agent sends an `assessment_start` message containing:

```json
{
  "ues_url": "http://ues:8000",
  "api_key": "user-level-api-key",
  "assessment_instructions": "You are a personal assistant AI being evaluated...",
  "current_time": "2026-01-22T09:00:00Z",
  "initial_state_summary": {
    "email": { "total": 12, "unread": 5 },
    "calendar": { "total": 8, "events_today": 3 },
    "sms": { "total": 15, "unread": 2 },
    "chat": { "total": 1, "unread": 1 }
  }
}
```

**Key fields:**
- `ues_url`: Base URL for all UES REST API calls
- `api_key`: Include in `X-API-Key` header for all UES requests
- `assessment_instructions`: Fixed text directing agent to check chat for user instructions
- `current_time`: Starting simulation time
- `initial_state_summary`: Overview of items in each modality

### 2. Retrieve User Instructions

The actual assessment goals and constraints are delivered via the **chat modality**. The agent MUST:

1. Query `GET /chat/state` to retrieve chat messages
2. Find the message from role `"user"` containing the instructions
3. Parse and understand the goals, rules, and context provided

Example user instructions (from chat):
```
Hi! I need your help managing my inbox today. Here's what I need:

**Goals:**
- Reply to all urgent emails (marked with [URGENT] in subject)
- Archive any completed threads
- Flag emails that need follow-up for later

**Rules:**
- Don't delete any emails
- Don't send emails to external domains
- Be professional in all responses

My schedule is busy today, so prioritize anything time-sensitive. Thanks!
```

### 3. Execute Turn Loop

The agent operates in a turn-based loop:

```
┌─────────────────────────────────────────────────────────────────┐
│  TURN LOOP                                                      │
│                                                                 │
│  1. Query UES state (GET /email/state, /calendar/state, etc.)  │
│  2. Analyze the situation and decide what to do                 │
│  3. Take actions via UES REST API (POST /email/submit, etc.)   │
│  4. Send turn_complete to Green Agent                           │
│  5. Wait for turn_start from Green Agent                        │
│  6. Repeat until assessment ends                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Turn Complete Message

After taking actions, send a `turn_complete` message to the Green Agent:

```json
{
  "actions_taken": 3,
  "notes": "Replied to 2 urgent emails, archived 1 spam thread",
  "time_step": "PT1H"
}
```

- `actions_taken`: Number of UES API calls made this turn
- `notes`: Optional reasoning/explanation for logging and potential scoring
- `time_step`: ISO 8601 duration for how much to advance simulator time (e.g., "PT1H" = 1 hour, "PT30M" = 30 minutes)

#### Turn Start Message

After time advances, receive a `turn_start` message:

```json
{
  "current_time": "2026-01-22T10:00:00Z",
  "events_processed": 3
}
```

- `current_time`: New simulation time
- `events_processed`: Number of events that fired (new emails arrived, calendar reminders, etc.)

### 4. Signal Completion

The assessment ends when:
- **Scenario complete**: Simulation time reaches the scenario's end time
- **Early completion**: Agent sends an `early_completion` message when done
- **Timeout**: Agent doesn't respond within the turn timeout
- **Error**: Unrecoverable error occurs

To signal early completion:
```json
{
  "reason": "All tasks completed successfully"
}
```

### 5. Receive Assessment Complete

The Green Agent sends an `assessment_complete` message:

```json
{
  "reason": "scenario_complete"
}
```

Reasons: `"scenario_complete"`, `"early_completion"`, `"timeout"`, `"error"`

---

## Quick Start Example

The easiest way to create a Purple Agent is to extend `BaseAgent` and use the provided infrastructure:

```python
"""Simple email-reading agent."""

from client import AsyncUESClient

from agentbeats.purple import (
    AssessmentContext,
    AssessmentStartMessage,
    BaseAgent,
    EarlyCompletionMessage,
    TurnCompleteMessage,
    run_purple_agent,
)


class MyEmailAgent(BaseAgent):
    """A simple agent that reads and marks emails as read."""

    async def on_assessment_start(
        self,
        message: AssessmentStartMessage,
        context: AssessmentContext,
        ues: AsyncUESClient,
    ) -> None:
        """Retrieve user instructions from chat."""
        chat_state = await ues.chat.get_state()
        for msg in chat_state.messages:
            if msg.role == "user":
                # Store instructions for later use
                context.custom_data["instructions"] = msg.content
                break

    async def execute_turn(
        self,
        context: AssessmentContext,
        ues: AsyncUESClient,
    ) -> TurnCompleteMessage | EarlyCompletionMessage:
        """Process unread emails each turn."""
        email_state = await ues.email.get_state()
        unread_emails = [e for e in email_state.emails if not e.is_read]

        if not unread_emails:
            return EarlyCompletionMessage(reason="All emails processed")

        # Mark each unread email as read
        for email in unread_emails:
            await ues.email.mark_as_read(email.id)

        return TurnCompleteMessage(
            actions_taken=len(unread_emails),
            notes=f"Marked {len(unread_emails)} emails as read",
            time_step="PT1H",
        )


if __name__ == "__main__":
    agent = MyEmailAgent()
    run_purple_agent(
        agent=agent,
        name="My Email Agent",
        description="A simple agent that reads emails",
    )
```

Run the agent:
```bash
uv run python my_agent.py --host 0.0.0.0 --port 9009
```

See [examples/simple_agent.py](examples/simple_agent.py) for a complete working example.

---

## UES REST API Access

### Authentication

All UES API requests require the API key provided in `assessment_start`:

```
X-API-Key: <api_key>
```

Or:
```
Authorization: Bearer <api_key>
```

### Allowed Endpoints

The Purple Agent has **user-level access** — it can read all state and perform user-side actions, but cannot control the simulation or inject events.

#### State & Query (Read)

| Endpoint | Description |
|----------|-------------|
| `GET /{modality}/state` | Get full current state for a modality |
| `POST /{modality}/query` | Query with filters |
| `GET /simulator/time` | Get current simulation time |

**Modalities**: `email`, `sms`, `chat`, `calendar`, `location`, `weather`

#### User-Side Actions (Write)

| Modality | Allowed Actions |
|----------|-----------------|
| Email | `send`, `reply`, `forward`, `move`, `archive`, `delete`, `label`, `mark_read` |
| SMS | `send`, `react`, `delete`, `mark_read` |
| Calendar | `create`, `update`, `delete`, `rsvp` |
| Chat | `send` |

**Action format:**
```
POST /{modality}/submit
Content-Type: application/json
X-API-Key: <api_key>

{
  "action": "<action_name>",
  ...action-specific fields...
}
```

### Forbidden Endpoints

The following are **blocked** for Purple Agents:

- Simulator-side actions (e.g., `/email/receive`, `/sms/receive`)
- Time control (e.g., `/simulator/time/advance`)
- Simulation control (e.g., `/simulator/reset`)
- Event management (e.g., `/events`)
- Undo/Redo operations
- WebSocket/Webhook endpoints
- Admin endpoints

Attempting to access forbidden endpoints returns `403 Forbidden`.

---

## Implementation Requirements

### Minimum Viable Implementation

A Purple Agent must at minimum:

1. **Start an A2A server** that accepts messages
2. **Handle `assessment_start`**: Connect to UES, retrieve user instructions from chat
3. **Execute at least one turn**: Query state, take an action, send `turn_complete`
4. **Handle `assessment_complete`**: Clean up and terminate gracefully

### Recommended Implementation

A competitive Purple Agent should also:

1. **Parse user instructions** into structured goals and constraints
2. **Track progress** toward goals across multiple turns
3. **Plan actions** strategically rather than reactively
4. **Handle new events** (emails, messages) that arrive between turns
5. **Manage time efficiently** by requesting appropriate `time_step` values
6. **Provide helpful notes** explaining reasoning in `turn_complete`
7. **Signal early completion** when all goals are achieved

### Error Handling

- **Invalid actions**: UES returns `400 Bad Request` with details — log and continue
- **Forbidden endpoints**: UES returns `403 Forbidden` — do not retry
- **Server errors**: Implement retry with backoff for `5xx` errors
- **Timeouts**: Track turn timeout and ensure `turn_complete` is sent in time

---

## Project Structure

```
agentbeats/purple/
├── README.md               # This file
├── __init__.py             # Package exports
├── schemas.py              # Message schemas (re-exports from green + purple-specific)
├── context.py              # AssessmentContext for state tracking
├── base_agent.py           # BaseAgent abstract class and SimpleAgent reference
├── executor.py             # PurpleExecutor (A2A lifecycle management)
├── server.py               # A2A server setup (create_agent_card, run_purple_agent)
├── ues_client.py           # TrackedAsyncUESClient with automatic action tracking
└── examples/
    ├── simple_agent.py     # Minimal working example
    └── llm_agent.py        # LLM-powered agent example
```

**Tests** are located in `tests/agentbeats/purple/`:
- `test_schemas.py` - Message schema tests
- `test_context.py` - AssessmentContext state tracking tests
- `test_base_agent.py` - BaseAgent and SimpleAgent tests
- `test_executor.py` - PurpleExecutor lifecycle tests
- `test_server.py` - Server utilities tests
- `test_ues_client.py` - TrackedAsyncUESClient tests
- `test_integration.py` - Integration tests with mock UES

---

## Tracked UES Client

The `TrackedAsyncUESClient` automatically records actions in the `AssessmentContext`, eliminating the need to manually call `context.record_action()`:

```python
from agentbeats.purple import (
    AssessmentContext,
    TrackedAsyncUESClient,
)

# Actions are automatically tracked
async with TrackedAsyncUESClient(context) as ues:
    await ues.email.send(...)       # context.actions_this_turn = 1
    await ues.email.archive([...])  # context.actions_this_turn = 2
    
    # Read operations are NOT tracked
    state = await ues.email.get_state()  # still 2
```

**Tracked actions** (write operations):
- Email: send, read, unread, star, unstar, archive, delete, move, add_label, remove_label
- SMS: send, read, unread, delete, react
- Chat: send, delete, clear
- Calendar: create, update, delete, rsvp
- Location: update
- Weather: update

**Not tracked** (read-only): get_state, query

---

## Running the Agent

### Local Development

```bash
# Install dependencies
uv sync

# Run the simple example
uv run python -m agentbeats.purple.examples.simple_agent --host 0.0.0.0 --port 9009

# Run the LLM-powered example (requires OPENAI_API_KEY)
uv run python -m agentbeats.purple.examples.llm_agent --host 0.0.0.0 --port 9009

# Or run your own agent script
uv run python my_agent.py --host 0.0.0.0 --port 9009
```

### Using `run_purple_agent`

The `run_purple_agent` helper handles CLI parsing and server setup:

```python
from agentbeats.purple import BaseAgent, run_purple_agent

class MyAgent(BaseAgent):
    # ... implement required methods ...
    pass

if __name__ == "__main__":
    run_purple_agent(
        agent=MyAgent(),
        name="My Agent",
        description="Description for agent card",
        version="1.0.0",
    )
```

This automatically provides `--host`, `--port`, and `--card-url` CLI arguments.

### Docker

```bash
# Build the image
docker build -t ues-purple-agent .

# Run the container
docker run -p 9009:9009 ues-purple-agent --host 0.0.0.0 --port 9009
```

### CLI Arguments

When using `run_purple_agent`, these arguments are available:

| Argument | Default | Description |
|----------|---------|-------------|
| `--host` | `0.0.0.0` | Host address to bind to |
| `--port` | `9009` | Port to listen on |
| `--card-url` | (auto) | URL to advertise in the agent card |

---

## Scoring Dimensions

The Green Agent evaluates Purple Agent performance across five dimensions:

| Dimension | Description |
|-----------|-------------|
| **Accuracy** | Correctness of outputs, information quality, factual accuracy |
| **Instruction Following** | Adherence to user instructions, constraints, and procedures |
| **Efficiency** | Minimal unnecessary actions, appropriate time management |
| **Safety** | Non-harmful behavior, avoids dangerous/inappropriate content |
| **Politeness** | Tone and manner of interactions, professional communication |

Each scenario defines specific **criteria** within these dimensions. The overall score is the sum of all criteria scores.

---

## Resources

- [AgentBeats Tutorial](https://github.com/RDI-Foundation/agentbeats-tutorial) — Learning resources and examples
- [Agent Template](https://github.com/RDI-Foundation/agent-template) — Official Purple Agent template
- [A2A Protocol Documentation](https://a2a-protocol.org/latest/) — Protocol specification
- [UES REST API Documentation](../../docs/REST_API.md) — Full API reference
- [UES Python Client](../../client/CLIENT_QUICK_REFERENCE.md) — Python client library

---

## License

This baseline agent is part of the UES project and is available under the same license.
