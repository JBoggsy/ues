# Example Agents

This directory contains example agents demonstrating different patterns for integrating with UES.

## Overview

UES supports two types of agents:

1. **User-Side Agents**: AI assistants being tested that query the simulated environment and take actions
2. **Simulator-Side Agents**: External agents that generate realistic content and react to simulation events

Both types interact with UES through the same REST API, but serve different purposes in testing scenarios.

## Examples

### `simple_email_summary/` - User-Side Agent

A user-side agent that summarizes emails received each hour.

**Demonstrates:**
- Programmatic orchestration (advancing time, querying state)
- Hourly email summarization using Ollama
- Simple polling-based interaction pattern

**Use case:** Testing how an AI assistant might process and summarize the user's inbox.

[📖 Read the full README](simple_email_summary/README.md)

---

### `email_reply_generator/` - Simulator-Side Agent

A simulator-side agent that monitors for sent emails and generates realistic replies from character recipients.

**Demonstrates:**
- WebSocket-based event monitoring
- Character personality simulation using LLMs
- Thread-aware conversation tracking
- Variable response delays for realism

**Use case:** Creating dynamic, interactive test scenarios where "other people" respond realistically to the user's emails.

[📖 Read the full README](email_reply_generator/README.md)

---

### `calendar_conflict_resolver/` - User-Side Agent

A user-side agent that analyzes calendar conflicts and recommends resolutions for a busy project manager.

**Demonstrates:**
- Calendar API integration for conflict detection
- Multi-factor priority analysis (attendees, meeting type, history)
- LLM-powered recommendation generation
- Structured daily briefing output

**Use case:** Testing how an AI assistant might help users manage scheduling conflicts intelligently.

[📖 Read the full README](calendar_conflict_resolver/README.md)

---

### `sms_group_chat/` - Simulator-Side Agent

A simulator-side agent that simulates multiple distinct personalities in a group SMS chat planning a camping trip.

**Demonstrates:**
- Multi-character simulation with unique personalities
- Realistic per-character response timing
- Inter-character reactions and group dynamics
- Conversation state tracking (decisions, opinions)

**Use case:** Creating realistic group messaging scenarios where "friends" interact naturally with each other and the user.

[📖 Read the full README](sms_group_chat/README.md)

---

### `party_planner/` - Dual Agent (User-Side + Simulator-Side)

A comprehensive integration test with both agent types: an AI assistant (user-side) coordinates a party while guests and vendors (simulator-side) respond realistically.

**Demonstrates:**
- Dual-agent architecture with both agent types interacting
- Multi-modal coordination (email, SMS, calendar)
- RSVP tracking and vendor negotiation flows
- Objective test scoring of AI assistant capabilities

**Use case:** End-to-end testing of an AI assistant's ability to coordinate complex multi-party tasks.

[📖 Read the full README](party_planner/README.md)

---

## Running the Examples

All examples require:
- UES server running: `uv run uvicorn main:app --reload`
- Ollama running with a model available (default: `gemma3:12b`)

```bash
# Run from the UES project root
cd /path/to/ues

# Simple Email Summary (user-side)
uv run python examples/agents/simple_email_summary/agent.py

# Email Reply Generator (simulator-side)
uv run python examples/agents/email_reply_generator/agent.py
```

## Creating Your Own Agents

See the [Agent Integration Guide](../../docs/AGENT_INTEGRATION.md) for comprehensive documentation on:
- Python client usage (sync and async)
- Real-time notifications (WebSocket and Webhooks)
- Common agent patterns
- Best practices

## File Structure

Each example agent follows this structure:

```
example_agent/
├── agent.py                    # Main agent code
├── README.md                   # Documentation
├── system_prompt.txt           # LLM prompt template
├── scenario.ues-scenario.json  # Test scenario
└── characters.json             # (optional) Character definitions
```
