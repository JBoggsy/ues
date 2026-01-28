# Event Generation Agent Pattern

This document describes a **design pattern** for building external agents that generate realistic
event content for UES simulations. This is not a built-in UES feature—it's a reference architecture
for developers building their own simulator-side agents.

## Overview

An Event Generation Agent is an external service that:

1. Monitors the UES simulation state via the REST API
2. Generates realistic event content using LLMs
3. Schedules new events back into the simulation

This pattern is useful for:

- Creating realistic email, SMS, and chat content
- Generating character-driven responses to user actions
- Filling in event details from high-level descriptions
- Building interactive test environments

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Event Generation Agent                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Agent Orchestrator                                      │   │
│  │  • Monitors UES state (polling or WebSocket)            │   │
│  │  • Decides when to generate events                       │   │
│  │  • Coordinates LLM calls                                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│       ┌──────────────────────┼──────────────────────┐          │
│       │                      │                      │          │
│  ┌────┴────┐           ┌─────┴─────┐          ┌─────┴────┐    │
│  │ Context │           │   LLM     │          │  Event   │    │
│  │ Gatherer│           │ Generator │          │ Scheduler│    │
│  └─────────┘           └───────────┘          └──────────┘    │
│       │                      │                      │          │
└───────┼──────────────────────┼──────────────────────┼──────────┘
        │                      │                      │
        │              (Your LLM Provider)            │
        │                                             │
        └─────────────── UES REST API ────────────────┘
```

## Implementation Guide

### 1. Context Gathering

Before generating content, gather relevant context from UES:

```python
from ues_client import UESClient

def gather_context(client: UESClient, modality: str) -> dict:
    """Gather context from UES for content generation."""
    context = {
        "current_time": client.time.get_state().current_time,
        "modality_state": None,
        "recent_events": [],
    }
    
    # Get modality-specific state
    if modality == "email":
        state = client.email.get_state()
        context["modality_state"] = {
            "user_email": state.user_email_address,
            "recent_emails": list(state.emails.values())[-10:],
            "threads": state.threads,
        }
    elif modality == "sms":
        state = client.sms.get_state()
        context["modality_state"] = {
            "user_phone": state.user_phone_number,
            "conversations": state.conversations,
            "recent_messages": list(state.messages.values())[-20:],
        }
    # ... other modalities
    
    return context
```

### 2. LLM Content Generation

Use gathered context to generate realistic content:

```python
def generate_email_content(
    context: dict,
    description: str,
    character: dict,  # Character personality info
) -> dict:
    """Generate email content using an LLM."""
    
    prompt = f"""You are generating email content for a simulation.

Character: {character['name']}
Personality: {character['personality']}
Relationship to user: {character['relationship']}

Current simulator time: {context['current_time']}
User's email: {context['modality_state']['user_email']}

Recent email context:
{format_recent_emails(context['modality_state']['recent_emails'])}

Event description: {description}

Generate a realistic email. Respond with JSON:
{{
    "subject": "...",
    "body_text": "...",
    "priority": "normal|high|low"
}}
"""
    
    response = call_your_llm(prompt)  # Use your preferred LLM
    return parse_json_response(response)
```

### 3. Event Scheduling

Schedule generated events back to UES:

```python
from datetime import timedelta

def schedule_generated_event(
    client: UESClient,
    modality: str,
    content: dict,
    delay_minutes: int = 5,
) -> str:
    """Schedule a generated event in UES."""
    
    current_time = client.time.get_state().current_time
    scheduled_time = current_time + timedelta(minutes=delay_minutes)
    
    if modality == "email":
        event_data = {
            "operation": "receive",
            "from_address": content["from_address"],
            "to_addresses": [content["to_address"]],
            "subject": content["subject"],
            "body_text": content["body_text"],
            "priority": content.get("priority", "normal"),
        }
    # ... handle other modalities
    
    result = client.events.schedule(
        modality=modality,
        scheduled_time=scheduled_time,
        data=event_data,
    )
    
    return result.event_id
