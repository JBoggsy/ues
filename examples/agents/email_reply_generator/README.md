# Email Reply Generator Agent

This example demonstrates a **simulator-side agent** that monitors for emails sent by the user
and automatically generates realistic replies from the recipient characters using an LLM.

## Overview

Unlike the `simple_email_summary` example (which is a user-side agent that summarizes emails), this
agent simulates the **other people** in the user's world. When the user sends an email to a known
character, the agent:

1. Detects the `email.sent` event via WebSocket
2. Retrieves the full email content and conversation thread history
3. Generates an in-character reply using an LLM
4. Schedules the reply to arrive after a realistic delay

This pattern enables dynamic, interactive testing scenarios where AI assistants can be tested in
realistic conversational contexts.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    UES (Simulation Engine)                      │
│                                                                 │
│   email.sent event ──────► WebSocket ──────► Reply Generator   │
│                                                   Agent         │
│   ◄───────────────── email.receive event ◄─────────────────────┤
│    (scheduled with delay)                                       │
└─────────────────────────────────────────────────────────────────┘
```

**Key Components:**

- **WebSocket Subscription**: Real-time monitoring of `email.sent` events
- **Character Definitions**: JSON file defining personalities and response behaviors
- **Thread Tracking**: Maintains conversation context for coherent multi-turn replies
- **Variable Delays**: Realistic response timing based on character profiles
- **LLM Integration**: Uses Ollama for character-consistent reply generation

## Prerequisites

- **UES server** running at `http://localhost:8000` (or specify with `--ues-host`)
- **Ollama** running at `http://localhost:11434` (or specify with `--ollama-host`)
- A model pulled in Ollama (default: `gemma3:12b`)

## Running the Example

From the UES project root:

```bash
# Terminal 1: Start the UES server
uv run uvicorn main:app --reload

# Terminal 2: Run the agent
uv run python examples/agents/email_reply_generator/agent.py

# With custom options
uv run python examples/agents/email_reply_generator/agent.py \
    --model llama3.2:3b \
    --ollama-host http://localhost:11434 \
    --ues-host http://localhost:8000
```

## Testing the Agent

Once the agent is running, you can trigger replies by sending emails:

### Option 1: Using the UES API (curl)

```bash
# Send an email to Sarah Chen (your manager)
curl -X POST http://localhost:8000/email/send \
  -H "Content-Type: application/json" \
  -d '{
    "from_address": "alex.johnson@techcorp.com",
    "to_addresses": ["sarah.chen@techcorp.com"],
    "subject": "Re: Q1 Planning - Need Your Input",
    "body_text": "Hi Sarah,\n\nHere are my thoughts:\n1. Auth refactor: ~3 weeks with testing\n2. Main risk is the OAuth migration for existing users\n3. Happy to mentor David!\n\nLet me know if you need more detail.\n\nAlex"
  }'

# Advance time to receive the scheduled reply
curl -X POST http://localhost:8000/simulator/time/advance \
  -H "Content-Type: application/json" \
  -d '{"seconds": 1800}'
```

### Option 2: Using the Python Client

```python
from client import UESClient
from datetime import timedelta

with UESClient() as client:
    # Send an email
    client.email.send(
        from_address="alex.johnson@techcorp.com",
        to_addresses=["marcus.williams@techcorp.com"],
        subject="Re: Quick question about the rate limiter",
        body_text="Hey Marcus!\n\nGood catch on the Redis question. Yes, we're using Redis for distributed state - planning to use a sliding window algorithm.\n\nLunch sounds great! Thursday work for you?\n\nAlex"
    )
    
    # Advance time to trigger the reply
    client.time.advance(seconds=1200)  # 20 minutes
    
    # Check for new emails
    emails = client.email.query(folder="inbox", is_read=False)
    for email in emails.emails:
        print(f"From: {email.from_address}")
        print(f"Subject: {email.subject}")
        print(f"Body: {email.body_text[:200]}...")
```

### Option 3: Using the Web UI

1. Open `http://localhost:5173` in your browser
2. Advance time to receive some initial emails
3. Use the email interface to compose and send replies
4. Watch the agent console for reply generation
5. Advance time again to receive the generated replies

## The Characters (`characters.json`)

The scenario includes 8 distinct characters with unique personalities:

### Work Characters

| Character | Role | Personality |
|-----------|------|-------------|
| **Sarah Chen** | Engineering Manager | Professional, supportive, efficient. Values clear communication. |
| **Marcus Williams** | Senior Engineer | Friendly, collaborative, detail-oriented. Enjoys technical discussions. |
| **Emily Rodriguez** | DevOps Engineer | Calm under pressure, technically precise. Concise and action-oriented. |
| **David Kim** | Junior Engineer | Eager to learn, appreciative. Asks good questions. |
| **Priya Patel** | Product Manager | Organized, stakeholder-focused. Balances business and technical needs. |

### Personal Characters

| Character | Role | Personality |
|-----------|------|-------------|
| **Linda Johnson** | Mother | Warm, caring, sometimes worries. Uses endearments. |
| **Mike Chen** | College Friend | Fun-loving, enthusiastic. Uses casual language and emoji. |
| **Sam Taylor** | Partner | Supportive, thoughtful, playful. Shows interest in your day. |

