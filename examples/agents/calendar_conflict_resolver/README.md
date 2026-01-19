# Calendar Conflict Resolver Agent

This example demonstrates a **user-side agent** that monitors the user's calendar, detects
scheduling conflicts, and generates intelligent recommendations for resolving them.

## Overview

The agent simulates an AI personal assistant helping a busy project manager navigate a week
filled with overlapping meetings, double-bookings, and back-to-back events with insufficient
travel time. The agent analyzes meeting priorities, attendee importance, and scheduling
constraints to provide actionable recommendations.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    UES (Simulation Engine)                      │
│                                                                 │
│   Calendar State ◄───── Query ◄───── Conflict Resolver Agent   │
│                                              │                  │
│                                              ▼                  │
│                                      LLM Analysis               │
│                                              │                  │
│                                              ▼                  │
│                                    Recommendations Output       │
└─────────────────────────────────────────────────────────────────┘
```

**Key Components:**

- **Calendar Querying**: Uses the calendar API to retrieve events and detect overlaps
- **Conflict Detection**: Identifies double-bookings, insufficient gaps, and location conflicts
- **Priority Analysis**: Weighs meeting importance based on attendees, subjects, and recurrence
- **LLM Reasoning**: Generates natural language explanations for recommendations
- **Daily Briefing**: Summarizes the day's conflicts and proposed resolutions

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
uv run python examples/agents/calendar_conflict_resolver/agent.py

# With custom options
uv run python examples/agents/calendar_conflict_resolver/agent.py \
    --model llama3.2:3b \
    --ollama-host http://localhost:11434 \
    --ues-host http://localhost:8000
```

## The Scenario (`scenario.ues-scenario.json`)

The scenario simulates a challenging work week (Monday-Friday, January 19-23, 2026) for Jordan
Blake, a project manager at a consulting firm juggling three active client projects.

### The User

**Jordan Blake** - Senior Project Manager at Apex Consulting
- Reports to VP of Client Services (high-priority meetings)
- Manages 3 concurrent client engagements (Clients A, B, and C)
- Coordinates with a 5-person dev team requiring frequent decisions
- Works from the downtown office but has occasional client site visits

### Scheduled Events & Conflicts

The week includes approximately 35 calendar events with intentional conflicts:

| Day | Conflicts | Description |
|-----|-----------|-------------|
| **Monday** | 3 | Morning standup overlaps with client A sync; PM has triple-booking (VP meeting, client B, team retrospective) |
| **Tuesday** | 2 | Back-to-back meetings with 0 gap at different locations; lunch meeting conflicts with personal appointment |
| **Wednesday** | 4 | Worst day - 4 overlapping meetings in the 2-4pm block including mandatory all-hands |
| **Thursday** | 2 | Client presentations scheduled simultaneously; travel time ignored between office and client site |
| **Friday** | 1 | End-of-week review conflicts with pre-existing team celebration |

### Conflict Types Represented

1. **Direct Overlaps**: Two or more meetings at the exact same time
2. **Insufficient Gaps**: Back-to-back meetings with no buffer time
3. **Location Conflicts**: Sequential meetings at different locations without travel time
4. **Priority Conflicts**: VP/executive meetings conflicting with client meetings
5. **Recurring vs. One-time**: Standing meetings conflicting with important one-offs

## The Characters

### Executive

| Character | Role | Meeting Priority |
|-----------|------|------------------|
| **Rachel Kim** | VP of Client Services | 🔴 Critical - Her meetings override almost everything |

### Clients

| Character | Role | Meeting Priority | Notes |
|-----------|------|------------------|-------|
| **Tom Nguyen** | Client A Lead | 🟡 Medium | Flexible on timing, good relationship |
| **Aisha Patel** | Client B Lead | 🔴 High | Contract renewal in 2 weeks, inflexible |
| **Derek Morrison** | Client C Lead | 🟡 Medium | New engagement, still building rapport |

### Internal Team

| Character | Role | Meeting Priority |
|-----------|------|------------------|
| **Dev Team (5 engineers)** | Development Team | 🟢 Low-Medium | Can often be rescheduled or made async |
| **HR Representative** | Benefits/Admin | 🟢 Low | Usually flexible |
| **Finance Contact** | Budget Reviews | 🟡 Medium | Quarterly deadlines matter |

## The Agent (`agent.py`)

