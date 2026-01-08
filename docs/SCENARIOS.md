# Scenarios

A **scenario** is a repeatable simulation setup that dictates the initial state of the UES as well
as a set of events which modify the user's environment over time. Scenarios provide the controlled,
deterministic test environment against which AI personal assistants can be evaluated.

## Core Principles

UES scenarios are **pure data**—they contain only:

1. **Initial State**: The starting configuration of all modalities (emails, calendar events,
   location, weather, etc.)
2. **Scheduled Events**: A sequence of timestamped events that will execute during the simulation
3. **Metadata**: Version info, author, description for documentation purposes

Scenarios contain **no agent logic or LLM dependencies**. This design ensures:

- **Complete Reproducibility**: The same scenario produces identical results every time
- **Framework Independence**: No vendor lock-in to specific LLM providers
- **Simplicity**: Scenarios are easy to understand, share, and version control
- **Testability**: The simulation engine can be fully tested without LLM mocking

## Scenario Formatting

Scenario formatting is described in detail in [SCENARIO_FORMAT.md](guides/SCENARIO_FORMAT.md).

## Scenario Exporting & Importing

The procedure for exporting scenarios from or importing scenarios to the simulator is detailed in
[SCENARIO_SAVE_LOAD.md](guides/SCENARIO_SAVE_LOAD.md).

## Creating Scenarios

### Manual Creation

Developers can create scenarios by:

1. **Using the Web UI**: Design initial states and events through the visual interface, then export
2. **Writing JSON directly**: Create scenario files following the format specification
3. **Using the API**: Build scenarios programmatically via the REST API or client library
4. **Capturing state**: Run a simulation, make changes via API, then export the resulting state

### Scenario Structure

A complete scenario contains:

```json
{
  "metadata": {
    "ues_version": "0.1.0",
    "scenario_version": "1",
    "created_at": "2024-03-15T14:30:00+00:00",
    "author": "Developer Name",
    "description": "A day in the life of a busy professional"
  },
  "environment": {
    "time_state": { /* simulator time configuration */ },
    "modality_states": {
      "email": { /* initial email state */ },
      "calendar": { /* initial calendar state */ },
      "location": { /* initial location */ },
      /* ... other modalities */
    }
  },
  "events": {
    "events": [
      /* scheduled events with timestamps and modality inputs */
    ]
  }
}
```

### Example: Simple Workday Scenario

```json
{
  "metadata": {
    "description": "Morning email and meeting scenario"
  },
  "environment": {
    "time_state": {
      "current_time": "2024-03-15T08:00:00+00:00"
    },
    "modality_states": {
      "location": {
        "current_latitude": 37.7749,
        "current_longitude": -122.4194,
        "current_named_location": "Home"
      },
      "email": {
        "emails": {},
        "user_email_address": "user@example.com"
      }
    }
  },
  "events": {
    "events": [
      {
        "scheduled_time": "2024-03-15T08:30:00+00:00",
        "modality": "email",
        "data": {
          "operation": "receive",
          "from_address": "boss@company.com",
          "to_addresses": ["user@example.com"],
          "subject": "Team meeting moved to 10am",
          "body_text": "Hi, the 9am meeting is now at 10am. See you then."
        }
      },
      {
        "scheduled_time": "2024-03-15T09:00:00+00:00",
        "modality": "location",
        "data": {
          "latitude": 37.7849,
          "longitude": -122.4094,
          "named_location": "Office"
        }
      }
    ]
  }
}
```

## External Agent Integration

While UES scenarios are pure data, the simulation system is designed to be **fully interactable by
external agents** through its REST API. This enables powerful testing patterns:

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    UES Core (Pure Simulation)                   │
│  • Deterministic scenario execution                             │
│  • State management                                             │
│  • Event scheduling and execution                               │
│  • REST API + WebSocket notifications                           │
└───────────────────────────────┬─────────────────────────────────┘
                                │
         ┌──────────────────────┼──────────────────────┐
         │                      │                      │
   Simulator-Side         User-Side Agent         Developer
   Agent (optional)       (being tested)          (Web UI)
         │                      │                      │
         └──────────────────────┴──────────────────────┘
                    All use the same REST API
