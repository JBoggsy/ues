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
- Empty inbox (all emails arrive as scheduled events throughout the day)

**Scheduled events throughout the day (48 emails):**

The scenario includes a dense distribution of emails, particularly during busy hours (8-10am, 3-5pm):

| Hour | Count | Types |
|------|-------|-------|
| 6-7 AM | 2 | Spam (dev tools promo, fitness newsletter) |
| 7-8 AM | 2 | Spam (morning briefing), Automated (CI/CD build success) |
| 8-9 AM | 6 | Work (Q1 planning, API docs question, **URGENT** incident + 2 replies), Automated (standup reminder) |
| 9-10 AM | 4 | Spam (cloud sales), Work (post-mortem, meeting agenda), Personal (mom checking in) |
| 10-11 AM | 4 | Work (feature timeline), Automated (Jira, LinkedIn), Spam (TechCrunch) |
| 11-12 PM | 3 | Personal (college friend reunion), Work (code review request), Spam |
| 12-1 PM | 3 | Spam (coffee, DoorDash, webinar promo) |
| 1-2 PM | 4 | Automated (cafeteria survey, meeting reminder), Work (PR question), Spam (Hacker Newsletter) |
| 2-3 PM | 2 | Work (meeting notes), HR (benefits enrollment) |
| 3-4 PM | 4 | Spam (webinar), Work (security notice, PR thanks), Personal (dentist reminder) |
| 4-5 PM | 4 | Automated (GitHub, Jira digest), Work (Q1 confirmation), Spam (electronics sale) |
| 5-6 PM | 3 | Work (API docs thanks), Personal (dinner plans), Spam (courses) |
| 6-7 PM | 3 | Personal (package delivery), Spam (fitness trackers, travel deals) |
| 7-8 PM | 4 | Automated (weekly summary), Spam (groceries, VPN, crypto newsletter) |

**Email types represented:**
- **Spam/promotional** (18): Software deals, fitness apps, cloud services, food delivery, shopping, webinars, learning platforms, travel deals, VPN, crypto
- **Work emails** (13): Q1 planning, API documentation, code review, meeting notes, security notices, follow-ups
- **Work incident thread** (3): Production API latency incident with status update and fix deployed
- **Automated/System** (9): CI/CD, standup bot, calendar reminders, Jira notifications, GitHub, weekly summary
- **Personal emails** (5): Mom, college friend, dinner plans, dentist appointment, package delivery

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