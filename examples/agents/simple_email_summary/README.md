# Simple Email Summary Example

This example demonstrates a simple user agent which checks the user's email every hour and provides
a summary of new emails in the last hour. In this simplest example, the agent's orchestration is
scripted: the script uses the Python client to advance the simulator time to the next hour and then
queries it for emails received over the previous hour. It provides the response JSON from this query
to the agent, which then generates a summary, which is printed out. The loop repeats until the
simulator reaches 8pm.

## Prerequisites

- **UES server** running at `http://localhost:8000` (or specify with `--ues-host`)
- **Ollama** running at `http://localhost:11434` (or specify with `--ollama-host`)
- A model pulled in Ollama (default: `gemma3:12b`)

## Running the Example

From the UES project root:

```bash
# Start the UES server (in one terminal)
uv run uvicorn main:app --reload

# Run the agent (in another terminal)
uv run python examples/agents/simple_email_summary/agent.py

# Or with custom options
uv run python examples/agents/simple_email_summary/agent.py \
    --model llama3.2:3b \
    --ollama-host http://localhost:11434 \
    --ues-host http://localhost:8000
```

## The Scenario (`scenario.ues-scenario.json`)

The scenario simulates a single workday (Friday, Jan 16, 2026) for Alex Johnson, a software
engineer at TechCorp.

**Initial state (6:00 AM):**
- Two unread spam/promotional emails from overnight

**Scheduled events throughout the day:**
| Time | Type | Description |
|------|------|-------------|
| 6:45 AM | Spam | Software deals promotional email |
| 8:15 AM | Work (1-1) | Sarah asks for Q1 planning input (needs response by EOD) |
| 8:32 AM | Calendar | Meeting invite for 2pm Project Alpha Sync |
| 8:45 AM | Work (Team) | **URGENT** - Mike reports production API gateway issue |
| 8:52 AM | Work (Team) | Jennifer replies with fix to the API issue |
| 9:10 AM | Personal | Mom asks about Sunday dinner |
| 10:30 AM | Notification | LinkedIn connection requests |
| 11:45 AM | Work (1-1) | David requests code review on auth refactor PR |
| 2:30 PM | HR | Benefits enrollment deadline reminder |
| 4:15 PM | Work (1-1) | Sarah confirms she received Q1 priorities |
| 5:45 PM | Personal | Jamie asks about dinner plans tonight |
| 7:00 PM | Spam | Travel deals promotional email |

**Email types represented:**
- Spam/promotional (sender-identifiable by domain patterns like `promo`, `deals`, `noreply`)
- Work 1-1 emails (direct requests and follow-ups)
- Work team threads (multi-person urgent discussion with replies)
- Calendar invitations
- Automated notifications (LinkedIn, HR)
- Personal emails (family and partner)

**Note:** This is a skeleton scenario with ~12 emails. For more thorough testing, expand to 36+
emails with denser distribution in busy hours (8-10am, 2-4pm).

## The Agent (`agent.py`)

The agent is a simple hourly email summary agent, contained within a single Python file. Every hour
it is presented with the JSON response from querying the UES for emails within the last hour and
replies with a summary of the hour's emails. 

### Orchestration

The agent is orchestrated purely programmatically according to the following pseudo-code:

```python
load_scenario(scenario_file)
for hour in range(6, 21):
    prev_hour = hour-1
    query_response = query_emails(since=prev_hour)
    summary = call_agent(query_response)
    print(hour, summary)
```

### Agent Model

In this example, Ollama is used to run the agent model, and the specific model used is configurable
using the `--model` argument when running `agent.py` from the command line. The argument's value
will be used as-is to select the model powering the agent. The default model is `gemma3:12b`. The
agent's system prompt is sourced from `system_prompt.txt`.

## The System Prompt (`system_prompt.txt`)

The system prompt instructs the agent to:
- Focus only on work and personal emails
- Ignore spam, promotional, and automated notification emails (identified by sender patterns)
- Synthesize information into a cohesive 2-4 sentence briefing
- Highlight urgent or time-sensitive items
- Respond with "No important emails this hour" if only spam was received