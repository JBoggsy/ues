# SMS Group Chat Simulator Agent

This example demonstrates a **simulator-side agent** that simulates multiple distinct personalities
in a group SMS chat, creating realistic group dynamics with agreements, disagreements, and
natural conversation flow.

## Overview

Unlike single-character simulation, this agent manages **multiple personalities simultaneously**,
each with their own response timing, communication style, and opinions. The scenario involves
planning a weekend camping trip with friends, showcasing how different personalities interact
and influence each other in a group setting.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    UES (Simulation Engine)                      │
│                                                                 │
│   sms.sent event ──────► WebSocket ──────► Group Chat Agent    │
│        │                                         │              │
│        │                                         ▼              │
│        │                                  Character Router      │
│        │                                         │              │
│        │                         ┌───────────────┼───────────┐  │
│        │                         ▼               ▼           ▼  │
│        │                      Morgan          Riley       Jordan │
│        │                      (eager)       (skeptic)    (chill) │
│        │                         │               │           │  │
│        │                         ▼               ▼           ▼  │
│        │                    LLM Generation (per character)      │
│        │                         │               │           │  │
│   ◄────┴─────────────────────────┴───────────────┴───────────┘  │
│   sms.receive events (staggered by character response times)    │
└─────────────────────────────────────────────────────────────────┘
```

**Key Components:**

- **WebSocket Subscription**: Real-time monitoring of messages to the group thread
- **Character Router**: Determines which characters should respond to each message
- **Personality Engine**: Maintains distinct voice, timing, and opinions for each character
- **Inter-Character Reactions**: Characters respond to each other, not just the user
- **Conversation Memory**: Tracks what's been decided, who agreed, outstanding questions

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
uv run python examples/agents/sms_group_chat/agent.py

# With custom options
uv run python examples/agents/sms_group_chat/agent.py \
    --model llama3.2:3b \
    --ollama-host http://localhost:11434 \
    --ues-host http://localhost:8000
```

## The Scenario (`scenario.ues-scenario.json`)

The scenario simulates a Thursday-Saturday period where the user (Casey) is trying to organize
a camping trip for the upcoming weekend with their friend group.

### Initial State

- **Simulator Time**: Thursday, January 22, 2026, 10:00 AM
- **Existing Group Thread**: "Weekend Warriors 🏕️" with 5 participants
- **Thread History**: A few messages from earlier in the week establishing the camping idea
- **Decisions Needed**: Destination, departure time, gear assignments, food planning

### The Planning Challenge

The group needs to decide:
1. **Where**: Three options discussed (Pine Ridge, Lake Haven, Mountain View)
2. **When**: Friday evening vs Saturday morning departure
3. **Who brings what**: Tents, cooking gear, coolers, firewood
4. **Food**: Meal planning and grocery shopping coordination
5. **Transportation**: Who drives, carpooling arrangements

## The Characters (`characters.json`)

### Casey (The User)

The trip organizer trying to nail down logistics. Casey is patient but wants to make decisions
and move forward with planning.

### Morgan - The Enthusiast 🎉

| Attribute | Description |
|-----------|-------------|
| **Personality** | Boundlessly enthusiastic, always positive, sometimes overwhelming |
| **Response Time** | 10-30 seconds (first to respond, always) |
| **Communication Style** | Heavy emoji use (🏕️⛺🔥), exclamation points, ALL CAPS for excitement |
| **Decision Pattern** | Says yes to everything, volunteers for tasks eagerly |
| **Quirks** | Sends multiple messages in rapid succession, reacts to everything |

**Example messages:**
- "OMG YES!!! 🏕️🏕️🏕️"
- "I can bring the big tent AND the backup tent just in case!!"
- "This is gonna be AMAZING you guys"

### Riley - The Skeptic 🤔

| Attribute | Description |
|-----------|-------------|
| **Personality** | Cautious, risk-aware, needs convincing but ultimately supportive |
| **Response Time** | 2-5 minutes (thinks before responding) |
| **Communication Style** | Questions, concerns, "what if" scenarios, proper punctuation |
| **Decision Pattern** | Raises objections first, then comes around after discussion |
| **Quirks** | Checks weather forecasts, reads reviews, mentions past mishaps |

**Example messages:**
- "I just checked the forecast and there's a 30% chance of rain on Saturday..."
- "Remember last time when we forgot the can opener? I'm making a checklist."
- "Has anyone actually been to Pine Ridge? The reviews mention bears."

### Jordan - The Chill One 😎

| Attribute | Description |
|-----------|-------------|
| **Personality** | Extremely laid back, goes with the flow, low-maintenance |
| **Response Time** | 1-4 hours (often misses conversations entirely) |
| **Communication Style** | Minimal words, lowercase, rarely uses punctuation or emoji |
| **Decision Pattern** | "whatever works", "im good either way", defers to group |
| **Quirks** | Sometimes responds to messages from hours ago, asks questions already answered |

**Example messages:**
- "sounds good"
- "im down for whatever"
- "wait what time are we leaving" (3 hours after it was decided)

### Alex - The Maybe 📅

| Attribute | Description |
|-----------|-------------|
| **Personality** | Wants to come but has complicated scheduling, partner-dependent |
| **Response Time** | 30-90 minutes (has to check with partner first) |
| **Communication Style** | Apologetic, lots of "let me check", conditional commitments |
| **Decision Pattern** | Tentative yes, then confirms/backs out after checking |
| **Quirks** | Partner (Sam) is mentioned frequently, schedule is always "complicated" |