### Responsiveness Settings

Each character has configurable response timing:

```json
{
  "responsiveness": {
    "min_delay_minutes": 5,
    "max_delay_minutes": 30,
    "work_hours_only": true
  },
  "work_hours": {
    "start": "08:00",
    "end": "18:00",
    "timezone": "America/Los_Angeles"
  }
}
```

## The Scenario (`scenario.ues-scenario.json`)

The scenario simulates a Monday workday for Alex Johnson with 12 incoming emails:

| Time | From | Subject | Type |
|------|------|---------|------|
| 8:05 AM | Sarah Chen | Q1 Planning - Need Your Input | Work (requires response) |
| 8:30 AM | Marcus Williams | Quick question about the rate limiter | Work (technical question) |
| 9:00 AM | David Kim | Help with JWT refresh tokens? | Work (mentoring opportunity) |
| 9:45 AM | Emily Rodriguez | Deployment approval needed | Work (action required) |
| 10:30 AM | Priya Patel | Dashboard API - Timeline Check | Work (estimate request) |
| 11:00 AM | Linda Johnson | Weekend visit? | Personal (family) |
| 12:15 PM | Mike Chen | Dude - Austin reunion happening! | Personal (friends) |
| 2:00 PM | Marcus Williams | Re: Quick question... (follow-up) | Work (thread continuation) |
| 3:30 PM | Sam Taylor | Dinner plans | Personal (partner) |
| 4:15 PM | Sarah Chen | Re: Q1 Planning - Quick follow-up | Work (urgent follow-up) |
| 5:00 PM | Emily Rodriguez | Re: Deployment... - Update | Work (status update) |
| 5:45 PM | David Kim | Re: Help with JWT... | Work (follow-up) |

## The Agent (`agent.py`)

### How It Works

1. **Startup**: Loads scenario, characters, and connects to WebSocket
2. **Event Monitoring**: Subscribes to `email.sent` events
3. **Character Matching**: Checks if recipient is a known character
4. **Context Gathering**: Retrieves thread history for conversation context
5. **Reply Generation**: Calls Ollama with character profile and thread context
6. **Scheduling**: Creates a future `email.receive` event with realistic delay

### Thread Awareness

The agent maintains conversation context by:
- Querying the full email thread when a reply is detected
- Including all previous emails in the LLM prompt
- Setting proper `thread_id`, `in_reply_to`, and `references` fields

### Example Console Output

```
============================================================
Email Reply Generator Agent
============================================================
Model: gemma3:12b
Ollama: http://localhost:11434
UES: http://localhost:8000
Characters: 8
============================================================

Loading scenario...
Scenario loaded successfully.
Simulation started.

Simulator time: 2026-01-20 08:00 PST

Connecting to WebSocket...
Waiting for user to send emails...
✓ Subscribed to email.sent events

📧 Email sent detected!
   To: sarah.chen@techcorp.com
   Subject: Re: Q1 Planning - Need Your Input

   🎭 Generating reply as Sarah Chen...
   📜 Thread has 1 previous email(s)
   ✓ Reply scheduled for 08:47:23
   (in 12.4 minutes)

   --- Preview ---
   Hi Alex,

   Thank you for the quick turnaround on this - really helpful!

   Your timeline estimate for the auth refactor looks reasonable...
   ----------------
```

## Extending the Example

### Adding New Characters

Edit `characters.json` to add new character definitions:

```json
{
  "new.character@example.com": {
    "name": "New Character",
    "role": "Their Role",
    "relationship": "How they relate to user",
    "personality": "Their personality traits...",
    "communication_style": "How they write emails...",
    "responsiveness": {
      "min_delay_minutes": 5,
      "max_delay_minutes": 30,
      "work_hours_only": true
    }
  }
}
```

### Customizing the System Prompt

Edit `system_prompt.txt` to modify how the LLM generates replies. You might:
- Add specific instructions for handling certain topics
- Adjust the output format
- Include domain-specific context

### Using Different LLM Models

The agent works with any Ollama-compatible model:

```bash
# Smaller, faster model
python agent.py --model llama3.2:3b

# Larger, more capable model
python agent.py --model llama3.1:70b
```

## Limitations

- **No real work hour enforcement**: The agent schedules replies immediately with delays, but doesn't actually wait for character work hours
- **Single recipient focus**: When emailing multiple recipients, each character responds independently
- **No conversation memory across sessions**: Thread context is retrieved fresh each time
- **Synchronous LLM calls**: Generation happens sequentially, which could slow down with many simultaneous emails

## See Also

- [Simple Email Summary Agent](../simple_email_summary/) - User-side agent example
- [Agent Integration Guide](../../../docs/AGENT_INTEGRATION.md) - Comprehensive agent patterns
- [WebSocket Documentation](../../../docs/WEBSOCKET.md) - Real-time event subscription
- [Scenarios Guide](../../../docs/SCENARIOS.md) - Creating and loading scenarios