The agent performs daily calendar analysis with the following workflow:

### Orchestration

```python
load_scenario(scenario_file)

for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
    # Advance to start of business day (8 AM)
    advance_to_day_start(day)
    
    # Query all events for today
    events = query_calendar(day)
    
    # Detect conflicts
    conflicts = detect_conflicts(events)
    
    # For each conflict, gather context
    for conflict in conflicts:
        attendee_info = get_attendee_priorities(conflict)
        meeting_context = get_meeting_details(conflict)
    
    # Generate recommendations using LLM
    recommendations = call_agent(conflicts, context)
    
    # Output daily briefing
    print_briefing(day, recommendations)
```

### Conflict Detection Logic

The agent uses the following rules to identify conflicts:

1. **Time Overlap**: Events where `start_A < end_B AND start_B < end_A`
2. **Buffer Violations**: Less than 15 minutes between consecutive meetings
3. **Location Gaps**: Different locations with less than 30 minutes travel buffer
4. **All-Day Conflicts**: All-day events that conflict with timed meetings

### Priority Scoring

Each meeting receives a priority score based on:

| Factor | Weight | Description |
|--------|--------|-------------|
| Attendee Seniority | 30% | VP > Director > Manager > IC |
| Client vs Internal | 25% | External clients generally higher priority |
| Recurring vs One-time | 15% | One-time meetings often harder to reschedule |
| Subject Keywords | 15% | "URGENT", "Review", "Decision" boost priority |
| Historical Patterns | 15% | Meetings that frequently get rescheduled are lower priority |

## The System Prompt (`system_prompt.txt`)

The system prompt instructs the agent to:

- Analyze calendar conflicts from the perspective of a busy project manager
- Consider business relationships and political implications of rescheduling
- Prioritize client-facing commitments appropriately
- Suggest specific alternative times when recommending reschedules
- Explain reasoning clearly for each recommendation
- Flag conflicts that require human judgment (e.g., two equally important clients)

## Expected Output

The agent produces a daily briefing like:

```
═══════════════════════════════════════════════════════════════
📅 CALENDAR BRIEFING - Monday, January 19, 2026
═══════════════════════════════════════════════════════════════

🔴 CRITICAL CONFLICTS (3)

1. 9:00 AM - TRIPLE BOOKING
   • Team Standup (recurring, internal)
   • Client A Weekly Sync (Tom Nguyen)
   • 1:1 with Rachel Kim (VP)

   RECOMMENDATION: Attend VP 1:1 (highest priority). Decline Client A 
   sync and propose Tuesday 9 AM instead - Tom is typically flexible. 
   Skip standup - request async update from team lead.

   REASONING: VP meetings are critical and Rachel requested this 
   specifically. Tom has historically been accommodating with 
   reschedules. Standup can be covered via Slack summary.

2. 2:00 PM - DOUBLE BOOKING
   ...

───────────────────────────────────────────────────────────────
📊 SUMMARY
   • Total meetings today: 8
   • Conflicts requiring action: 3
   • Meetings to decline: 2
   • Meetings to reschedule: 1
   • Available focus time: 1.5 hours (11:00 AM - 12:30 PM)
═══════════════════════════════════════════════════════════════
```

## Key Patterns Demonstrated

1. **Calendar API Integration**: Querying events, detecting overlaps, analyzing attendees
2. **Multi-Factor Decision Making**: Combining rules-based priority scoring with LLM reasoning
3. **Structured Output Generation**: Producing actionable, well-formatted recommendations
4. **Context Accumulation**: Building up meeting context before making recommendations
5. **Time-Based Iteration**: Processing the scenario day-by-day

## Extending This Example

Ideas for extending this example:

- **Automated Actions**: Have the agent actually decline/reschedule via the calendar API
- **Learning from Feedback**: Track which recommendations the user accepts/rejects
- **Proactive Scheduling**: Suggest optimal times for new meetings based on existing calendar
- **Integration with Email**: Parse meeting-related emails to understand context
- **Team Calendar Awareness**: Consider other team members' availability

## File Structure

```
calendar_conflict_resolver/
├── agent.py                    # Main agent code
├── README.md                   # This documentation
├── system_prompt.txt           # LLM prompt template
├── scenario.ues-scenario.json  # Test scenario with conflicts
└── priorities.json             # Attendee priority configuration
```