**Example messages:**
- "Let me check with Sam and get back to you"
- "So Sam has a thing Saturday morning but we could meet you there by noon?"
- "Ugh Sam's mom just called, might need to adjust our timing 😬"

### Taylor - The Joker 😂

| Attribute | Description |
|-----------|-------------|
| **Personality** | Class clown, deflects with humor, but genuinely helpful when needed |
| **Response Time** | 1-10 minutes (unpredictable) |
| **Communication Style** | Memes, jokes, GIF descriptions, playful teasing |
| **Decision Pattern** | Jokes first, then provides actual input when prompted |
| **Quirks** | Nicknames for everyone, references inside jokes, occasionally derails conversations |

**Example messages:**
- "I volunteer as tribute to bring the marshmallows 🔥"
- "Riley's bear paranoia activated 😂"
- "[GIF: man running from tent]"
- "Ok but seriously I can grab firewood on the way"

## The Agent (`agent.py`)

### Multi-Character Response Logic

When the user sends a message, the agent determines responses:

```python
async def on_user_message(message):
    # Determine which characters should respond
    responders = determine_responders(message, conversation_state)
    
    # For each responder, generate and schedule a response
    for character in responders:
        # Calculate response delay based on character
        delay = calculate_delay(character)
        
        # Generate response considering:
        # - Character personality
        # - What other characters have said
        # - Current conversation state
        # - What decisions have been made
        response = await generate_response(character, message, context)
        
        # Schedule the SMS to arrive after delay
        schedule_sms(character, response, delay)
```

### Inter-Character Dynamics

The agent tracks how characters interact with each other:

| Interaction | Behavior |
|-------------|----------|
| Morgan → Riley | Morgan reassures Riley's concerns enthusiastically |
| Riley → Morgan | Riley tempers Morgan's enthusiasm with practical concerns |
| Taylor → Riley | Taylor teases Riley about being a worrier |
| Jordan → Anyone | Jordan occasionally surfaces to agree with whatever was decided |
| Alex → Group | Alex apologizes for schedule complications |

### Conversation State Tracking

The agent maintains:

```python
conversation_state = {
    "decisions_made": {
        "destination": None,  # or "Pine Ridge"
        "departure_time": None,
        "transportation": {}
    },
    "pending_questions": [
        "Where should we go?",
        "What time do we leave?"
    ],
    "character_opinions": {
        "Morgan": {"destination": "anywhere!", "departure": "Friday night!!"},
        "Riley": {"destination": "Lake Haven (better reviews)", "departure": "Saturday (weather)"},
        # ...
    },
    "alex_status": "checking with Sam"
}
```

## The System Prompt (`system_prompt.txt`)

The system prompt is a template that gets populated per-character:

```
You are {character_name}, participating in a group SMS chat about planning a camping trip.

YOUR PERSONALITY:
{character_personality}

YOUR COMMUNICATION STYLE:
{character_style}

CURRENT CONVERSATION STATE:
{conversation_summary}

OTHER CHARACTERS' RECENT MESSAGES:
{recent_messages}

DECISIONS ALREADY MADE:
{decisions_made}

YOUR TASK:
Respond as {character_name} would to the latest message. Stay in character.
Consider what others have said and maintain your established opinions unless
genuinely convinced otherwise.

Remember:
- Keep responses SMS-appropriate (short, casual)
- Match {character_name}'s typing style exactly
- React to other characters' messages when relevant
- Don't resolve all conflict immediately - some disagreement is natural
```

## Expected Conversation Flow

A typical conversation might unfold like:

```
Casey: "Ok team, we need to decide: Pine Ridge, Lake Haven, or Mountain View?"

[15 seconds later]
Morgan: "PINE RIDGE!!! 🌲🏕️ I've been dying to go there!!"

[2 minutes later]
Riley: "I looked up Pine Ridge and some reviews mention the access road 
       is rough. Lake Haven has better facilities and cell service."

[3 minutes later]
Taylor: "Riley already pulled up the Yelp reviews 😂 classic"

[35 minutes later]
Alex: "Let me ask Sam if they have a preference - either works for us 
       schedule-wise I think"

[2.5 hours later]
Jordan: "im good with any of those"

[Next message from Casey triggers new round of responses...]
```

## Key Patterns Demonstrated

1. **Multi-Character Simulation**: Managing distinct personalities simultaneously
2. **Realistic Timing**: Each character has unique response latency patterns
3. **Group Dynamics**: Characters react to each other, not just the user
4. **State Tracking**: Maintaining decisions and opinions across the conversation
5. **Natural Disagreement**: Characters have different preferences that play out naturally
6. **SMS Conventions**: Short messages, casual language, appropriate emoji use

## Extending This Example

Ideas for extending this example:

- **Reactions**: Add SMS reaction support (👍, ❤️, 😂) to messages
- **Side Conversations**: Characters occasionally DM each other or the user
- **Dynamic Opinions**: Characters can be convinced to change their mind
- **Schedule Integration**: Connect to calendar to show Alex's actual conflicts
- **Media Sharing**: Characters share photos or links (simulated)
- **Read Receipts**: Track who has "seen" messages

## File Structure

```
sms_group_chat/
├── agent.py                    # Main agent code
├── README.md                   # This documentation
├── system_prompt.txt           # LLM prompt template (per-character)
├── characters.json             # Character definitions
└── scenario.ues-scenario.json  # Initial thread state and setup
```