```

## Character Management

For consistent character-driven content, maintain character definitions externally:

```python
characters = {
    "boss": {
        "name": "Sarah Chen",
        "email": "sarah.chen@company.com",
        "phone": "+1-555-0101",
        "personality": "Professional, direct, values efficiency. Sends concise emails.",
        "relationship": "User's manager",
    },
    "friend": {
        "name": "Mike Johnson",
        "email": "mike.j@email.com",
        "phone": "+1-555-0202",
        "personality": "Casual, uses emojis, tends to ramble. Close friend from college.",
        "relationship": "Close friend",
    },
}
```

## Reactive Event Pattern

Monitor UES for changes and generate responses:

```python
import time

class ReactiveAgent:
    def __init__(self, client: UESClient, characters: dict):
        self.client = client
        self.characters = characters
        self.seen_emails = set()
        self.seen_sms = set()
    
    def run(self, poll_interval: float = 1.0):
        """Main loop: monitor and react to changes."""
        while True:
            self.check_for_new_emails()
            self.check_for_new_sms()
            time.sleep(poll_interval)
    
    def check_for_new_emails(self):
        """Check for emails that need responses."""
        state = self.client.email.get_state()
        
        for email_id, email in state.emails.items():
            if email_id in self.seen_emails:
                continue
            self.seen_emails.add(email_id)
            
            # Check if this email is TO a character (user sent it)
            if email.folder == "sent":
                recipient = email.to_addresses[0]
                character = self.find_character_by_email(recipient)
                
                if character and character.get("reactive", True):
                    self.generate_reply(email, character)
    
    def generate_reply(self, original_email, character):
        """Generate and schedule a reply from a character."""
        context = gather_context(self.client, "email")
        
        content = generate_email_reply(
            context=context,
            original_email=original_email,
            character=character,
        )
        
        # Random delay for realism (5-30 minutes)
        delay = random.randint(5, 30)
        
        schedule_generated_event(
            client=self.client,
            modality="email",
            content={
                "from_address": character["email"],
                "to_address": original_email.from_address,
                "subject": f"Re: {original_email.subject}",
                "body_text": content["body_text"],
                "in_reply_to": original_email.message_id,
            },
            delay_minutes=delay,
        )
```

## Trigger Pattern

Watch for conditions and generate events when met:

```python
class TriggerAgent:
    def __init__(self, client: UESClient):
        self.client = client
        self.triggers = []
    
    def add_trigger(self, condition_fn, effect_fn):
        """Add a trigger: when condition is true, run effect."""
        self.triggers.append((condition_fn, effect_fn))
    
    def run(self, poll_interval: float = 5.0):
        """Check triggers periodically."""
        while True:
            state = self.get_full_state()
            
            for condition_fn, effect_fn in self.triggers:
                if condition_fn(state):
                    effect_fn(self.client, state)
            
            time.sleep(poll_interval)

# Example triggers
def missed_meeting_condition(state):
    """Check if user missed a meeting."""
    calendar = state["calendar"]
    location = state["location"]
    current_time = state["time"]["current_time"]
    
    for event in calendar.events.values():
        if event.start <= current_time <= event.end:
            if event.location and location.current_named_location != event.location:
                return True
    return False

def send_warning_email(client, state):
    """Effect: send a warning email about missed meeting."""
    client.email.receive(
        from_address="hr@company.com",
        to_addresses=[state["email"].user_email_address],
        subject="Meeting Attendance Reminder",
        body_text="Our records show you may have missed a scheduled meeting...",
    )
```

## Best Practices

1. **Rate Limiting**: Don't flood UES with generated events
2. **Caching**: Cache LLM responses for identical inputs to save costs
3. **Error Handling**: Handle API failures gracefully, retry with backoff
4. **Logging**: Log all generated content for debugging and replay
5. **Seeding**: Use fixed random seeds for reproducible behavior
6. **Character Consistency**: Maintain character state across interactions
7. **Context Windows**: Be mindful of LLM context limits when gathering context

## Exporting Generated Scenarios

After running with a generation agent, export the result for replay:

```python
# After interactive session with agents
scenario = client.scenario.export(
    author="Generated by EventGenerationAgent",
    description="Scenario generated from interactive session"
)

with open("generated_scenario.ues-scenario.json", "w") as f:
    f.write(scenario.to_json())

# Now you have a deterministic scenario that can be replayed without the agent
```

## See Also

- [SCENARIOS.md](../../guides/SCENARIOS.md) - Scenario concepts and external agent integration
- [API_CLIENT.md](../../client/API_CLIENT.md) - UES Python client documentation
- [REST_API.md](../../api/REST_API.md) - Complete API reference