```

### Simulator-Side Agents

Developers can build **external simulator-side agents** that:

- **React to events**: Monitor state changes via API polling or WebSocket, generate response events
  (e.g., auto-reply to emails, respond to meeting invites)
- **Generate realistic content**: Use LLMs to create email bodies, text messages, calendar
  descriptions that feel authentic
- **Simulate characters**: Maintain character personalities and respond in-character to user actions
- **Implement triggers**: Watch for conditions and schedule events when they're met

These agents are **completely external to UES**—they connect via the same API as the agent being
tested. This provides:

- **Framework freedom**: Use any LLM provider, any agent framework, any programming language
- **Cost control**: Manage your own API keys and model selection
- **Custom logic**: Implement whatever reactive/trigger behavior your tests need
- **No UES modifications**: Build sophisticated test environments without changing UES core

### Example: External Reactive Agent

```python
# Example: Simple email auto-reply agent (external to UES)
import time
from ues_client import UESClient

client = UESClient("http://localhost:8000")
seen_emails = set()

while True:
    # Poll for new emails
    state = client.email.get_state()
    for email_id, email in state.emails.items():
        if email_id not in seen_emails and email.folder == "inbox":
            seen_emails.add(email_id)
            
            # Generate reply using your preferred LLM
            reply_body = generate_reply_with_llm(email)
            
            # Schedule the reply to arrive after a delay
            client.events.schedule(
                modality="email",
                scheduled_time=current_time + timedelta(minutes=15),
                data={
                    "operation": "receive",
                    "from_address": email.from_address,
                    "to_addresses": [state.user_email_address],
                    "subject": f"Re: {email.subject}",
                    "body_text": reply_body,
                    "in_reply_to": email_id
                }
            )
    
    time.sleep(1)  # Poll interval
```

### WebSocket Support (Planned)

For more efficient reactive agents, UES will provide WebSocket subscriptions:

- Subscribe to specific event types or modality changes
- Receive real-time notifications instead of polling
- Reduce latency for reactive event generation

## Scenario Design Patterns

### Pattern 1: Static Regression Test

A fully pre-defined scenario for consistent regression testing:

- All events are pre-written with exact content
- No external agents needed
- 100% reproducible

### Pattern 2: Dynamic Content Generation

Use an external tool to generate scenario content before loading:

1. Write a scenario template with placeholders
2. Run an LLM-based tool to fill in realistic content
3. Export as a static scenario
4. Load and run deterministically

### Pattern 3: Interactive Testing

Run UES with external agents for dynamic testing:

1. Load a base scenario (initial state + some events)
2. Start external simulator-side agents (character responders, trigger monitors)
3. Connect the AI assistant being tested
4. Let all agents interact through the API
5. Optionally export final state as a new scenario for replay

### Pattern 4: Scenario Capture

Generate scenarios from interactive sessions:

1. Run an interactive simulation with external agents
2. All events (from any source) are recorded in the event queue
3. Export the complete scenario
4. Replay deterministically without the external agents

## Best Practices

1. **Start simple**: Begin with static scenarios, add complexity as needed
2. **Version control scenarios**: Track scenario JSON files in git
3. **Document thoroughly**: Use metadata fields to describe what the scenario tests
4. **Isolate variables**: Test one thing at a time with focused scenarios
5. **Build a library**: Create reusable scenario templates for common patterns
6. **Capture good runs**: When interactive testing produces good results, export and save

## Migration from Agentic Scenarios

If you have designs that assumed built-in agentic event generation:

| Old Concept | New Approach |
|-------------|--------------|
| `agentic: true` flag on events | Pre-generate content externally, save as static event |
| Built-in character agents | External agent that manages character personalities |
| Reactive event listeners | External agent polling/WebSocket subscription |
| Trigger DSL evaluation | External agent with custom condition checking |
| Baking mode | Default behavior—all scenarios are "baked" |

The key insight: **anything that required LLM calls now happens outside UES**, either before
scenario creation (content generation tools) or during simulation (external agents).